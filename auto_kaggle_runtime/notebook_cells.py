from __future__ import annotations

from collections.abc import Iterable


SAMBA_INSTALL_COMMANDS = [
    '!apt-get install -y samba',
    '!apt-get install -y screen',
    (
        '!curl -sSL https://ngrok-agent.s3.amazonaws.com/ngrok.asc '
        '| tee /etc/apt/trusted.gpg.d/ngrok.asc >/dev/null && '
        'echo "deb https://ngrok-agent.s3.amazonaws.com buster main" '
        '| tee /etc/apt/sources.list.d/ngrok.list && '
        'apt update && apt install ngrok -y'
    ),
]

ADD_SAMBA_SHARE_FUNCTION = """
def add_samba_share(smb_conf_path: str, sync_folder_name: str) -> None:
    samba_config = f'''
[{sync_folder_name}]
path = /kaggle/working/{sync_folder_name}
browseable = yes
read only = no
guest ok = yes
writeable = yes
'''
    with open(smb_conf_path, 'a', encoding='utf-8') as smb_conf:
        smb_conf.write(samba_config)
""".strip()


def project_download_commands(public_url: str) -> list[str]:
    return [
        f"!wget --recursive --no-parent --no-check-certificate -R 'index.html*' "
        f'{public_url} -P /kaggle/working/project'
    ]


def downloaded_project_path(public_url: str) -> str:
    return f"/kaggle/working/project/{public_url.removeprefix('https://').removeprefix('http://').rstrip('/')}"


def dependency_install_commands(modules: Iterable[str]) -> list[str]:
    return [f'!pip install {module}' for module in modules]


def additional_shell_commands(commands: Iterable[str]) -> list[str]:
    return [command if command.lstrip().startswith('!') else f'!{command}' for command in commands]


def python_path_commands(project_path: str) -> list[str]:
    return ['import sys', f"sys.path.append('{project_path}')"]


def samba_setup_cells(sync_folder_name: str, ngrok_auth_token: str) -> list[list[str]]:
    return [
        SAMBA_INSTALL_COMMANDS,
        [f'!mkdir -p /kaggle/working/{sync_folder_name}'],
        [
            f'!chown nobody:nogroup /kaggle/working/{sync_folder_name}',
            f'!chmod 777 /kaggle/working/{sync_folder_name}',
        ],
        [ADD_SAMBA_SHARE_FUNCTION],
        [f"add_samba_share('/etc/samba/smb.conf', '{sync_folder_name}')"],
        ['!/etc/init.d/smbd stop', '!/etc/init.d/nmbd stop', '!/etc/init.d/smbd start', '!/etc/init.d/nmbd start'],
        ['import os', 'get_ipython().system = os.system', f'!ngrok tcp 445 --authtoken {ngrok_auth_token} &'],
    ]
