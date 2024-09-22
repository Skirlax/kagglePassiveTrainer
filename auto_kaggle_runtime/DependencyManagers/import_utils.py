import importlib
import importlib.util
import os.path
import sys
from typing import Callable
import inspect
from distutils.sysconfig import get_python_lib


class ImportManager:
    def __init__(self, self_file_path: str, execution_context: Callable):
        self.execution_context = execution_context
        self.self_file_path = self_file_path

    def is_import_third_party(self, module_name: str, project_root: str):
        try:
            spec = importlib.util.find_spec(module_name)
            if spec is None or spec.origin is None:
                return False
            path = os.path.realpath(spec.origin)
            if spec.origin == "frozen":
                return True
            return project_root not in path

        except Exception as e:
            print(f"Encountered error while processing {module_name}:\n{e}")

    def is_import(self, line: str):
        return line.startswith("import") or line.startswith("from")

    def is_builtin(self, module_name: str):
        std_lib = get_python_lib(standard_lib=True)
        std_lib = [x.replace(".py", "") for x in os.listdir(std_lib)]
        return module_name in sys.builtin_module_names or module_name in std_lib

    def get_imports_from_line(self, line: str):
        imports = []
        modules = line.split("import")
        if len(modules) > 1 and "from" in line:
            imports.append(modules[0].replace("from", "").strip().split(".")[0])
            return imports
        if len(modules[1].strip().split("as")) > 1:
            modules = modules[1].strip().split("as")[0].split(",")
        else:
            modules = modules[1].strip().split(",")
        for module in modules:
            imports.append(module.strip())

        return imports

    def get_execution_context_wise_nested_imports(self):
        def get_third_party_file_imports(file_path: str):
            with open(file_path, "r") as f:
                source_lines = f.readlines()
            third_party_modules = set()
            for line in source_lines:
                if line.startswith("#") or line.startswith(" ") or line.startswith("\n"):
                    continue
                if not self.is_import(line):
                    break

                modules = self.get_imports_from_line(line)
                third_party_modules.update(set(
                    filter(lambda x: self.is_import_third_party(x, os.path.dirname(
                        self.self_file_path)) and not self.is_builtin(x), modules)))
                modules = list(
                    filter(lambda x: not self.is_import_third_party(x, os.path.dirname(
                        self.self_file_path)) and not self.is_builtin(x), modules))
                for module in modules:
                    if module not in sys.modules:
                        importlib.import_module(module)

                    actual_module = sys.modules[module]

                    third_party_modules.update(get_third_party_file_imports(inspect.getfile(actual_module)))
            return third_party_modules

        return get_third_party_file_imports(self.self_file_path)
