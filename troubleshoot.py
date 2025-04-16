import streamlit as st
import os
import sys
import json
import requests
from datetime import datetime
import platform

def run_troubleshooter():
    st.title("Emmy Authentication Troubleshooter")
    
    st.markdown("""
    This page helps diagnose issues with Gmail authentication. If you're having trouble
    connecting Emmy to your Gmail account, the information here can help identify the problem.
    """)
    
    # System Information
    st.header("System Information")
    system_info = {
        "OS": platform.system(),
        "OS Version": platform.version(),
        "Python Version": platform.python_version(),
        "Streamlit": st.__version__,
        "Time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Deployed": is_deployed()
    }
    
    st.json(system_info)
    
    # Authentication Status
    st.header("Authentication Status")
    
    auth_status = st.session_state.get('auth_status', 'Not started')
    st.info(f"Current status: {auth_status}")
    
    # Check if credentials files exist
    st.header("Credentials Files")
    
    creds_file = os.path.exists('credentials.json')
    token_file = os.path.exists('token.pickle')
    
    file_status = {
        "credentials.json": "✅ Found" if creds_file else "❌ Not found",
        "token.pickle": "✅ Found" if token_file else "❌ Not found"
    }
    
    st.json(file_status)
    
    # Check Streamlit secrets configuration
    st.header("Streamlit Secrets")
    
    has_secrets = False
    try:
        # Check if there are OpenAI secrets
        openai_key = st.secrets.get("openai", {}).get("api_key", "")
        has_openai = bool(openai_key)
        
        # Check if there are Google secrets
        google_creds = st.secrets.get("google", {}).get("credentials_json", "")
        has_google = bool(google_creds)
        
        has_secrets = has_openai and has_google
        
        secrets_status = {
            "OpenAI API Key": "✅ Found" if has_openai else "❌ Not found",
            "Google Credentials": "✅ Found" if has_google else "❌ Not found",
            "Google Credentials Length": len(google_creds) if has_google else 0
        }
        
        st.json(secrets_status)
    except Exception as e:
        st.error(f"Error accessing Streamlit secrets: {str(e)}")
    
    # Check redirect URIs in credentials
    if creds_file:
        st.header("OAuth Configuration")
        try:
            with open('credentials.json', 'r') as f:
                creds_data = json.load(f)
            
            redirect_uris = creds_data.get('web', {}).get('redirect_uris', [])
            
            uri_status = {
                "Has http://localhost:8080": "http://localhost:8080" in redirect_uris,
                "Has https://share.streamlit.io/auth": "https://share.streamlit.io/auth" in redirect_uris,
                "All URIs": redirect_uris
            }
            
            st.json(uri_status)
            
            # Validate required fields
            required_fields = ['client_id', 'client_secret', 'auth_uri', 'token_uri']
            missing_fields = [field for field in required_fields if field not in creds_data.get('web', {})]
            
            if missing_fields:
                st.warning(f"Missing required fields in credentials.json: {', '.join(missing_fields)}")
            else:
                st.success("All required OAuth fields are present in credentials.json")
                
        except Exception as e:
            st.error(f"Error parsing credentials.json: {str(e)}")
    
    # Common issues and solutions
    st.header("Common Issues & Solutions")
    
    with st.expander("Redirect URI Mismatch"):
        st.markdown("""
        ### Problem
        You see an error message about "redirect_uri_mismatch" during authentication.
        
        ### Solution
        1. Go to the [Google Cloud Console](https://console.cloud.google.com/)
        2. Navigate to "APIs & Services" > "Credentials"
        3. Find your OAuth 2.0 Client ID and click "Edit"
        4. Add these redirect URIs:
           - `http://localhost:8080` (for local testing)
           - `https://share.streamlit.io/auth` (for Streamlit Cloud)
        5. Save your changes and try again
        """)
    
    with st.expander("Invalid Client Secret"):
        st.markdown("""
        ### Problem
        You see an error about "invalid_client" or "invalid client secret".
        
        ### Solution
        1. Your credentials.json file may be corrupted or invalid
        2. Go to the Google Cloud Console and download a fresh copy of your credentials
        3. Replace your existing credentials.json file
        4. If using Streamlit Cloud, update your secrets.toml file with the new credentials
        """)
    
    with st.expander("Access Denied / Permission Issues"):
        st.markdown("""
        ### Problem
        You complete the OAuth flow but see "access denied" or permission errors.
        
        ### Solution
        1. Make sure the Gmail API is enabled in your Google Cloud project
        2. Check that your OAuth consent screen is configured properly
        3. Ensure all required scopes are added to your OAuth consent screen
        4. Try to authenticate again, making sure to approve all requested permissions
        """)
    
    with st.expander("Token Refresh Issues"):
        st.markdown("""
        ### Problem
        Authentication works initially but fails after some time.
        
        ### Solution
        1. Delete the existing `token.pickle` file
        2. Re-authenticate completely from the beginning
        3. Make sure your application has offline access by including `access_type='offline'` in your authorization URL
        """)
    
    # Network Connectivity Check
    st.header("Network Connectivity Check")
    
    if st.button("Check Google API Connectivity"):
        try:
            response = requests.get("https://www.googleapis.com/discovery/v1/apis/gmail/v1/rest", timeout=5)
            if response.status_code == 200:
                st.success("✅ Successfully connected to Google APIs")
            else:
                st.error(f"❌ Error connecting to Google APIs: HTTP {response.status_code}")
        except Exception as e:
            st.error(f"❌ Network error: {str(e)}")
    
    # Next steps
    st.header("Next Steps")
    
    st.markdown("""
    Based on the information above:
    
    1. If you see any **missing files** or **configuration issues**, fix those first
    2. If your OAuth configuration has issues with redirect URIs, update them in the Google Cloud Console
    3. If everything looks good but authentication still fails, try:
       - Clearing your browser cookies and cache
       - Using a private/incognito browser window
       - Deleting token.pickle and authenticating again
    """)
    
    # Reset authentication
    if st.button("Reset Authentication"):
        if os.path.exists('token.pickle'):
            os.remove('token.pickle')
            st.success("Authentication data reset. Please try authenticating again.")
        else:
            st.info("No authentication data to reset.")

def is_deployed():
    """Detect if running on Streamlit Cloud"""
    return 'STREAMLIT_SHARING_MODE' in os.environ or 'STREAMLIT_RUN_TARGET' in os.environ

if __name__ == "__main__":
    run_troubleshooter()
