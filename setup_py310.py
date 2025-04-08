"""
Setup script for installing required packages for Gmail Automation with Python 3.10
"""
import subprocess
import sys
import platform

def install_package(package):
    print(f"Installing {package}...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", package])

def main():
    print(f"Setting up environment using Python {sys.version}")
    
    # Core packages needed for Gmail API
    packages = [
        "google-api-python-client",
        "google-auth-httplib2",
        "google-auth-oauthlib",
        "secure-smtplib",
        "python-dotenv"
    ]
    
    # Install PyTorch with CUDA
    print("Installing PyTorch with CUDA support...")
    cuda_command = "torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
    subprocess.check_call([sys.executable, "-m", "pip", "install", cuda_command])
    
    # Install transformers and huggingface_hub
    packages.extend([
        "transformers",
        "huggingface_hub"
    ])
    
    # Install all required packages
    for package in packages:
        install_package(package)
    
    print("\nSetup complete! You can now run 'python Automation.py'")

if __name__ == "__main__":
    main()
