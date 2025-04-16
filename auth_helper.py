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

def is_deployed():
    """Check if running on Streamlit Cloud."""
    return 'STREAMLIT_SHARING_MODE' in os.environ or 'STREAMLIT_RUN_TARGET' in os.environ

def get_gmail_service():
    """Handles authentication for Gmail API.
    
    In deployment mode: Exclusively uses Streamlit secrets and session state.
    In local mode: Falls back to token.pickle and credentials.json files.
    """
    creds = None
    
    # Check if running in Streamlit
    is_streamlit = 'streamlit' in globals() or 'streamlit._is_running' in sys.modules
    
    # Initialize auth_status in session state if running in Streamlit
    if is_streamlit and 'auth_status' not in st.session_state:
        st.session_state['auth_status'] = "Starting authentication"
    
    # Detect if running in deployed environment
    deployed = is_deployed()
    
    try:
        # DEPLOYED MODE: Use only Streamlit secrets and session state
        if deployed and is_streamlit:
            if 'auth_status' in st.session_state:
                st.session_state['auth_status'] = "Running in Streamlit Cloud deployment mode"
            
            # STEP 1: Check if we have credentials in session state first
            if 'gmail_credentials' in st.session_state and st.session_state['gmail_credentials']:
                if 'auth_status' in st.session_state:
                    st.session_state['auth_status'] = "Using credentials from session state"
                
                # Create credentials object from session state
                creds_info = st.session_state['gmail_credentials']
                creds = Credentials(
                    token=creds_info.get('token'),
                    refresh_token=creds_info.get('refresh_token'),
                    token_uri=creds_info.get('token_uri'),
                    client_id=creds_info.get('client_id'),
                    client_secret=creds_info.get('client_secret'),
                    scopes=creds_info.get('scopes')
                )
                
                # Refresh token if expired
                if creds.expired and creds.refresh_token:
                    if 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "Refreshing token from session state"
                    creds.refresh(Request())
                    
                    # Update session state with refreshed credentials
                    st.session_state['gmail_credentials'] = {
                        'token': creds.token,
                        'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri,
                        'client_id': creds.client_id,
                        'client_secret': creds.client_secret,
                        'scopes': creds.scopes,
                        'expiry': creds.expiry.isoformat() if creds.expiry else None
                    }
            
            # STEP 2: If not in session state, check if token exists in secrets
            elif 'google' in st.secrets and 'token_json' in st.secrets['google'] and st.secrets['google']['token_json'].strip() != '{}':
                if 'auth_status' in st.session_state:
                    st.session_state['auth_status'] = "Using token from Streamlit secrets"
                
                try:
                    # Parse the token from secrets
                    token_data = json.loads(st.secrets['google']['token_json'])
                    if token_data:  # Check if token data is not empty
                        # Create credentials from token data
                        creds = Credentials.from_authorized_user_info(token_data)
                        
                        # Store in session state for future use
                        st.session_state['gmail_credentials'] = {
                            'token': creds.token,
                            'refresh_token': creds.refresh_token,
                            'token_uri': creds.token_uri,
                            'client_id': creds.client_id,
                            'client_secret': creds.client_secret,
                            'scopes': creds.scopes,
                            'expiry': creds.expiry.isoformat() if creds.expiry else None
                        }
                        
                        # Refresh if expired
                        if creds.expired and creds.refresh_token:
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = "Refreshing token from secrets"
                            creds.refresh(Request())
                            
                            # Update session state with refreshed credentials
                            st.session_state['gmail_credentials'] = {
                                'token': creds.token,
                                'refresh_token': creds.refresh_token,
                                'token_uri': creds.token_uri,
                                'client_id': creds.client_id,
                                'client_secret': creds.client_secret,
                                'scopes': creds.scopes,
                                'expiry': creds.expiry.isoformat() if creds.expiry else None
                            }
                except Exception as e:
                    if 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = f"Error loading token from secrets: {str(e)}"
                    creds = None
            
            # STEP 3: If no valid credentials yet, start OAuth flow using credentials from secrets
            if not creds or not creds.valid:
                if 'google' in st.secrets and 'credentials_json' in st.secrets['google']:
                    if 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "Starting OAuth flow from secrets credentials"
                    
                    # Get credentials from secrets
                    credentials_data = json.loads(st.secrets['google']['credentials_json'])
                    
                    # Extract client info
                    client_id = credentials_data['web']['client_id']
                    client_secret = credentials_data['web']['client_secret']
                    redirect_uri = 'https://share.streamlit.io/auth'
                    auth_uri = credentials_data['web']['auth_uri']
                    token_uri = credentials_data['web']['token_uri']
                    
                    # Create a flow object directly without a file
                    from google_auth_oauthlib.helpers import session_from_client_config
                    
                    client_config = {
                        "web": {
                            "client_id": client_id,
                            "client_secret": client_secret,
                            "auth_uri": auth_uri,
                            "token_uri": token_uri,
                            "redirect_uris": [redirect_uri]
                        }
                    }
                    
                    scopes = [
                        'https://www.googleapis.com/auth/gmail.modify',
                        'https://www.googleapis.com/auth/gmail.compose',
                        'https://www.googleapis.com/auth/gmail.send'
                    ]
                    
                    flow = InstalledAppFlow.from_client_config(
                        client_config, 
                        scopes=scopes,
                        redirect_uri=redirect_uri
                    )
                    
                    # Generate auth URL
                    auth_url, _ = flow.authorization_url(
                        access_type='offline',
                        include_granted_scopes='true',
                        prompt='consent'
                    )
                    
                    # Show authorization link to user
                    st.markdown(f"""
                    ### Gmail Authorization Required
                    
                    Click the link below to authorize access to your Gmail account:
                    
                    [Authorize Gmail Access]({auth_url})
                    
                    After authorization, you will be redirected back to this app with a code parameter.
                    """)
                    
                    # Check for auth code in URL params after redirect
                    query_params = st.experimental_get_query_params()
                    if 'code' in query_params:
                        try:
                            auth_code = query_params['code'][0]
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = "Processing authorization code"
                            
                            # Exchange auth code for tokens
                            flow.fetch_token(code=auth_code)
                            creds = flow.credentials
                            
                            # Save credentials to session state for future use
                            st.session_state['gmail_credentials'] = {
                                'token': creds.token,
                                'refresh_token': creds.refresh_token,
                                'token_uri': creds.token_uri,
                                'client_id': creds.client_id,
                                'client_secret': creds.client_secret,
                                'scopes': creds.scopes,
                                'expiry': creds.expiry.isoformat() if creds.expiry else None
                            }
                            
                            # Clear URL parameters to avoid reprocessing
                            st.experimental_set_query_params()
                            
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = "Successfully obtained credentials"
                        except Exception as e:
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = f"Error processing auth code: {str(e)}"
                            st.error(f"Authentication error: {str(e)}")
                            return None
                    else:
                        if 'auth_status' in st.session_state:
                            st.session_state['auth_status'] = "Waiting for authorization"
                        # Don't continue until we get the auth code
                        return None
                else:
                    if 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "No Google credentials found in secrets"
                    st.error("Google API credentials not found in Streamlit secrets.")
                    return None
                    
        # LOCAL MODE: Use local files (only for development environment)
        else:
            token_path = 'token.pickle'
            
            # If running in Streamlit local mode, update status
            if is_streamlit and 'auth_status' in st.session_state:
                st.session_state['auth_status'] = "Running in local development mode"
            
            # Use token.pickle if available
            if os.path.exists(token_path):
                if is_streamlit and 'auth_status' in st.session_state:
                    st.session_state['auth_status'] = "Loading credentials from local token.pickle"
                with open(token_path, 'rb') as token:
                    creds = pickle.load(token)
            
            # If credentials are not valid, refresh or get new ones
            if not creds or not creds.valid:
                # Refresh token if possible
                if creds and creds.expired and creds.refresh_token:
                    if is_streamlit and 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "Refreshing expired local token"
                    creds.refresh(Request())
                # Otherwise, need new credentials
                else:
                    if is_streamlit and 'auth_status' in st.session_state:
                        st.session_state['auth_status'] = "Starting local OAuth flow"
                    
                    # Check if credentials.json exists
                    if not os.path.exists('credentials.json'):
                        error_msg = "credentials.json file not found in local directory"
                        if is_streamlit:
                            if 'auth_status' in st.session_state:
                                st.session_state['auth_status'] = error_msg
                            st.error(error_msg)
                        else:
                            print(f"Error: {error_msg}")
                        return None
                    
                    # Create flow from local file
                    flow = InstalledAppFlow.from_client_secrets_file(
                        'credentials.json',
                        [
                            'https://www.googleapis.com/auth/gmail.modify',
                            'https://www.googleapis.com/auth/gmail.compose',
                            'https://www.googleapis.com/auth/gmail.send'
                        ],
                        redirect_uri='http://localhost:8080'
                    )
                    
                    # Run local server for auth flow
                    creds = flow.run_local_server(port=8080)
                
                # Save credentials to file for future runs (only in local mode)
                with open(token_path, 'wb') as token:
                    pickle.dump(creds, token)
        
        # Finally, create and return the Gmail service with the obtained credentials
        service = build('gmail', 'v1', credentials=creds)
        
        if is_streamlit and 'auth_status' in st.session_state:
            st.session_state['auth_status'] = "Gmail service created successfully"
        
        return service
    
    except Exception as e:
        error_msg = f"Authentication error: {str(e)}"
        if is_streamlit:
            if 'auth_status' in st.session_state:
                st.session_state['auth_status'] = error_msg
            st.error(error_msg)
        else:
            print(error_msg)
        return None

def get_auth_status():
    """Get the current authentication status for display"""
    return st.session_state.get('auth_status', 'Not started')