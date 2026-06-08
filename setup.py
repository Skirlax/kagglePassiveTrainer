from pathlib import Path

from setuptools import find_packages, setup


def read_requirements() -> list[str]:
    requirements_file = Path(__file__).with_name('requirements.txt')
    return [
        line.strip()
        for line in requirements_file.read_text(encoding='utf-8').splitlines()
        if line.strip() and not line.startswith('#')
    ]


setup(
    name='auto_kaggle_runtime',
    version='0.0.1',
    description='Auto-Kaggle Runtime',
    author='Skyr',
    packages=find_packages(),
    install_requires=read_requirements(),
    python_requires='>=3.10',
)
