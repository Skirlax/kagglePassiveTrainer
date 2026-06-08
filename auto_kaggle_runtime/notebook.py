from __future__ import annotations

import json
import os
import re
from collections.abc import Sequence
from pathlib import Path
from typing import Any

from auto_kaggle_runtime.project import copy_project_tree, recreate_project_snapshot

NOTEBOOK_FILE_NAME = '__notebook_source__.ipynb'
KERNEL_METADATA_FILE_NAME = 'kernel-metadata.json'


class Notebook:
    """Build and push Kaggle notebook artifacts."""

    def __init__(self, api: Any | None = None):
        self.notebook = _new_notebook()
        self.api = api

    def create(self, execution_file: str) -> Any:
        notebook_folder = self.assemble_to_kaggle_folder(execution_file)
        api = self._get_api()
        api.authenticate()
        return api.kernels_push(str(notebook_folder))

    def add_cell(self, source: Sequence[str] | str) -> None:
        cell_source = source if isinstance(source, str) else '\n'.join(source)
        self.notebook['cells'].append(_new_code_cell(cell_source))

    def remove_cell(self, from_top_index: int) -> None:
        self.notebook['cells'].pop(from_top_index)

    def assemble_to_kaggle_folder(self, execution_file: str) -> Path:
        project_root = Path(execution_file).resolve().parent
        notebook_folder = project_root / 'notebookFolder'
        notebook_folder.mkdir(exist_ok=True)

        (notebook_folder / NOTEBOOK_FILE_NAME).write_text(json.dumps(self.notebook, indent=2), encoding='utf-8')
        (notebook_folder / KERNEL_METADATA_FILE_NAME).write_text(
            json.dumps(_kernel_metadata(project_root), indent=2),
            encoding='utf-8',
        )
        return notebook_folder

    def copy_dirs(self, source_path: str, target_path: str, ignore_file_names: list[str] | None = None) -> None:
        copy_project_tree(source_path, target_path, ignore_file_names or [])

    def get_url(self) -> str:
        return self._get_api().kernels_list()[0].url

    def recreate_notebook_folder(self, source_path: str, target_path: str, ignore_file_names: list[str]) -> None:
        recreate_project_snapshot(source_path, target_path, ignore_file_names)

    def _get_api(self) -> Any:
        if self.api is None:
            from kaggle.api.kaggle_api_extended import KaggleApi

            self.api = KaggleApi()
        return self.api


def _new_notebook() -> dict[str, Any]:
    return {
        'cells': [],
        'metadata': {
            'kernelspec': {
                'display_name': 'Python 3',
                'language': 'python',
                'name': 'python3',
            },
            'language_info': {
                'codemirror_mode': {
                    'name': 'ipython',
                    'version': 3,
                },
                'file_extension': '.py',
                'mimetype': 'text/x-python',
                'name': 'python',
                'nbconvert_exporter': 'python',
                'pygments_lexer': 'ipython3',
                'version': '3.8.5',
            },
        },
        'nbformat': 4,
        'nbformat_minor': 5,
    }


def _new_code_cell(source: str) -> dict[str, Any]:
    return {
        'cell_type': 'code',
        'execution_count': None,
        'metadata': {},
        'outputs': [],
        'source': source,
    }


def _kernel_metadata(project_root: Path) -> dict[str, Any]:
    username = os.environ.get('KAGGLE_USERNAME')
    if not username:
        raise EnvironmentError('KAGGLE_USERNAME must be set before creating a Kaggle notebook')

    project_slug = _slugify(project_root.name)
    return {
        'title': f'{project_root.name}_automated',
        'code_file': NOTEBOOK_FILE_NAME,
        'id': f'{username}/{project_slug}-automated',
        'language': 'python',
        'kernel_type': 'notebook',
        'is_private': True,
        'enable_gpu': True,
        'enable_internet': True,
    }


def _slugify(value: str) -> str:
    slug = re.sub(r'[^a-z0-9-]+', '-', value.lower()).strip('-')
    return slug or 'kaggle-project'
