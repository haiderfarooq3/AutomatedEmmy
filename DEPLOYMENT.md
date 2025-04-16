# Deploying Emmy - Your Gmail Assistant

This guide will walk you through the process of deploying your Gmail automation application using Streamlit, both locally and on Streamlit Cloud.

## Table of Contents
1. [Prerequisites](#prerequisites)
2. [Local Deployment](#local-deployment)
3. [Streamlit Cloud Deployment](#streamlit-cloud-deployment)
4. [Handling Authentication in Deployment](#handling-authentication-in-deployment)
5. [Troubleshooting](#troubleshooting)

## Prerequisites

Before deploying, ensure you have:

- Python 3.10 or higher installed
- A valid Gmail account with API access
- An OpenAI API key
- Git installed (for Streamlit Cloud deployment)

## Local Deployment

### Step 1: Set Up Your Environment

1. **Clone or download the repository** to your local machine if you haven't already.

2. **Install required packages**:
   ```bash
   python setup_py310.py
   ```
   Or install from requirements.txt:
   ```bash
   pip install -r requirements.txt
   ```

### Step 2: Configure Your Credentials

1. **Gmail API Credentials**:
   - Make sure you have a valid `credentials.json` file in the project root directory.
   - This file should contain your OAuth 2.0 client credentials from the Google Developer Console.
   - If you don't have this file yet, follow these steps:
     - Go to [Google Cloud Console](https://console.cloud.google.com/)
     - Create a new project or select an existing one
     - Navigate to "APIs & Services" > "Credentials"
     - Click "Create Credentials" > "OAuth client ID"
     - Set application type to "Web application"
     - Add authorized redirect URIs: `http://localhost:8080`
     - Download the JSON file and save it as `credentials.json` in your project directory

2. **OpenAI API Key**:
   - You have two options:
     - **Option A**: Update the `.env` file with your OpenAI API key:
       ```
       OPENAI_API_KEY=your_api_key_here
       OPENAI_MODEL=gpt-3.5-turbo
       ```
     - **Option B**: Update `.streamlit/secrets.toml` with your OpenAI API key (already configured)

### Step 3: Run Locally

1. **Start the Streamlit app**:
   ```bash
   streamlit run streamlit_app.py
   ```

2. **Access the application** in your browser:
   - The app should automatically open in your default browser
   - If not, go to `http://localhost:8501`

3. **Authenticate with Gmail**:
   - Click "Authenticate Emmy with Gmail" in the sidebar
   - Follow the OAuth flow in the browser popup
   - Grant the requested permissions

Your application is now running locally!

## Streamlit Cloud Deployment

Streamlit Cloud offers free hosting for Streamlit applications connected to public GitHub repositories.

### Step 1: Prepare Your Repository

1. **Create a GitHub repository**:
   - Create a new repository on GitHub
   - Initialize Git in your project folder if you haven't already:
     ```bash
     git init
     ```
   - Add your files, commit them, and push to GitHub:
     ```bash
     git add .
     git commit -m "Initial commit"
     git branch -M main
     git remote add origin https://github.com/yourusername/your-repo-name.git
     git push -u origin main
     ```

2. **Important**: Update your `.gitignore` file to prevent sensitive information from being pushed to GitHub:
   - Make sure it includes:
     ```
     token.pickle
     credentials.json
     .env
     *.key
     ```

### Step 2: Set Up Streamlit Cloud

1. **Sign up for Streamlit Cloud**:
   - Go to [Streamlit Cloud](https://streamlit.io/cloud)
   - Sign in with your GitHub account

2. **Deploy your app**:
   - Click "New app"
   - Select your repository, branch (main), and the path to the main file (`streamlit_app.py`)
   - Click "Deploy"

### Step 3: Configure Secrets in Streamlit Cloud

Since your local secrets won't be uploaded to GitHub, you need to configure them in Streamlit Cloud:

1. **Add secrets**:
   - Go to your app's settings in Streamlit Cloud
   - Scroll down to "Secrets"
   - Add the following secrets (the same format as your `.streamlit/secrets.toml`):
     ```toml
     [openai]
     api_key = "your_openai_api_key"
     model = "gpt-3.5-turbo"

     [google]
     credentials_json = """your_google_credentials_json"""
     ```

2. **Save your changes**.

### Step 4: Additional Configuration for Streamlit Cloud

1. **Set up OAuth redirect URLs**:
   - Go back to [Google Cloud Console](https://console.cloud.google.com/)
   - Navigate to your project's OAuth consent screen
   - Add an authorized redirect URI: `https://share.streamlit.io/auth`
   - Save the changes

2. **Check deployment**:
   - Your app should now be deployed at `https://share.streamlit.io/yourusername/your-repo-name/main/streamlit_app.py`
   - The first time you run the app, you'll need to authenticate with Gmail again

## Handling Authentication in Deployment

When deploying on Streamlit Cloud, token persistence works differently than in local development:

### Preparing Authentication for Deployment

1. **First authenticate locally**:
   - Run the app locally and authenticate with your Gmail account
   - This will create the necessary `token.pickle` file

2. **Update your Streamlit secrets with token information**:
   ```bash
   python update_streamlit_secrets.py --update-token
   ```
   This will extract the token information from `token.pickle` and add it to your `.streamlit/secrets.toml` file.

3. **Export all secrets for deployment**:
   ```bash
   python update_streamlit_secrets.py --export-secrets
   ```
   This creates a `streamlit_secrets_for_deployment.toml` file with all the necessary secrets.

4. **Add secrets to Streamlit Cloud**:
   - Copy the contents of `streamlit_secrets_for_deployment.toml`
   - Go to your app's settings in Streamlit Cloud
   - Paste the content into the Secrets section
   - Click "Save"

This setup allows Emmy to authenticate without needing local token.pickle or credentials.json files on the deployed environment.

### Understanding the Authentication Flow

- **Local deployment**: Uses `credentials.json` and `token.pickle` files
- **Streamlit Cloud**: Uses the credentials and token information from Streamlit secrets
- In both cases, the app needs to be authorized with your Gmail account

## Troubleshooting

### Common Issues

1. **Authentication fails**:
   - Make sure your redirect URIs are correctly set in Google Cloud Console
   - For Streamlit Cloud, ensure `https://share.streamlit.io/auth` is added
   - For local deployment, ensure `http://localhost:8080` is added

2. **"OpenAI API key not valid" error**:
   - Check that you've set the correct API key in Streamlit secrets
   - Verify your OpenAI account is in good standing with sufficient credits

3. **Gmail API errors**:
   - Ensure the Gmail API is enabled in your Google Cloud project
   - Check that your OAuth consent screen is configured properly
   - Make sure you've granted the necessary permissions during authentication

4. **Application crashes on Streamlit Cloud**:
   - Check the logs in Streamlit Cloud dashboard
   - Ensure all dependencies are listed in `requirements.txt`
   - Make sure you're not using any local file paths that wouldn't exist on the server

### Accessing Logs

- **Local**: Logs appear in the terminal where you ran the Streamlit command
- **Streamlit Cloud**: View logs in the Streamlit Cloud dashboard under your app settings

### Getting Help

If you encounter issues that aren't covered here:
- Check the [Streamlit documentation](https://docs.streamlit.io/)
- Visit the [Streamlit community forum](https://discuss.streamlit.io/)
- For Gmail API issues, refer to the [Google API documentation](https://developers.google.com/gmail/api)

## Advanced: Using Custom Domains

If you want to use a custom domain with Streamlit Cloud:

1. Upgrade to Streamlit Cloud Teams or Enterprise tier
2. Follow the instructions in the Streamlit Cloud dashboard to set up your domain
3. Update your OAuth redirect URIs in Google Cloud Console to include your custom domain

## Next Steps

- Set up monitoring for your application
- Implement automated testing
- Consider adding user feedback mechanisms
- Explore Streamlit Components for enhanced UI capabilities
