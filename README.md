# kagglePassiveTrainer

#### Description

This library creates a Kaggle notebook that runs a local Python entry point on Kaggle's free GPU kernels.

This library will automatically

- Detect third-party packages imported by your entry file and nested local modules.
- Upload a clean snapshot of your project to a temporary HTTP server exposed through ngrok.
- Generate and push a Kaggle notebook that downloads the project, installs dependencies, adds the project to
  `sys.path`, and calls your entry point.
- Create a Samba share on Kaggle for checkpoint/output synchronization.

#### Quick example

```python
import os

from auto_kaggle_runtime.uploader import AutoKaggleUploader


def train() -> None:
    ...


if __name__ == "__main__":
    os.environ["KAGGLE_USERNAME"] = "your-kaggle-username"
    os.environ["KAGGLE_KEY"] = "your-kaggle-api-key"

    uploader = AutoKaggleUploader(train, __file__)
    uploader.start(
        ngrok_auth_token="your-ngrok-auth-token",
        checkpoint_folder_name="checkpoints",
        ignore=["package-to-skip"],
        additional=["pip install custom-package", "apt-get install -y system-package"],
        sleep_for=120,
    )
```

The entry point passed to `AutoKaggleUploader` must be callable without arguments, and `__file__` must be an
absolute path.
