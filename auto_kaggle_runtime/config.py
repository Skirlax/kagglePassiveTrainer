from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

RUNTIME_PACKAGE_NAME = 'auto_kaggle_runtime'


@dataclass(frozen=True)
class KaggleUploadConfig:
    """Runtime configuration for one Kaggle upload."""

    ngrok_auth_token: str
    checkpoint_folder_name: str
    ignored_modules: tuple[str, ...] = ()
    additional_commands: tuple[str, ...] = ()
    sleep_seconds: int = 60
    server_ready_timeout_seconds: int = 30

    @classmethod
    def from_start_arguments(
        cls,
        *,
        ngrok_auth_token: str,
        checkpoint_folder_name: str,
        ignore: Iterable[str] | None = None,
        additional: Iterable[str] | None = None,
        sleep_for: int = 60,
    ) -> KaggleUploadConfig:
        return cls(
            ngrok_auth_token=ngrok_auth_token,
            checkpoint_folder_name=checkpoint_folder_name,
            ignored_modules=_as_tuple(ignore),
            additional_commands=_as_tuple(additional),
            sleep_seconds=sleep_for,
        )

    @property
    def ignored_modules_with_runtime(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys((*self.ignored_modules, RUNTIME_PACKAGE_NAME)))

    def validate(self) -> None:
        if not self.ngrok_auth_token:
            raise ValueError('ngrok_auth_token must not be empty')
        if not self.checkpoint_folder_name:
            raise ValueError('checkpoint_folder_name must not be empty')
        if '/' in self.checkpoint_folder_name or '\\' in self.checkpoint_folder_name:
            raise ValueError('checkpoint_folder_name must be a folder name, not a path')
        if self.sleep_seconds < 0:
            raise ValueError('sleep_for must be greater than or equal to zero')
        if self.server_ready_timeout_seconds <= 0:
            raise ValueError('server_ready_timeout_seconds must be greater than zero')


def _as_tuple(values: Iterable[str] | None) -> tuple[str, ...]:
    if values is None:
        return ()
    return tuple(values)
