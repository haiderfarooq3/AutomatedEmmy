# auth_helper.py
import os
import pickle
import json
import sys
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials
from google.oauth2 import service_account
import base64

def is_deployed():
    """Check if running on Streamlit Cloud."""
    return 'STREAMLIT_SHARING_MODE' in os.environ or 'STREAMLIT_RUN_TARGET' in os.environ

def get_gmail_service():
    """Handles authentication for both local and Streamlit Cloud environments."""
    creds = None
    token_path = 'token.pickle'
    
    # Check if running on Streamlit Cloud or locally
    is_streamlit = 'streamlit' in globals() or 'streamlit._is_running' in sys.modules
    
    # Track authentication status for debugging
    if is_streamlit and 'auth_status' not in st.session_state:
        st.session_state['auth_status'] = "Starting authentication"
    
    try:
        # When deployed on Streamlit Cloud, use secrets directly
        if is_streamlit and is_deployed():
            if 'auth_status' in st.session_state:
                st.session_state['auth_status'] = "Running in Streamlit Cloud deployment mode"
            
            # Check if we have token information in session state
            if 'gmail_token' in st.session_state and st.session_state['gmail_token']:
                if 'auth_status' in st.session_state:
                    st.session_state['auth_status'] = "Using existing token from session state"
                # Create credentials from stored token info
                creds = Credentials.from_authorized_user_info(
                    st.session_state['gmail_token']
                )
            else:
                if 'auth_status' in st.session_state:
                    st.session_state['auth_status'] = "No token in session state, checking secrets"
                
                # Check if credentials JSON is in secrets
                if 'google' in st.secrets and 'credentials_json' in st.secrets['google']:
                    # Create a temporary credentials file from secrets
                    if 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "Creating OAuth flow from secrets"
                    
                    # Check if we have a token in secrets
                    if 'google' in st.secrets and 'token_json' in st.secrets['google']:
                        try:
                            # Try to create credentials from the token in secrets
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = "Creating credentials from token in secrets"
                            token_info = json.loads(st.secrets['google']['token_json'])
                            creds = Credentials.from_authorized_user_info(token_info)
                            
                            # Store token in session state for future use
                            st.session_state['gmail_token'] = token_info
                            
                            # If token is expired and has refresh token, refresh it
                            if creds and creds.expired and creds.refresh_token:
                                if 'auth_status' in st.session_state:
                                    st.session_state['auth_status'] = "Refreshing expired token"
                                creds.refresh(Request())
                                # Update session state with refreshed token
                                st.session_state['gmail_token'] = json.loads(creds.to_json())
                        except Exception as e:
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = f"Error loading token from secrets: {str(e)}"
                            creds = None
                    
                    # If still no valid credentials, start OAuth flow
                    if not creds or not creds.valid:
                        # Load credentials from secrets
                        credentials_json = st.secrets['google']['credentials_json']
                        
                        # Use a temporary file to hold credentials
                        with open('temp_credentials.json', 'w') as f:
                            f.write(credentials_json)
                        
                        # Start OAuth flow with Streamlit-compatible redirect
                        if 'auth_status' in st.session_state:
                            st.session_state['auth_status'] = "Starting OAuth flow with temp credentials"
                        
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'temp_credentials.json', 
                            ['https://www.googleapis.com/auth/gmail.modify',
                             'https://www.googleapis.com/auth/gmail.compose',
                             'https://www.googleapis.com/auth/gmail.send'],
                            redirect_uri='https://share.streamlit.io/auth'
                        )
                        
                        # Generate authorization URL
                        auth_url, _ = flow.authorization_url(
                            prompt='consent',
                            access_type='offline',
                            include_granted_scopes='true'
                        )
                        
                        # Display authorization URL
                        st.markdown(f"""
                        ### Gmail Authorization Required
                        
                        Click the link below to authorize access to your Gmail account:
                        
                        [Authorize Gmail Access]({auth_url})
                        
                        After authorization, you will be redirected back to this app.
                        """)
                        
                        # Check for authorization code in query params (after redirect)
                        query_params = st.experimental_get_query_params()
                        if 'code' in query_params:
                            auth_code = query_params['code'][0]
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = "Received auth code, fetching token"
                            
                            try:
                                # Exchange authorization code for token
                                flow.fetch_token(code=auth_code)
                                creds = flow.credentials
                                
                                # Store token in session state
                                token_json = creds.to_json()
                                st.session_state['gmail_token'] = json.loads(token_json)
                                
                                if 'auth_status' in st.session_state:
                                    st.session_state['auth_status'] = "Successfully obtained token"
                                
                                # Clean up temporary file
                                if os.path.exists('temp_credentials.json'):
                                    os.remove('temp_credentials.json')
                                    
                                # Clear URL parameters to avoid reprocessing the code
                                st.experimental_set_query_params()
                            except Exception as e:
                                if 'auth_status' in st.session_state:
                                    st.session_state['auth_status'] = f"Error exchanging auth code: {str(e)}"
                                st.error(f"Error in authorization process: {str(e)}")
                                # Clean up temporary file
                                if os.path.exists('temp_credentials.json'):
                                    os.remove('temp_credentials.json')
                                return None
                        else:
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = "Waiting for authorization"
                            # Clean up temporary file
                            if os.path.exists('temp_credentials.json'):
                                os.remove('temp_credentials.json')
                            return None
                else:
                    if 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "No Google credentials found in secrets"
                    st.error("❌ Google credentials not found in Streamlit secrets")
                    return None
        else:
            # Local development mode - use token.pickle if available
            if os.path.exists(token_path):
                if is_streamlit and 'auth_status' in st.session_state:
                    st.session_state['auth_status'] = "Loading credentials from token.pickle"
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If credentials are not valid, refresh or get new ones
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    if is_streamlit and 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "Refreshing expired token"
                    creds.refresh(Request())
                else:
                    # Local flow for new credentials
                    if is_streamlit and 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "Starting local OAuth flow"
                    
                    if not os.path.exists('credentials.json'):
                        if is_streamlit:
                            st.error("credentials.json file not found. Please create it from your Google Cloud Console.")
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = "credentials.json file not found"
                        else:
                            print("Error: credentials.json file not found")
                        return None
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json', 
                        ['https://www.googleapis.com/auth/gmail.modify',
                         'https://www.googleapis.com/auth/gmail.compose',
                         'https://www.googleapis.com/auth/gmail.send'],
                        redirect_uri='http://localhost:8080'
                    )
                    creds = flow.run_local_server(port=8080)
                
                # Save credentials for next run (only in local mode)
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
        
        # Create Gmail API service
        service = build('gmail', 'v1', credentials=creds)
        if is_streamlit and 'auth_status' in st.session_state:
            st.session_state['auth_status'] = "Gmail service created successfully"
        return service
    
    except Exception as e:
        error_msg = f"Authentication error: {str(e)}"
        if is_streamlit:
            st.error(error_msg)
            if 'auth_status' in st.session_state:
                st.session_state['auth_status'] = error_msg
        else:
            print(error_msg)
        return None

def get_auth_status():
    """Get the current authentication status for display"""
    return st.session_state.get('auth_status', 'Not started')