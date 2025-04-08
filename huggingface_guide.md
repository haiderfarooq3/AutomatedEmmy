# Hugging Face Integration Guide

This guide explains how to set up and use Hugging Face models with the Gmail Automated Assistant.

## Getting a Hugging Face Token

1. Go to [Hugging Face](https://huggingface.co/) and sign up or log in
2. Navigate to [Settings > Access Tokens](https://huggingface.co/settings/tokens)
3. Click "New token"
4. Give your token a name (e.g., "Gmail Assistant")
5. Select "Read" access
6. Click "Generate token"
7. Copy the generated token - you'll need it when running the application

## Installing Required Libraries

Make sure you have all required dependencies installed:

```bash
pip install -r requirements.txt
```

## Using the Hugging Face Integration

When running the application, you'll be prompted to enter your Hugging Face token:

```bash
python Automation.py
```

Enter your token when prompted, or press Enter to skip using Hugging Face models.

## Supported Models

The default model is `Qwen/Qwen2.5-0.5B-Instruct`, but you can modify the code to use other models. Popular alternatives include:

- `gpt2` - A smaller model that works well for simple tasks
- `facebook/blenderbot-400M-distill` - Good for conversation-like emails
- `EleutherAI/gpt-neo-125m` - A smaller open-source GPT model

To change the model, modify the `setup_huggingface` function call in `main()`.

## Troubleshooting

### Model Loading Issues

If you encounter errors loading models:

1. Check your internet connection
2. Verify that your Hugging Face token is valid
3. Try a smaller model if you have limited RAM

### Authentication Issues

If you see authentication errors:

1. Make sure you're using a valid Hugging Face token
2. Run `huggingface-cli login` separately with your token
