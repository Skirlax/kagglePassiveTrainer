from __future__ import annotations

import inspect
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from auto_kaggle_runtime.config import KaggleUploadConfig
from auto_kaggle_runtime.dependencies import ImportManager
from auto_kaggle_runtime.notebook import Notebook
from auto_kaggle_runtime.notebook_cells import (
    additional_shell_commands,
    dependency_install_commands,
    downloaded_project_path,
    project_download_commands,
    python_path_commands,
    samba_setup_cells,
)
from auto_kaggle_runtime.server import SimpleFileServer
from auto_kaggle_runtime.source import build_execution_source

StatusReporter = Callable[[str], None]
Sleeper = Callable[[float], None]


class AutoKaggleUploader:
    """Create a Kaggle notebook that runs a local zero-argument function."""

    def __init__(
        self,
        execution_context: Callable[[], Any],
        execution_file_path: str,
        *,
        notebook: Notebook | None = None,
        import_manager: ImportManager | None = None,
        file_server: SimpleFileServer | None = None,
        status_reporter: StatusReporter = print,
        sleeper: Sleeper = time.sleep,
    ):
        self._validate_execution_context(execution_context, execution_file_path)
        self.execution_context = execution_context
        self.execution_file_path = str(Path(execution_file_path).resolve())
        self.project_root = Path(self.execution_file_path).parent
        self.import_manager = import_manager or ImportManager(self.execution_file_path, self.execution_context)
        self.notebook = notebook or Notebook()
        self.file_server = file_server or SimpleFileServer()
        self.report = status_reporter
        self.sleeper = sleeper

    def start(
        self,
        ngrok_auth_token: str,
        checkpoint_folder_name: str,
        ignore: list[str] | None = None,
        additional: list[str] | None = None,
        sleep_for: int = 60,
    ) -> None:
        """Create and push a Kaggle notebook for the configured execution context."""

        config = KaggleUploadConfig.from_start_arguments(
            ngrok_auth_token=ngrok_auth_token,
            checkpoint_folder_name=checkpoint_folder_name,
            ignore=ignore,
            additional=additional,
            sleep_for=sleep_for,
        )
        config.validate()

        self.report('Starting Kaggle upload...')
        project_snapshot_path = self.project_root / 'notebookFolder' / 'project'
        self.notebook.recreate_notebook_folder(str(self.project_root), str(project_snapshot_path), ['notebookFolder'])

        self.file_server.start_in_background(str(project_snapshot_path), config.ngrok_auth_token)
        public_url = self._wait_for_public_url(config.server_ready_timeout_seconds)
        self.report(f'Temporary server started at {public_url}.')

        self._add_remote_project_setup(public_url)
        self._add_checkpoint_sync_setup(config)
        self._add_additional_commands(config)
        self._add_dependency_installation(config)
        self._add_execution_cells(public_url)

        try:
            result = self.notebook.create(self.execution_file_path)
        except Exception:
            self.file_server.stop()
            raise

        self.report(f'Sleeping for {config.sleep_seconds} seconds to allow the notebook to download the project.')
        self.sleeper(config.sleep_seconds)
        self.report(
            'Find your ngrok tunnel address here: https://dashboard.ngrok.com/agents\n'
            "It's the one that tunnels to localhost:445"
        )
        self.report(f'Notebook ready at {result.url}!')

    def get_file_without_self_run(self, file_path: str) -> str:
        return build_execution_source(file_path)

    def _add_remote_project_setup(self, public_url: str) -> None:
        self.notebook.add_cell(project_download_commands(public_url))

    def _add_checkpoint_sync_setup(self, config: KaggleUploadConfig) -> None:
        for cell in samba_setup_cells(config.checkpoint_folder_name, config.ngrok_auth_token):
            self.notebook.add_cell(cell)

    def _add_additional_commands(self, config: KaggleUploadConfig) -> None:
        commands = additional_shell_commands(config.additional_commands)
        if commands:
            self.notebook.add_cell(commands)

    def _add_dependency_installation(self, config: KaggleUploadConfig) -> None:
        ignored_modules = set(config.ignored_modules_with_runtime)
        modules = sorted(set(self.import_manager.get_execution_context_wise_nested_imports()) - ignored_modules)
        self.report(f'Identified {len(modules)} installable third-party modules: {modules}')
        if modules:
            self.notebook.add_cell(dependency_install_commands(modules))

    def _add_execution_cells(self, public_url: str) -> None:
        self.notebook.add_cell(python_path_commands(downloaded_project_path(public_url)))
        self.notebook.add_cell(build_execution_source(self.execution_file_path))
        self.notebook.add_cell(f'{self.execution_context.__name__}()')

    def _wait_for_public_url(self, timeout_seconds: int) -> str:
        deadline = time.monotonic() + timeout_seconds
        while self.file_server.url is None:
            if time.monotonic() > deadline:
                raise TimeoutError('Timed out waiting for the local file server ngrok URL')
            self.sleeper(1)
        return self.file_server.url

    @staticmethod
    def _validate_execution_context(execution_context: Callable[..., Any], execution_file_path: str) -> None:
        if not callable(execution_context):
            raise TypeError('execution_context must be callable')

        execution_path = Path(execution_file_path)
        if not execution_path.is_absolute():
            raise ValueError('execution_file_path must be absolute')
        if not execution_path.is_file():
            raise FileNotFoundError(execution_file_path)

        signature = inspect.signature(execution_context)
        if signature.parameters:
            raise ValueError('execution_context must not require arguments')
