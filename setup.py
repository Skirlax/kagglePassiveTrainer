from setuptools import setup, find_packages

setup(
    name='auto_kaggle_runtime',
    version='0.0.1',
    description='Auto-Kaggle Runtime',
    author='Skyr',
    packages=find_packages(),
    install_requires=open("requirements.txt").read().strip().split("\n"),
)
