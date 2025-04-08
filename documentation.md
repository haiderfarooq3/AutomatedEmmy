# Gmail Automation Tool Documentation

## Overview

This tool automatically handles emails by:
1. Sending professionally formatted emails with proper subject fields
2. Automatically signing emails
3. Replying to important unread emails
4. Extracting recipient emails from incoming messages

## Setup and Installation

### Requirements

- Python 3.6+ (Python 3.10 recommended for better CUDA compatibility)
- Gmail account with API access configured

### Installation

1. Clone this repository or download the source code
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. For GPU support (recommended for faster responses), install PyTorch with CUDA:
   ```bash
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
   ```

## OAuth Setup Guide

### Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on "Select a project" at the top of the page
3. Click "NEW PROJECT" in the window that appears
4. Enter a project name (e.g., "Gmail Assistant")
5. Click "CREATE"
6. Wait for the project to be created and then select it

### Step 2: Enable the Gmail API

1. In the Google Cloud Console, go to the "APIs & Services" > "Library" section
2. Search for "Gmail API"
3. Click on the Gmail API result
4. Click "ENABLE"

### Step 3: Configure the OAuth Consent Screen

1. Go to "APIs & Services" > "OAuth consent screen"
2. Select "External" user type (or "Internal" if you're using Google Workspace)
3. Click "CREATE"
4. Enter the required information:
   - App name (e.g., "Gmail Assistant")
   - User support email (your email)
   - Developer contact information (your email)
5. Click "SAVE AND CONTINUE"
6. On the Scopes page, click "ADD OR REMOVE SCOPES"
7. In the filter box, search for "gmail" and select these scopes:
   - `https://www.googleapis.com/auth/gmail.modify`
   - `https://www.googleapis.com/auth/gmail.compose`
   - `https://www.googleapis.com/auth/gmail.send`
8. Click "UPDATE" and then "SAVE AND CONTINUE"
9. On the Test users page, click "ADD USERS"
10. Enter your own Google email address
11. Click "ADD" and then "SAVE AND CONTINUE"
12. Review your app registration summary and click "BACK TO DASHBOARD"

### Step 4: Create OAuth Client ID

1. Go to "APIs & Services" > "Credentials"
2. Click "CREATE CREDENTIALS" at the top of the page
3. Select "OAuth client ID" from the dropdown menu
4. For Application type, select "Desktop app"
5. Name your OAuth client (e.g., "Gmail Assistant Desktop Client")
6. Click "CREATE"
7. Download the JSON file and save it as `credentials.json` in your project directory

### Step 5: Configure Redirect URIs

1. In the Credentials page, find your OAuth client ID and click on the pencil icon to edit
2. Under "Authorized redirect URIs", click "ADD URI"
3. Enter exactly: `http://localhost:8080`
4. Click "SAVE"

## Hugging Face Integration

### Getting a Hugging Face Token

1. Go to [Hugging Face](https://huggingface.co/) and sign up or log in
2. Navigate to [Settings > Access Tokens](https://huggingface.co/settings/tokens)
3. Click "New token"
4. Give your token a name (e.g., "Gmail Assistant")
5. Select "Read" access
6. Click "Generate token"
7. Copy the generated token - you'll need it when running the application

### Supported Models

The default model is `Qwen/Qwen2.5-0.5B-Instruct`, but you can modify the code to use other models. Popular alternatives include:

- `gpt2` - A smaller model that works well for simple tasks
- `facebook/blenderbot-400M-distill` - Good for conversation-like emails
- `EleutherAI/gpt-neo-125m` - A smaller open-source GPT model

## Usage

1. Run the script:
   ```bash
   python Automation.py
   ```

2. When prompted, enter your Hugging Face token (or press Enter to skip)
3. The script will check for GPU availability and use it if present
4. Emails will be processed according to importance and automatic responses will be generated

## Troubleshooting

### GPU Issues

If your GPU is not being detected:

1. Verify your hardware and drivers:
   ```bash
   # Windows
   nvidia-smi
   ```

2. Check PyTorch CUDA support:
   ```python
   import torch
   print(f"CUDA available: {torch.cuda.is_available()}")
   ```

3. Reinstall PyTorch with the correct CUDA version:
   ```bash
   pip uninstall -y torch torchvision torchaudio
   pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu126
   ```

### OAuth Authentication Issues

If you encounter a "redirect_uri_mismatch" error:

1. Delete the `token.pickle` file if it exists
2. Double-check that you've added exactly `http://localhost:8080` as an authorized redirect URI
3. Make sure you're using the correct `credentials.json` file
4. Try running the application again

### Model Loading Issues

If you encounter errors loading Hugging Face models:

1. Check your internet connection
2. Verify that your Hugging Face token is valid
3. Try a smaller model if you have limited RAM

## Security Notes

- Never hardcode your email password or API keys in the script
- Keep your `credentials.json` file and `token.pickle` file secure
- Use environment variables or secure configuration files for any sensitive information
- Consider using OAuth2 for more secure authentication (as implemented in this tool)
