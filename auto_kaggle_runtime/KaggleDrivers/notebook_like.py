import json
import os.path
import shutil
import nbformat


class Notebook:
    def __init__(self):
        from kaggle.api.kaggle_api_extended import KaggleApi
        self.notebook = nbformat.v4.new_notebook()
        self.api = KaggleApi()

    def create(self, execution_file: str):
        self.api.authenticate()
        self.assemble_to_kaggle_folder(execution_file)
        return self.api.kernels_push(os.path.dirname(execution_file) + "/notebookFolder")

    def add_cell(self, source: list):
        cell = nbformat.v4.new_code_cell(source="\n".join(source))
        self.notebook["cells"].append(cell)

    def remove_cell(self, from_top_index: int):
        self.notebook["cells"].pop(from_top_index)

    def assemble_to_kaggle_folder(self, execution_file: str):
        project_root_dir = os.path.dirname(execution_file)
        # if os.path.exists(f"{project_root_dir}/notebookFolder"):
        #     shutil.rmtree(f"{project_root_dir}/notebookFolder")
        os.makedirs(f"{project_root_dir}/notebookFolder",exist_ok=True)
        with open(f"{project_root_dir}/notebookFolder/__notebook_source__.ipynb", "w") as file:
            nbformat.write(self.notebook, file)
        with open(f"{project_root_dir}/notebookFolder/__notebook_source__.ipynb", "r") as file:
            content = json.load(file)
            content["metadata"] = {"kernelspec": {
                "display_name": "Python 3",
                "language": "python",
                "name": "python3"
            },
                "language_info": {
                    "codemirror_mode": {
                        "name": "ipython",
                        "version": 3
                    },
                    "file_extension": ".py",
                    "mimetype": "text/x-python",
                    "name": "python",
                    "nbconvert_exporter": "python",
                    "pygments_lexer": "ipython3",
                    "version": "3.8.5"
                }
            }
        with open(f"{project_root_dir}/notebookFolder/__notebook_source__.ipynb", "w") as file:
            json.dump(content, file)
        username = os.environ.get("KAGGLE_USERNAME")
        metadata_file = {
            "title": project_root_dir.split("/")[-1] + "_automated",
            "code_file": f"{project_root_dir}/notebookFolder/__notebook_source__.ipynb",
            "id": username + "/" + project_root_dir.split("/")[-1].lower() + "-automated",
            "language": "python",
            "kernel_type": "notebook",
            "is_private": True,
            "enable_gpu": True,
            "enable_internet": True,
        }
        with open(f"{project_root_dir}/notebookFolder/kernel-metadata.json", "w") as file:
            json.dump(metadata_file, file)

    def copy_dirs(self, source_path: str, target_path: str, ignore_file_names: list[str] = None):
        if ignore_file_names is None:
            ignore_file_names = []
        os.makedirs(target_path, exist_ok=True)
        for item in os.listdir(source_path):
            if item in ignore_file_names:
                continue
            s = os.path.join(source_path, item)
            d = os.path.join(target_path, item)
            if os.path.isdir(s):
                self.copy_dirs(s, d)
            else:
                shutil.copy(s, d)

    def get_url(self):
        return self.api.kernels_list()[0].url

    def recreate_notebook_folder(self, source_path: str, target_path: str, ignore_file_names: list):
        if os.path.exists(target_path):
            parent_dir = os.path.dirname(target_path)
            shutil.rmtree(parent_dir)

        os.makedirs(target_path)
        self.copy_dirs(source_path, target_path, ignore_file_names)
