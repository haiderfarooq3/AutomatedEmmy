"""
Setup script for installing required packages for Gmail Automation with Python 3.10
with optimization packages for improved performance
"""
import subprocess
import sys
import platform
import os
import multiprocessing

def install_package(package):
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def main():
    print(f"Setting up environment using Python {sys.version}")
    print(f"CPU Cores: {multiprocessing.cpu_count()}")
    
    # Core packages needed for Gmail API
    packages = [
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "secure-smtplib",
        "python-dotenv"
    ]
    
    # Performance optimization packages
    print("Installing performance optimization packages...")
    optimization_packages = [
        "cachetools",       # For efficient caching
        "ujson",            # Faster JSON processing
        "numba",            # JIT compilation for numerical operations
        "psutil",           # For system monitoring
        "pyarrow",          # For more efficient pandas operations
        "fastparquet",      # For faster data handling
        "rich",             # For better console output
        "line_profiler",    # For performance profiling
        "memory_profiler",  # For memory usage analysis
        "ray",              # For distributed computing
    ]
    packages.extend(optimization_packages)
    
    # Install PyTorch with CUDA support based on system configuration
    print("Detecting optimal PyTorch installation...")
    
    if platform.system() == "Windows":
        print("Windows system detected")
        cuda_command = "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
    else:
        # Better CUDA version detection for Linux
        cuda_version = "cu118"  # Default
        
        # Check for NVIDIA drivers
        try:
            gpu_info = subprocess.check_output("nvidia-smi", shell=True).decode("utf-8")
            print(f"GPU Info: {gpu_info.splitlines()[0]}")
            
            # Try to detect CUDA version
            if os.path.exists("/usr/local/cuda"):
                try:
                    nvcc_output = subprocess.check_output(["nvcc", "--version"]).decode("utf-8")
                    print(f"NVCC Info: {nvcc_output.splitlines()[0]}")
                    
                    if "11.8" in nvcc_output:
                        cuda_version = "cu118"
                    elif "12.1" in nvcc_output:
                        cuda_version = "cu121"
                    elif "12.6" in nvcc_output:
                        cuda_version = "cu126"
                except Exception as e:
                    print(f"Error getting NVCC version: {e}, using default {cuda_version}")
        except Exception as e:
            print(f"No NVIDIA GPU detected: {e}")
            print("Installing CPU-only PyTorch")
            cuda_version = "cpu"
        
        cuda_command = f"torch torchvision torchaudio --index-url https://download.pytorch.org/whl/{cuda_version}"
    
    print(f"Installing PyTorch with: {cuda_command}")
    subprocess.check_call([sys.executable, "-m", "pip", "install", cuda_command])
    
    # Install optimized transformers and huggingface packages
    print("Installing transformers and Hugging Face packages with optimizations...")
    huggingface_packages = [
        "transformers[sentencepiece]",  # Include sentencepiece for better tokenization
        "huggingface_hub",
        "accelerate",                   # For faster model loading and inference
        "bitsandbytes",                 # For quantization and optimization
        "optimum",                      # Hugging Face's optimization library
        "datasets",                     # Hugging Face's dataset library (optimized)
        "tokenizers>=0.14.0",           # Latest tokenizers for better performance
        "sentencepiece",                # For efficient tokenization
        "protobuf",                     # Required for model serialization
        "safetensors",                  # Safe and efficient tensor serialization
    ]
    packages.extend(huggingface_packages)
    
    # Streamlit with performance packages
    print("Installing Streamlit with optimization packages...")
    streamlit_packages = [
        "streamlit>=1.25.0",
        "watchdog",                     # Better file watching for Streamlit
        "pydeck",                       # For better visualizations
        "pillow",                       # For image processing
        "plotly",                       # For interactive visualizations
        "streamlit-profiler",           # Streamlit performance profiling
        "altair",                       # For visualization
    ]
    packages.extend(streamlit_packages)
    
    # Optional packages for better Gmail integration
    print("Installing Gmail API optimization packages...")
    gmail_packages = [
        "apiclient",                    # API client helpers
        "email-validator",              # Validate email addresses
        "python-dateutil",              # Better date handling
        "pytz",                         # Timezone handling
        "tqdm",                         # Progress bars
    ]
    packages.extend(gmail_packages)
    
    # Install all required packages
    print(f"\nInstalling {len(packages)} packages...")
    for package in packages:
        install_package(package)
    
    print("\nInstalling optional acceleration libraries...")
    try:
        # These might fail on some systems but are helpful when they work
        acceleration_libs = [
            "nvidia-ml-py3",            # For NVIDIA GPU monitoring
            "torch-tensorrt",           # TensorRT integration for PyTorch
            "onnx",                     # ONNX model format for faster inference
            "onnxruntime",              # Runtime for ONNX models
            "onnxruntime-gpu",          # GPU acceleration for ONNX models
        ]
        
        for lib in acceleration_libs:
            try:
                print(f"Trying to install {lib}...")
                subprocess.check_call([sys.executable, "-m", "pip", "install", lib])
                print(f"Successfully installed {lib}")
            except Exception as e:
                print(f"Failed to install {lib}: {e}")
    except Exception as e:
        print(f"Some optional acceleration libraries could not be installed: {e}")
    
    print("\nSetup complete! You can now run 'python Automation.py' or 'streamlit run streamlit_app.py'")
    
    # Print instructions for verifying installation
    print("\n--- Verification Instructions ---")
    print("To verify PyTorch installation:")
    print("  python -c \"import torch; print('CUDA available:', torch.cuda.is_available())\"")
    print("\nTo verify transformers installation:")
    print("  python -c \"from transformers import pipeline; print('Transformers loaded successfully')\"")
    print("\nTo verify Gmail API installation:")
    print("  python -c \"from googleapiclient.discovery import build; print('Gmail API client loaded successfully')\"")

if __name__ == "__main__":
    main()
