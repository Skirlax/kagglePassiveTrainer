from __future__ import annotations

import ast
from pathlib import Path

from auto_kaggle_runtime.config import RUNTIME_PACKAGE_NAME


def build_execution_source(file_path: str | Path) -> str:
    """Return source code suitable for a notebook cell.

    The generated source removes imports of this helper package and top-level
    ``if __name__ == "__main__"`` blocks, leaving user code and function
    definitions intact.
    """

    source_path = Path(file_path)
    source = source_path.read_text(encoding='utf-8')
    tree = ast.parse(source, filename=str(source_path))
    lines = source.splitlines()

    removed_lines = _lines_to_remove(tree)
    kept_lines = [line for line_number, line in enumerate(lines, start=1) if line_number not in removed_lines]
    return '\n'.join(kept_lines).rstrip() + '\n'


def _lines_to_remove(tree: ast.Module) -> set[int]:
    removed_lines: set[int] = set()
    for node in tree.body:
        if _imports_runtime_package(node) or _is_main_guard(node):
            removed_lines.update(range(node.lineno, getattr(node, 'end_lineno', node.lineno) + 1))
    return removed_lines


def _imports_runtime_package(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return any(_is_runtime_module(alias.name) for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module is not None and _is_runtime_module(node.module)
    return False


def _is_runtime_module(module_name: str) -> bool:
    return module_name == RUNTIME_PACKAGE_NAME or module_name.startswith(f'{RUNTIME_PACKAGE_NAME}.')


def _is_main_guard(node: ast.stmt) -> bool:
    return isinstance(node, ast.If) and _compares_dunder_name_to_main(node.test)


def _compares_dunder_name_to_main(node: ast.expr) -> bool:
    if not isinstance(node, ast.Compare) or len(node.ops) != 1 or not isinstance(node.ops[0], ast.Eq):
        return False
    if len(node.comparators) != 1:
        return False
    left = node.left
    right = node.comparators[0]
    return (_is_dunder_name(left) and _is_main_literal(right)) or (_is_main_literal(left) and _is_dunder_name(right))


def _is_dunder_name(node: ast.expr) -> bool:
    return isinstance(node, ast.Name) and node.id == '__name__'


def _is_main_literal(node: ast.expr) -> bool:
    return isinstance(node, ast.Constant) and node.value == '__main__'
