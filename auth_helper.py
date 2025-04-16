# auth_helper.py
import os
import pickle
import json
import sys
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

def get_gmail_service():
    """Handles authentication for both local and Streamlit Cloud environments."""
    creds = None
    token_path = 'token.pickle'
    
    # Check if running on Streamlit Cloud or locally
    is_streamlit = 'streamlit' in globals() or 'streamlit._is_running' in sys.modules
    
    # Load existing credentials from token.pickle if available
    if os.path.exists(token_path):
        with open(token_path, 'rb') as token:
            creds = pickle.load(token)
    
    # If credentials are not valid, refresh or get new ones
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # For Streamlit Cloud, use credentials from secrets
            if is_streamlit:
                try:
                    if 'google' in st.secrets and 'credentials_json' in st.secrets['google']:
                        # Create credentials.json from secrets
                        credentials_json = st.secrets['google']['credentials_json']
                        with open('credentials.json', 'w') as f:
                            f.write(credentials_json)
                        
                        # Use redirect that works on Streamlit Cloud
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', 
                            ['https://www.googleapis.com/auth/gmail.modify',
                            'https://www.googleapis.com/auth/gmail.compose',
                            'https://www.googleapis.com/auth/gmail.send'],
                            redirect_uri='https://share.streamlit.io/auth'
                        )
                        creds = flow.run_local_server(port=8080)
                    else:
                        st.error("Google credentials not found in Streamlit secrets")
                        return None
                except Exception as e:
                    st.error(f"Error with Streamlit secrets: {e}")
                    return None
            else:
                # Local development flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    'credentials.json', 
                    ['https://www.googleapis.com/auth/gmail.modify',
                    'https://www.googleapis.com/auth/gmail.compose',
                    'https://www.googleapis.com/auth/gmail.send'],
                    redirect_uri='http://localhost:8080'
                )
                creds = flow.run_local_server(port=8080)
            
            # Save credentials for next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
    
    service = build('gmail', 'v1', credentials=creds)
    return service