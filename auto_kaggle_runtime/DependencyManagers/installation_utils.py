import importlib.metadata
from pip._internal import main as pipmain


class InstallationManager:

    def attempt_install(self, modules: list[str], ignore: list[str]):
        for module in modules:
            if module in ignore:
                continue
            try:
                pipmain(["install", importlib.metadata.distribution(module).metadata["Name"]])
            except Exception as e:
                print(f"Failing to install module {module}, exception:\n{e}")

