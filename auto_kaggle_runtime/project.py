from __future__ import annotations

import shutil
from collections.abc import Iterable
from pathlib import Path

DEFAULT_EXCLUDED_NAMES = frozenset(
    {
        '.git',
        '.idea',
        '.mypy_cache',
        '.pytest_cache',
        '__pycache__',
        'notebookFolder',
    }
)


def recreate_project_snapshot(
    source_path: str | Path,
    target_path: str | Path,
    ignore_file_names: Iterable[str] = (),
) -> None:
    """Recreate a clean project snapshot for Kaggle to download."""

    source_root = Path(source_path).resolve()
    target_root = Path(target_path).resolve()
    target_parent = target_root.parent

    if source_root == target_parent:
        raise ValueError('target_path must be inside a dedicated staging directory')
    if target_parent.exists():
        shutil.rmtree(target_parent)

    copy_project_tree(source_root, target_root, ignore_file_names)


def copy_project_tree(source_path: str | Path, target_path: str | Path, ignore_file_names: Iterable[str] = ()) -> None:
    source_root = Path(source_path).resolve()
    target_root = Path(target_path).resolve()
    excluded_names = set(DEFAULT_EXCLUDED_NAMES)
    excluded_paths: set[Path] = set()

    for ignored_file_name in ignore_file_names:
        ignored_path = Path(ignored_file_name)
        excluded_names.add(ignored_path.name)
        if ignored_path.is_absolute():
            excluded_paths.add(ignored_path.resolve())

    _copy_directory(source_root, target_root, excluded_names, excluded_paths)


def _copy_directory(source_root: Path, target_root: Path, excluded_names: set[str], excluded_paths: set[Path]) -> None:
    target_root.mkdir(parents=True, exist_ok=True)
    for source_item in source_root.iterdir():
        resolved_source_item = source_item.resolve()
        if source_item.name in excluded_names or resolved_source_item in excluded_paths:
            continue
        if target_root in resolved_source_item.parents:
            continue

        target_item = target_root / source_item.name
        if source_item.is_dir():
            _copy_directory(source_item, target_item, excluded_names, excluded_paths)
        else:
            shutil.copy2(source_item, target_item)
