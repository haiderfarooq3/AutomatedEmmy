# GPU Troubleshooting Guide

If you're seeing "No GPU detected. Using CPU for inference," follow these steps to diagnose and resolve the issue.

## Step 1: Verify Hardware and Drivers

### Check GPU Hardware
```bash
# Windows
wmic path win32_VideoController get name, driverversion

# Linux
lspci | grep -i nvidia
```

### Verify CUDA Installation
```bash
# Windows
nvidia-smi

# Linux
nvidia-smi
```

If `nvidia-smi` shows output with your GPU listed, CUDA drivers are installed.

## Step 2: Check PyTorch CUDA Support

```python
import torch
print(f"PyTorch version: {torch.__version__}")
print(f"CUDA available: {torch.cuda.is_available()}")
if torch.cuda.is_available():
    print(f"CUDA device: {torch.cuda.get_device_name(0)}")
```

Save this as `check_cuda.py` and run it to verify PyTorch's CUDA detection.

## Step 3: Install PyTorch with CUDA Support

If PyTorch doesn't detect CUDA, reinstall it with the correct CUDA version:

1. Uninstall current PyTorch:
   ```bash
   pip uninstall -y torch torchvision torchaudio
   ```

2. Install PyTorch with CUDA support:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
   ```

3. Verify installation:
   ```bash
   python -c "import torch; print(torch.cuda.is_available())"
   ```

## Step 4: Check CUDA Environment Variables

Ensure CUDA paths are correctly set:

### Windows
```
echo %CUDA_PATH%
echo %PATH%
```

### Linux/Mac
```
echo $CUDA_PATH
echo $PATH
```

## Smaller Model Option

If GPU issues persist, you can modify the script to use a smaller model more suitable for CPU:

```python
def setup_huggingface(self, model_name="distilgpt2", hf_token=None):
    # This model is smaller and works better on CPU
    # ...rest of the function...
```

## Additional Resources

- [PyTorch CUDA Documentation](https://pytorch.org/docs/stable/notes/cuda.html)
- [NVIDIA CUDA Installation Guide](https://docs.nvidia.com/cuda/cuda-installation-guide-microsoft-windows/index.html)
- [Hugging Face Optimizing for GPU Guide](https://huggingface.co/docs/transformers/performance)
