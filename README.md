# kagglePassiveTrainer

#### 📄 Description

This library allows you to train your neural networks at Kaggle's free GPU kernels with ease. 

This library will automatically

- Detect the installable pip packages in your project, ignoring local imports as well as built-in modules and install them on the kernel.
- Upload your project to the kernel and add it to python path so all your local directories and files can be utilized in the kernel without any modification required on your part.
- Run your code on the kernel
  - You can download any outputs made by your script in the Output tab on the kernel URL

#### 🚀 Quick example

```python
from auto_kaggle_runtime.auto_kaggle_uploader import AutoKaggleUploader

if __name__ == '__main__':
    os.environ["KAGGLE_USERNAME"] = "your-kaggle-username"
    os.environ["KAGGLE_KEY"] = "your-kaggle-api-key"
    inter = AutoKaggleUploader(your_target_method, __file__)
    inter.start("your-ngrok-auth-token", ignore=["pip-package-to-ignore"],
                additional=["pip install something, sudo apt install something-else"],
                sleep_for=120)  # How long should we wait for the project to be uploaded?
```
