# Gmail Automation Tool - Instructions

Follow these steps to set up and run the Gmail Automation Tool using your older Python installation for better CUDA compatibility.

## Setup Instructions

1. **Set up the Environment**
   - Double-click the `setup_env.bat` file
   - This will automatically:
     - Find an older Python installation (3.8-3.11) on your system
     - Install all required dependencies
     - Configure PyTorch with CUDA support

2. **Run the Automation Tool**
   - Double-click the `run_automation.bat` file
   - This will:
     - Launch the script using the older Python version
     - Show GPU detection information
     - Ask for your Hugging Face token (optional)
     - Process and respond to important emails

## Troubleshooting

If you encounter issues:

- **GPU Not Detected**: Run `check_gpu.py` with your older Python installation:
  ```
  python3.10 check_gpu.py  # Replace 3.10 with your version
  ```

- **Authentication Issues**: Delete the `token.pickle` file and run again to re-authenticate

- **Model Loading Errors**: Try a smaller model when prompted, or manually edit the model name in the code to "distilgpt2"

## Advanced Usage

To run specific Python versions manually:

```
python3.10 Automation.py  # Replace 3.10 with your version
```

To install requirements manually:

```
python3.10 -m pip install -r requirements.txt  # Replace 3.10 with your version
```
