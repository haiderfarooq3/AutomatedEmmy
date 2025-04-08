# Detailed OAuth Setup Guide

This guide will help you properly set up OAuth 2.0 credentials for the Gmail Automated Assistant.

## Step 1: Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on "Select a project" at the top of the page
3. Click "NEW PROJECT" in the window that appears
4. Enter a project name (e.g., "Gmail Assistant")
5. Click "CREATE"
6. Wait for the project to be created and then select it

## Step 2: Enable the Gmail API

1. In the Google Cloud Console, go to the "APIs & Services" > "Library" section
2. Search for "Gmail API"
3. Click on the Gmail API result
4. Click "ENABLE"

## Step 3: Configure the OAuth Consent Screen

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

## Step 4: Create OAuth Client ID

1. Go to "APIs & Services" > "Credentials"
2. Click "CREATE CREDENTIALS" at the top of the page
3. Select "OAuth client ID" from the dropdown menu
4. For Application type, select "Desktop app"
5. Name your OAuth client (e.g., "Gmail Assistant Desktop Client")
6. Click "CREATE"
7. You'll see a dialog showing your client ID and client secret. Click "OK"
8. Find your newly created client ID in the list and click the download icon (↓) on the right
9. Save the downloaded JSON file as `credentials.json` in your project directory

## Step 5: Configure Redirect URIs

This is a crucial step that resolves the "redirect_uri_mismatch" error:

1. In the Credentials page, find your OAuth client ID and click on the pencil icon to edit
2. Under "Authorized redirect URIs", click "ADD URI"
3. Enter exactly: `http://localhost:8080`
4. Click "SAVE"

## Step 6: Running the Application

1. Place the downloaded `credentials.json` file in the same directory as the `Automation.py` script
2. Run the application: `python Automation.py`
3. A browser window will open asking you to sign in with your Google account
4. After signing in, you'll see a page asking for permissions to access your Gmail
5. Click "Allow"
6. You should see a "The authentication flow has completed" message
7. The application will now run and a `token.pickle` file will be created to store your credentials

## Troubleshooting

If you still encounter the "redirect_uri_mismatch" error:

1. Delete the `token.pickle` file if it exists
2. Double-check that you've added exactly `http://localhost:8080` as an authorized redirect URI
3. Make sure you're using the correct `credentials.json` file
4. Try running the application again
