# auth_helper.py
import os
import pickle
import json
import sys
import streamlit as st
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.oauth2 import service_account
import requests

def get_gmail_service():
    """Handles authentication for both local and Streamlit Cloud environments."""
    creds = None
    token_path = 'token.pickle'
    
    # Check if running on Streamlit Cloud or locally
    is_streamlit = 'streamlit' in globals() or 'streamlit._is_running' in sys.modules
    
    try:
        # Load existing credentials from token.pickle if available
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
                st.session_state['auth_status'] = "Using existing credentials"
        
        # If credentials are not valid, refresh or get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                st.session_state['auth_status'] = "Refreshing expired token"
                try:
                    creds.refresh(Request())
                    st.session_state['auth_status'] = "Token refreshed successfully"
                except Exception as refresh_error:
                    st.session_state['auth_status'] = f"Token refresh failed: {str(refresh_error)}"
                    # Token refresh failed, need to authenticate again
                    creds = None
            
            # Need to get new credentials
            if not creds:
                # For Streamlit Cloud, use credentials from secrets
                if is_streamlit:
                    try:
                        st.session_state['auth_status'] = "Checking for Google credentials in Streamlit secrets"
                        if 'google' in st.secrets and 'credentials_json' in st.secrets['google']:
                            # Create credentials.json from secrets
                            credentials_json = st.secrets['google']['credentials_json']
                            st.session_state['auth_status'] = "Found credentials in secrets, creating credentials.json"
                            
                            # Check if credentials_json is valid JSON
                            try:
                                json.loads(credentials_json)
                            except json.JSONDecodeError as json_error:
                                st.session_state['auth_status'] = f"Invalid JSON in credentials: {str(json_error)}"
                                st.error("⚠️ Your Google credentials contain invalid JSON. Please check your secrets.toml file.")
                                return None
                            
                            # Write credentials to file
                            with open('credentials.json', 'w') as f:
                                f.write(credentials_json)
                            
                            # Use redirect that works on Streamlit Cloud
                            st.session_state['auth_status'] = "Starting OAuth flow with Streamlit Cloud redirect"
                            flow = InstalledAppFlow.from_client_secrets_file(
                                'credentials.json', 
                                ['https://www.googleapis.com/auth/gmail.modify',
                                'https://www.googleapis.com/auth/gmail.compose',
                                'https://www.googleapis.com/auth/gmail.send'],
                                redirect_uri='https://share.streamlit.io/auth'
                            )
                            
                            # Set authorization prompt to 'consent' to always prompt
                            auth_url, _ = flow.authorization_url(
                                prompt='consent',
                                access_type='offline',
                                include_granted_scopes='true'
                            )
                            
                            # In Streamlit, we need to handle the redirect manually
                            st.markdown(f"""
                            ### Gmail Authorization Required
                            
                            Click the link below to authorize Emmy to access your Gmail account:
                            
                            [Authorize Gmail Access]({auth_url})
                            
                            After authorization, you will be redirected back to this app.
                            """)
                            
                            # Check if auth code is in query params (after redirect)
                            query_params = st.experimental_get_query_params()
                            if 'code' in query_params:
                                auth_code = query_params['code'][0]
                                st.session_state['auth_status'] = "Received auth code, exchanging for token"
                                try:
                                    flow.fetch_token(code=auth_code)
                                    creds = flow.credentials
                                    st.session_state['auth_status'] = "OAuth flow completed successfully"
                                    # Clear the URL parameters
                                    st.experimental_set_query_params()
                                except Exception as token_error:
                                    st.session_state['auth_status'] = f"Error exchanging auth code: {str(token_error)}"
                                    st.error(f"⚠️ Failed to exchange authorization code: {str(token_error)}")
                                    return None
                            else:
                                st.session_state['auth_status'] = "Waiting for authorization code"
                                st.info("Please complete the authorization process in the opened browser window.")
                                return None
                        else:
                            st.error("⚠️ Google credentials not found in Streamlit secrets")
                            st.session_state['auth_status'] = "No Google credentials in secrets"
                            return None
                    except Exception as e:
                        st.error(f"⚠️ Error with Streamlit secrets: {str(e)}")
                        st.session_state['auth_status'] = f"Error with Streamlit secrets: {str(e)}"
                        return None
                else:
                    # Local development flow
                    st.session_state['auth_status'] = "Starting local OAuth flow"
                    try:
                        flow = InstalledAppFlow.from_client_secrets_file(
                            'credentials.json', 
                            ['https://www.googleapis.com/auth/gmail.modify',
                            'https://www.googleapis.com/auth/gmail.compose',
                            'https://www.googleapis.com/auth/gmail.send'],
                            redirect_uri='http://localhost:8080'
                        )
                        creds = flow.run_local_server(port=8080)
                        st.session_state['auth_status'] = "Local OAuth flow completed successfully"
                    except Exception as local_auth_error:
                        st.session_state['auth_status'] = f"Local OAuth flow failed: {str(local_auth_error)}"
                        if "redirect_uri_mismatch" in str(local_auth_error):
                            st.error("⚠️ Redirect URI mismatch. Make sure http://localhost:8080 is added to your Google Cloud OAuth credentials.")
                        else:
                            st.error(f"⚠️ Authentication failed: {str(local_auth_error)}")
                        return None
                
                # Save credentials for next run
                if creds:
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                    st.session_state['auth_status'] = "Credentials saved to token.pickle"
        
        try:
            service = build('gmail', 'v1', credentials=creds)
            st.session_state['auth_status'] = "Gmail service built successfully"
            return service
        except Exception as service_error:
            st.session_state['auth_status'] = f"Error building Gmail service: {str(service_error)}"
            st.error(f"⚠️ Failed to initialize Gmail service: {str(service_error)}")
            return None
    
    except Exception as general_error:
        st.session_state['auth_status'] = f"General error: {str(general_error)}"
        st.error(f"⚠️ Authentication error: {str(general_error)}")
        return None

def get_auth_status():
    """Get the current authentication status for display"""
    return st.session_state.get('auth_status', 'Not started')