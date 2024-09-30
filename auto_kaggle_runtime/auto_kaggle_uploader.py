import inspect
import os.path
import time
from typing import Callable

from pyngrok import ngrok

from auto_kaggle_runtime.DependencyManagers.import_utils import ImportManager
from auto_kaggle_runtime.DependencyManagers.sftp_server import start_server, SimpleFileServer
from auto_kaggle_runtime.KaggleDrivers.notebook_like import Notebook


class AutoKaggleUploader:
    def __init__(self, execution_context: Callable, execution_file_path: str):
        self.check_assertions(execution_context, execution_file_path)
        self.execution_context = execution_context
        self.execution_file_path = execution_file_path
        self.import_manager = ImportManager(self.execution_file_path, self.execution_context)
        self.notebook = Notebook()

    def check_assertions(self, execution_context: Callable, execution_file_path: str):
        assert callable(
            execution_context), ("The execution context must be a callable method from which this class is "
                                 "instantiated and the program is run!")
        assert os.path.isabs(
            execution_file_path), "The path to the file in which the execution context is located must be absolute!"

        assert len(inspect.signature(execution_context).parameters) == 0, "Execution context can't require arguments"

    def start(self, ngrok_auth_token: str, checkpoint_folder_name: str, ignore: list[str] = None,
              additional: list[str] = None,
              sleep_for: int = 60) -> None:
        """
        This method will start the Kaggle notebook and upload the provided execution context to the Kaggle notebook.
        :param ngrok_auth_token: The ngrok authentication token that will be used to create tunnels.
        :param checkpoint_folder_name: The name of the folder where your program will store checkpoints (data). This will be prefixed with /kaggle/working/ in the Kaggle notebook.
        :param ignore: What modules should be ignored while installing the third-party modules?
        :param additional: What additional commands should be run before the provided method?
        :param sleep_for: How long should we wait for the notebook to get the data?
        :return: None
        """
        if ignore is None:
            ignore = []
        if additional is None:
            additional = []
        ignore.append("auto_kaggle_runtime")
        print("Starting kaggle upload...")
        self.notebook.recreate_notebook_folder(os.path.dirname(self.execution_file_path),
                                               os.path.dirname(self.execution_file_path) + "/notebookFolder/project",
                                               [self.execution_file_path, "notebookFolder"])
        server = SimpleFileServer()
        start_server(server, os.path.dirname(self.execution_file_path) + "/notebookFolder" + "/project",
                     ngrok_auth_token)
        while server.url is None:
            time.sleep(1)
        url = server.url
        print(f"Temporary server started at {url}.")
        self.notebook.add_cell(
            [f"!wget --recursive --no-parent --no-check-certificate -R 'index.html*' {url} -P /kaggle/working/project"])
        self._setup_samba(checkpoint_folder_name, ngrok_auth_token)
        # self.notebook.add_cell(["!ls /kaggle/working/project"])
        self.notebook.add_cell(["!" + x for x in additional])
        modules = self.import_manager.get_execution_context_wise_nested_imports()
        print(f"Identified {len(modules)} installable, third-party modules! Those are: {modules}")
        modules = list(filter(lambda x: x not in ignore, modules))
        self.notebook.add_cell([f"!pip install {x}" for x in modules])
        self.notebook.add_cell(
            ["import os,sys", f"sys.path.append('/kaggle/working/project/{url.replace('https://', '')}')"])
        self.notebook.add_cell([self.get_file_without_self_run(self.execution_file_path)])
        self.notebook.add_cell([self.execution_context.__name__ + "()"])
        result = self.notebook.create(self.execution_file_path)
        print(f"Sleeping for {sleep_for} to allow the notebook to get the data.")
        time.sleep(sleep_for)
        print(f"Find your ngrok tunnel address here: https://dashboard.ngrok.com/agents\nIt's the one that tunnels to "
              f"localhost:445")
        print(f"Notebook ready at {result.url}!")

    def get_file_without_self_run(self, file_path: str):
        with open(file_path, "r") as file:
            file_content = file.read()
        new_lines = []
        for line in file_content.split("\n"):
            if "auto_kaggle_runtime" in line:
                continue
            new_lines.append(line)
        file_content = "\n".join(new_lines)
        return file_content.split("if __name__ == ")[0]

    def _setup_samba(self, sync_folder_name: str, ngrok_auth_token: str) -> None:

        def add_samba_share(smb_conf_path,sync_folder_name_):
            samba_config = f"""
            [{sync_folder_name_}]
            path = /kaggle/working/{sync_folder_name_}
            browseable = yes
            read only = no
            guest ok = yes
            writeable = yes
            """
            with open(smb_conf_path, "a") as smb_conf:
                smb_conf.write(samba_config)

        self.notebook.add_cell(["!apt-get install -y samba", "!apt-get install -y screen",
                                '!curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc | tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && echo "deb https://ngrok-agent.s3.amazonaws.com buster main" | tee /etc/apt/sources.list.d/ngrok.list && apt update && apt install ngrok -y'])
        self.notebook.add_cell([f"!mkdir -p /kaggle/working/{sync_folder_name}"])
        self.notebook.add_cell([f"!chown nobody:nogroup /kaggle/working/{sync_folder_name}",
                                f"!chmod 777 /kaggle/working/{sync_folder_name}"])
        self.notebook.add_cell(
            [inspect.getsource(add_samba_share)])
        self.notebook.add_cell([f"add_samba_share('/etc/samba/smb.conf','{sync_folder_name}')"])
        self.notebook.add_cell(["!/etc/init.d/smbd stop", "!/etc/init.d/nmbd stop",
                                "!/etc/init.d/smbd start", "!/etc/init.d/nmbd start"])
        self.notebook.add_cell(
            ["import os", "get_ipython().system = os.system", f"!ngrok tcp 445 --authtoken {ngrok_auth_token} &"])
