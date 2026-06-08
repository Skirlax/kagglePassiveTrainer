from __future__ import annotations

import ast
import importlib.metadata
import importlib.util
import sys
import sysconfig
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class ImportRequest:
    """A normalized import statement extracted from Python source."""

    module: str
    level: int = 0
    imported_names: tuple[str, ...] = ()

    @property
    def top_level_module(self) -> str:
        if self.module:
            return self.module.split('.', maxsplit=1)[0]
        if self.imported_names:
            return self.imported_names[0].split('.', maxsplit=1)[0]
        return ''


@dataclass
class DependencyScanner:
    """Find third-party packages imported by a Python file and local imports."""

    project_root: Path
    package_distributions: Mapping[str, list[str]] = field(default_factory=importlib.metadata.packages_distributions)
    _visited_files: set[Path] = field(default_factory=set, init=False, repr=False)

    def __post_init__(self) -> None:
        self.project_root = self.project_root.resolve()

    def scan_file(self, file_path: str | Path) -> set[str]:
        source_path = Path(file_path).resolve()
        if source_path in self._visited_files:
            return set()

        self._visited_files.add(source_path)
        tree = ast.parse(source_path.read_text(encoding='utf-8'), filename=str(source_path))

        dependencies: set[str] = set()
        for import_request in collect_imports(tree):
            dependencies.update(self._scan_import(import_request, source_path))
        return dependencies

    def _scan_import(self, import_request: ImportRequest, current_file: Path) -> set[str]:
        if import_request.top_level_module == '__future__':
            return set()

        local_modules = self._resolve_local_imports(import_request, current_file)
        if local_modules:
            dependencies: set[str] = set()
            for local_module in local_modules:
                dependencies.update(self.scan_file(local_module))
            return dependencies

        module_name = import_request.top_level_module
        if not module_name or self.is_standard_library(module_name):
            return set()

        return set(self.distribution_names_for(module_name))

    def _resolve_local_imports(self, import_request: ImportRequest, current_file: Path) -> list[Path]:
        if import_request.level > 0:
            return self._resolve_relative_imports(import_request, current_file)
        return self._resolve_absolute_imports(import_request)

    def _resolve_absolute_imports(self, import_request: ImportRequest) -> list[Path]:
        local_paths: list[Path] = []
        if import_request.module:
            module_path = self._resolve_module_parts(self.project_root, import_request.module.split('.'))
            if module_path is not None:
                local_paths.append(module_path)
                local_paths.extend(self._resolve_imported_submodules(module_path, import_request.imported_names))
                return _unique_paths(local_paths)

        for imported_name in import_request.imported_names:
            module_path = self._resolve_module_parts(self.project_root, imported_name.split('.'))
            if module_path is not None:
                local_paths.append(module_path)
        return _unique_paths(local_paths)

    def _resolve_relative_imports(self, import_request: ImportRequest, current_file: Path) -> list[Path]:
        base_directory = current_file.parent
        for _ in range(import_request.level - 1):
            base_directory = base_directory.parent

        local_paths: list[Path] = []
        if import_request.module:
            module_path = self._resolve_module_parts(base_directory, import_request.module.split('.'))
            if module_path is not None:
                local_paths.append(module_path)
                local_paths.extend(self._resolve_imported_submodules(module_path, import_request.imported_names))
                return _unique_paths(local_paths)

        for imported_name in import_request.imported_names:
            module_path = self._resolve_module_parts(base_directory, imported_name.split('.'))
            if module_path is not None:
                local_paths.append(module_path)
        return _unique_paths(local_paths)

    def _resolve_imported_submodules(self, module_path: Path, imported_names: Iterable[str]) -> list[Path]:
        package_directory = module_path.parent if module_path.name == '__init__.py' else None
        if package_directory is None:
            return []

        local_paths: list[Path] = []
        for imported_name in imported_names:
            module_path = self._resolve_module_parts(package_directory, imported_name.split('.'))
            if module_path is not None:
                local_paths.append(module_path)
        return local_paths

    @staticmethod
    def _resolve_module_parts(base_directory: Path, module_parts: list[str]) -> Path | None:
        module_path = base_directory.joinpath(*module_parts)
        file_path = module_path.with_suffix('.py')
        package_path = module_path / '__init__.py'

        if file_path.is_file():
            return file_path.resolve()
        if package_path.is_file():
            return package_path.resolve()
        return None

    def distribution_names_for(self, module_name: str) -> tuple[str, ...]:
        distributions = self.package_distributions.get(module_name)
        if distributions:
            return tuple(sorted(distributions))
        return (module_name,)

    @staticmethod
    def is_standard_library(module_name: str) -> bool:
        if module_name in sys.builtin_module_names:
            return True
        if module_name in getattr(sys, 'stdlib_module_names', set()):
            return True

        spec = importlib.util.find_spec(module_name)
        if spec is None or spec.origin is None:
            return False
        if spec.origin in {'built-in', 'frozen'}:
            return True

        origin = Path(spec.origin).resolve()
        standard_library = Path(sysconfig.get_paths()['stdlib']).resolve()
        return standard_library in origin.parents and 'site-packages' not in origin.parts


class ImportManager:
    """Backward-compatible facade for dependency detection."""

    def __init__(self, self_file_path: str, execution_context: Callable[..., object] | None = None):
        self.execution_context = execution_context
        self.self_file_path = str(Path(self_file_path).resolve())
        self.project_root = Path(self.self_file_path).parent

    def get_execution_context_wise_nested_imports(self) -> list[str]:
        scanner = DependencyScanner(self.project_root)
        return sorted(scanner.scan_file(self.self_file_path))

    def is_import_third_party(self, module_name: str, project_root: str) -> bool:
        scanner = DependencyScanner(Path(project_root))
        if scanner._resolve_module_parts(Path(project_root), module_name.split('.')) is not None:
            return False
        return not scanner.is_standard_library(module_name)

    def is_import(self, line: str) -> bool:
        return bool(_collect_imports_from_text(line))

    def is_builtin(self, module_name: str) -> bool:
        return DependencyScanner.is_standard_library(module_name)

    def get_imports_from_line(self, line: str) -> list[str]:
        return [request.top_level_module for request in _collect_imports_from_text(line) if request.top_level_module]


def collect_imports(tree: ast.AST) -> list[ImportRequest]:
    requests: list[ImportRequest] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            requests.extend(ImportRequest(alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            requests.append(
                ImportRequest(
                    module=node.module or '',
                    level=node.level,
                    imported_names=tuple(alias.name for alias in node.names if alias.name != '*'),
                )
            )
    return requests


def _collect_imports_from_text(source: str) -> list[ImportRequest]:
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return []
    return [request for request in collect_imports(tree) if request.top_level_module]


def _unique_paths(paths: Iterable[Path]) -> list[Path]:
    return list(dict.fromkeys(paths))
