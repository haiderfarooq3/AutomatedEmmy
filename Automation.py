__import__('streamlit').config.set_option('server.fileWatcherType', 'none')
import os
import sys  # Add missing sys import
import base64
import pickle
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import re
from datetime import datetime
import argparse
import torch
import openai
from dotenv import load_dotenv
import json
import time
import streamlit as st
from constants import CATEGORY_DISPLAY_NAMES, AUTO_RESPONSE_CATEGORIES, AUTO_RESPONSE_WAITING_TIMES

# Check if running in Streamlit
is_streamlit = 'streamlit' in sys.modules or 'streamlit._is_running' in sys.modules or 'st' in globals()

# Load environment variables from .env file for local development
load_dotenv()

# Get OpenAI API key from environment or Streamlit secrets
if is_streamlit or 'streamlit._is_running' in sys.modules:
    try:
        # Running in Streamlit - use secrets
        openai.api_key = st.secrets["openai"]["api_key"]
        OPENAI_MODEL = st.secrets["openai"]["model"]
    except Exception as e:
        print(f"Error loading from Streamlit secrets: {e}")
        # Fallback to environment variables
        openai.api_key = os.getenv("OPENAI_API_KEY")
        OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
else:
    # Running standalone - use environment variables
    openai.api_key = os.getenv("OPENAI_API_KEY")
    OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")

# Define the scopes required for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.modify',
          'https://www.googleapis.com/auth/gmail.compose',
          'https://www.googleapis.com/auth/gmail.send']

# Parse command line arguments
parser = argparse.ArgumentParser(description='Gmail Automation Tool')
parser.add_argument('--no-prompt', action='store_true', help='Run without interactive prompts')
parser.add_argument('--openai-key', type=str, help='OpenAI API key', default=None)
args = parser.parse_args()

class GmailAssistant:
    def __init__(self):
        self.service = self.authenticate()
        self.user_id = 'me'  # 'me' refers to the authenticated user
        self.user_email = None
        self.openai_model = OPENAI_MODEL
        self.config = self.load_config()
        
    def load_config(self):
        """Load configuration from Streamlit secrets or fallback to defaults."""
        try:
            if 'streamlit' in globals() or 'streamlit._is_running' in sys.modules:
                config = {}
                
                # Get auto_response settings from st.secrets
                if 'config' in st.secrets:
                    if 'auto_response' in st.secrets.config:
                        config['auto_response'] = {
                            'enabled': st.secrets.config.auto_response.get('enabled', False),
                            'categories': st.secrets.config.auto_response.get('categories', 'Priority Inbox Only'),
                            'waiting_time': st.secrets.config.auto_response.get('waiting_time', 5)
                        }
                    
                    # Get user settings from st.secrets
                    if 'user' in st.secrets.config:
                        config['user'] = {
                            'name': st.secrets.config.user.get('name', 'Emmy User'),
                            'custom_prompt': st.secrets.config.user.get('custom_prompt', None)
                        }
                
                # Return the constructed config
                return config
            
        except Exception as e:
            print(f"Error loading config from Streamlit secrets: {e}")
        
        # Return a default config if Streamlit secrets are not available
        return {
            "auto_response": {
                "enabled": False,
                "categories": "Priority Inbox Only",
                "waiting_time": 5
            },
            "user": {
                "name": "Emmy User",
                "custom_prompt": "Write a professional email response. Make sure proper formatting is done. DO NOT include the subject line in the email body as it will be added separately."
            }
        }
            
    def authenticate(self):
        """Authenticate with Gmail API through interactive OAuth flow."""
        try:
            # Check if we're in a Streamlit environment
            is_streamlit = (
                'streamlit' in sys.modules or 
                'streamlit._is_running' in sys.modules or 
                'st' in globals()
            )
            
            if is_streamlit:
                try:
                    import json
                    from google.oauth2.credentials import Credentials
                    from googleapiclient.discovery import build
                    from google.auth.transport.requests import Request
                    from google_auth_oauthlib.flow import Flow
                    
                    # Check if we have credentials in session state
                    if 'google_creds' in st.session_state and st.session_state.google_creds:
                        # Use existing credentials from session state
                        creds_data = st.session_state.google_creds
                        
                        # Create credentials object
                        creds = Credentials(
                            token=creds_data.get('token'),
                            refresh_token=creds_data.get('refresh_token'),
                            token_uri=creds_data.get('token_uri'),
                            client_id=creds_data.get('client_id'),
                            client_secret=creds_data.get('client_secret'),
                            scopes=creds_data.get('scopes')
                        )
                        
                        # Refresh token if expired
                        if creds.expired and creds.refresh_token:
                            creds.refresh(Request())
                            # Update token in session state
                            st.session_state.google_creds['token'] = creds.token
                        
                        # Build and return service
                        service = build('gmail', 'v1', credentials=creds)
                        return service
                    
                    # Check if we have a code in URL query parameters
                    if 'code' in st.query_params:
                        # We have an authorization code - exchange it for tokens
                        code = st.query_params['code']
                        
                        # Get client config from secrets
                        creds_json = json.loads(st.secrets["google"]["credentials_json"])
                        
                        # Create flow to exchange code for credentials
                        flow = Flow.from_client_config(
                            client_config=creds_json,
                            scopes=SCOPES,
                            redirect_uri=creds_json['web']['redirect_uris'][0]
                        )
                        
                        # Exchange code for tokens
                        flow.fetch_token(code=code)
                        creds = flow.credentials
                        
                        # Store credentials in session state
                        st.session_state.google_creds = {
                            'token': creds.token,
                            'refresh_token': creds.refresh_token, 
                            'token_uri': creds.token_uri,
                            'client_id': creds.client_id,
                            'client_secret': creds.client_secret,
                            'scopes': creds.scopes
                        }
                        
                        # Clear URL parameters
                        st.query_params.clear()
                        
                        # Build and return service
                        service = build('gmail', 'v1', credentials=creds)
                        return service
                    
                    # No credentials and no code - need to start OAuth flow
                    # Update session state but DON'T show UI here
                    st.session_state.auth_status = "need_oauth"
                    return None
                    
                except Exception as e:
                    print(f"[ERROR] Authentication error in Streamlit mode: {e}")
                    st.session_state.auth_status = f"error: {str(e)}"
                    return None
            else:
                # Standard authentication flow for local use
                creds = None
                token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
                
                if os.path.exists(token_path):
                    with open(token_path, 'rb') as token:
                        creds = pickle.load(token)
                
                # If credentials don't exist or are invalid, go through the flow
                if not creds or not creds.valid:
                    if creds and creds.expired and creds.refresh_token:
                        creds.refresh(Request())
                    else:
                        # Get credentials.json from current directory
                        creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
                        
                        if not os.path.exists(creds_path):
                            print(f"[ERROR] credentials.json not found at {creds_path}")
                            return None
                        
                        flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                        creds = flow.run_local_server(port=8080)
                    
                    # Save the credentials for the next run
                    with open(token_path, 'wb') as token:
                        pickle.dump(creds, token)
                
                # Build the service
                service = build('gmail', 'v1', credentials=creds)
                return service
                    
        except Exception as e:
            print(f"[ERROR] Authentication error: {e}")
            return None

    def get_unread_emails(self, max_results=10):
        """Get a list of unread emails."""
        try:
            response = self.service.users().messages().list(
                userId=self.user_id,
                q='is:unread',
                maxResults=max_results
            ).execute()
            
            if 'messages' not in response:
                return []
            
            messages = []
            for msg in response['messages']:
                message = self.service.users().messages().get(
                    userId=self.user_id,
                    id=msg['id'],
                    format='full'
                ).execute()
                
                messages.append(message)
                
            return messages
        except Exception as e:
            print(f'Error retrieving emails: {e}')
            return []
    
    def extract_email_info(self, message):
        """Extract subject, sender, and content from an email message."""
        headers = message['payload']['headers']
        subject = next((h['value'] for h in headers if h['name'] == 'Subject'), 'No Subject')
        sender = next((h['value'] for h in headers if h['name'] == 'From'), 'Unknown Sender')
        
        # Extract email body
        parts = message['payload'].get('parts', [])
        body = ''
        
        if 'body' in message['payload'] and 'data' in message['payload']['body']:
            # Handle single part messages
            body = base64.urlsafe_b64decode(message['payload']['body']['data']).decode('utf-8')
        elif parts:
            # Handle multipart messages
            for part in parts:
                if part.get('mimeType') == 'text/plain' and 'data' in part.get('body', {}):
                    body = base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
                    break
        
        return {
            'id': message['id'],
            'subject': subject,
            'sender': sender,
            'body': body,
            'date': self._get_date(headers)
        }
    
    def _get_date(self, headers):
        """Extract date from email headers."""
        date_str = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        try:
            if date_str:
                # This is a simple conversion, might need to be more robust for different date formats
                return datetime.strptime(date_str.split(' +')[0], '%a, %d %b %Y %H:%M:%S')
        except Exception:
            pass
        return datetime.now()
    
    def sort_emails(self, max_results=20):
        """Sort emails into categories based on advanced rule-based logic."""
        categories = {
            'priority_inbox': [],
            'main_inbox': [],
            'urgent_alerts': [],
            'basic_alerts': [],
            'fyi_cc': [],
            'billing_finance': [],
            'scheduling_calendars': [],
            'marketing_promotions': [],
            'team_internal': [],
            'projects_clients': [],
            'needs_review': [],
            'rules_in_training': []
        }
        
        unread_emails = self.get_unread_emails(max_results=max_results)
        
        for email in unread_emails:
            email_info = self.extract_email_info(email)
            classifications = self._classify_email(email_info)
            
            # Debug statement to print classifications for specific subjects
            if "warning" in email_info['subject'].lower() or "error" in email_info['subject'].lower() or "critical" in email_info['subject'].lower():
                print(f"Classification for '{email_info['subject']}': {classifications}")
            
            # If email matches multiple categories, use the highest confidence one
            if classifications:
                best_match = max(classifications, key=lambda x: x[1])
                category, confidence = best_match
                
                # If confidence is too low, put in needs_review
                if confidence < 0.6:
                    categories['needs_review'].append(email_info)
                else:
                    categories[category].append(email_info)
            else:
                # If no classification matches, put in needs_review
                categories['needs_review'].append(email_info)
        
        return categories
    
    def _classify_email(self, email_info):
        """
        Analyze email subject and return list of (category, confidence) tuples based on keyword matching.
        """
        classifications = []
        subject = email_info['subject'].lower()
        
        # Define keywords for each category
        category_keywords = {
            'priority_inbox': ['follow up', 'question', 'need', 'asap', 'approve', 'feedback', 'waiting on', 'deadline', 'important'],
            'main_inbox': ['update', 'information', 'hello', 'hi', 'greetings', 'thanks', 'thank you'],
            'urgent_alerts': ['warning', 'critical', 'error', 'alert', 'urgent', 'failed', 'down', 'issue', 'emergency', 'breach'],
            'basic_alerts': ['report', 'summary', 'update', 'daily stats', 'weekly stats', 'monthly stats', 'notification'],
            'fyi_cc': ['fyi', 'for your information', 'just letting you know', 'for your awareness', 'in case you missed'],
            'billing_finance': ['invoice', 'payment', 'receipt', 'subscription', 'charge', 'statement', 'bill', 'transaction', 'finance'],
            'scheduling_calendars': ['invite', 'meeting', 'calendar', 'schedule', 'appointment', 'call', 'booking', 'zoom', 'google meet', 'teams'],
            'marketing_promotions': ['webinar', 'deal', 'promo', 'save', 'limited time', 'offer', 'discount', 'subscribe', 'newsletter'],
            'team_internal': ['team', 'internal', 'quick question', 'can you check', 'office'],
            'projects_clients': ['project', 'client', 'proposal', 'deliverable', 'scope', 'contract']
        }
        
        # Simple matching based on subject keywords only
        for category, keywords in category_keywords.items():
            for keyword in keywords:
                if keyword in subject:
                    # Add category with fixed confidence
                    classifications.append((category, 0.8))
                    break  # Stop after first match in a category
        
        # If no classification found, mark as needs_review
        if not classifications:
            classifications.append(('needs_review', 0.7))
            
        return classifications
    
    def create_draft(self, to, subject, body):
        """Create a draft email."""
        try:
            message = MIMEMultipart()
            message['to'] = to
            message['subject'] = subject
            
            msg = MIMEText(body)
            message.attach(msg)
            
            raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
            
            draft = self.service.users().drafts().create(
                userId=self.user_id,
                body={'message': {'raw': raw_message}}
            ).execute()
            
            return draft
        except Exception as e:
            print(f'Error creating draft: {e}')
            return None
    
    def auto_respond(self, email_info, template=None):
        """Generate and send an automatic response to an email."""
        # Skip auto-response if disabled in config
        if not self.config.get('auto_response', {}).get('enabled', False):
            print("[INFO] Auto-response is disabled in config")
            return None
            
        # Get the configured categories for auto-responses
        auto_response_category = self.config.get('auto_response', {}).get('categories', 'Priority Inbox Only')
        categories_to_respond = AUTO_RESPONSE_CATEGORIES.get(auto_response_category, ['priority_inbox'])
        
        # Get the waiting time before sending response
        waiting_time = self.config.get('auto_response', {}).get('waiting_time', 5)
        if isinstance(waiting_time, str):
            waiting_time = AUTO_RESPONSE_WAITING_TIMES.get(waiting_time, 5)
        
        # Wait the configured amount of time (converted to seconds)
        if waiting_time > 0:
            print(f"[INFO] Waiting {waiting_time} minutes before sending response...")
            time.sleep(waiting_time * 60)
        
        # Get the user's name for signature
        user_name = self.get_user_name()
        
        if template is None:
            # Default response template
            template = (
                f"Hi {self.extract_name(email_info['sender'])},\n\n"
                "Thank you for your email. I've received your message and will get back to you soon.\n\n"
                "Best regards,\n"
                f"{user_name}"
            )
        
        to = self.extract_email(email_info['sender'])
        subject = f"Re: {email_info['subject']}"
        
        # Generate the response instead of using a template
        response_body = self.generate_email(
            recipient_name=self.extract_name(email_info['sender']),
            original_subject=email_info['subject'],
            original_content=email_info['body']
        )
        
        if response_body:
            # Send email directly rather than creating a draft
            send_result = self.send_email(
                to=to,
                subject=subject,
                body=response_body
            )
            return send_result
        else:
            # Fall back to template if generation fails
            return self.create_draft(to, subject, template)
    
    def extract_name(self, sender):
        """Extract name from email sender format: 'Name <email@example.com>'"""
        match = re.match(r'(.*?)\s*<', sender)
        if match:
            return match.group(1).strip()
        return 'there'  # Fallback if name can't be extracted
    
    def extract_email(self, sender):
        """Extract email from sender format: 'Name <email@example.com>'"""
        match = re.search(r'<(.*?)>', sender)
        if match:
            return match.group(1)
        return sender  # Return the whole string if it doesn't match the pattern
    
    def send_email(self, draft_id=None, to=None, subject=None, body=None):
        """Send an email, either from a draft or directly."""
        try:
            if draft_id:
                # Send an existing draft
                sent_message = self.service.users().drafts().send(
                    userId=self.user_id,
                    body={'id': draft_id}
                ).execute()
                return sent_message
            elif to and subject and body:
                # Create and send a new email
                message = MIMEMultipart()
                message['to'] = to
                message['subject'] = subject
                
                msg = MIMEText(body)
                message.attach(msg)
                
                raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode('utf-8')
                
                sent_message = self.service.users().messages().send(
                    userId=self.user_id,
                    body={'raw': raw_message}
                ).execute()
                
                return sent_message
            else:
                print("Error: Either draft_id or (to, subject, body) must be provided")
                return None
        except Exception as e:
            print(f'Error sending email: {e}')
            return None
    
        # Fix for setup_openai method
    def setup_openai(self, api_key=None, model=None, no_prompt=False):
        """Set up OpenAI for content generation."""
        try:
            # First try to use explicitly provided parameters
            if api_key:
                self.openai_client = openai.OpenAI(api_key=api_key.strip())
            elif 'streamlit' in sys.modules:
                try:
                    # Get from Streamlit secrets if available
                    api_key = st.secrets["openai"]["api_key"]
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    print(f"Using OpenAI API key from Streamlit secrets: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else 'None'}")
                    
                    # Only override model if not explicitly provided
                    if not model and "model" in st.secrets["openai"]:
                        model = st.secrets["openai"]["model"]
                        print(f"Using OpenAI model from Streamlit secrets: {model}")
                except Exception as e:
                    print(f"[WARNING] Could not load API key from Streamlit secrets: {e}")
                    # Fall back to environment variables
                    api_key = os.getenv("OPENAI_API_KEY")
                    if api_key:
                        self.openai_client = openai.OpenAI(api_key=api_key)
                        print(f"Using OpenAI API key from environment: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else 'None'}")
            else:
                # Not in Streamlit, use environment variables
                api_key = os.getenv("OPENAI_API_KEY")
                if api_key:
                    self.openai_client = openai.OpenAI(api_key=api_key)
                    print(f"Using OpenAI API key from environment: {'*' * (len(api_key) - 4) + api_key[-4:] if api_key else 'None'}")
            
            # Set the model after determining API key
            if model:
                self.openai_model = model
            else:
                self.openai_model = os.getenv("OPENAI_MODEL", "gpt-3.5-turbo")
            
            print(f"[DEBUG] Using OpenAI model: {self.openai_model}")
            print(f"[DEBUG] API key is set: {hasattr(self, 'openai_client')}")

            # Verify that we have a client
            if not hasattr(self, 'openai_client'):
                print("[ERROR] OpenAI client could not be initialized")
                return False
            
            # Test the API key with a simple request
            try:
                response = self.openai_client.chat.completions.create(
                    model=self.openai_model,
                    messages=[{"role": "user", "content": "Hello, this is a test."}],
                    max_tokens=10
                )
                print(f"[DEBUG] API test successful: {response.choices[0].message.content}")
                return True
            except Exception as e:
                print(f"[ERROR] API test failed: {e}")
                return False
                
        except Exception as e:
            print(f"[ERROR] Failed to set up OpenAI: {e}")
            print("[DEBUG] Exception type:", type(e).__name__)
            return False
    def generate_text(self, prompt, max_tokens=500, temperature=0.7):
        """Generate text using OpenAI."""
        try:
            # Verify the client is available before making the request
            if not hasattr(self, 'openai_client'):
                print("[ERROR] OpenAI client is not initialized")
                return None
                
            print(f"[DEBUG] Generating text with {self.openai_model}, max_tokens={max_tokens}, temp={temperature}")
            
            # Use the new OpenAI API
            response = self.openai_client.chat.completions.create(
                model=self.openai_model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
                n=1
            )
            
            # Extract the generated text from the response
            generated_text = response.choices[0].message.content
            print(f"[DEBUG] Generation successful: {len(generated_text)} characters")
            
            return generated_text
        except Exception as e:
            print(f"[ERROR] Text generation failed: {type(e).__name__}: {e}")
            return None
    def generate_email(self, topic=None, recipient_name=None, original_subject=None, original_content=None):
        """Generate an email using OpenAI with context from original email."""
        # Get custom prompt from config, or use default if not set
        user_prompt = self.config.get('user', {}).get('custom_prompt', 
            "Write a professional email response. Make sure proper formatting is done. DO NOT include the subject line in the email body as it will be added separately.")
        
        # Create a prompt for the model with context from original email
        prompt = user_prompt
        if recipient_name:
            prompt += f" to {recipient_name}"
        if original_subject:
            prompt += f" regarding '{original_subject}'"
        
        # Add context from original email if available
        if original_content:
            # Truncate the content if it's too long to fit in the prompt
            max_context_length = 500
            context = original_content[:max_context_length] + "..." if len(original_content) > max_context_length else original_content
            prompt += f"\n\nOriginal email content:\n{context}\n\nWrite a professional and helpful response without repeating the subject in the email body:"
        else:
            prompt += ":\n\n"
        
        generated_text = self.generate_text(prompt, max_tokens=500)
        if not generated_text:
            return f"Thank you for your email. I've received your message and will get back to you with a more detailed response soon.\n\nBest regards,\n{self.get_user_name()}"
            
        # Clean up the generated text to extract only the email body
        clean_email = self._extract_email_body(generated_text)
        
        # Replace [Your Name] placeholder with user's name
        user_name = self.get_user_name()
        clean_email = clean_email.replace("[Your Name]", user_name)
        
        return clean_email
    
    def _extract_email_body(self, generated_text):
        """Extract just the email body from the generated text."""
        # Remove the initial prompt/instructions if present
        patterns_to_remove = [
            r"Write a professional email response.*?(?=Dear|Hi|Hello)",
            r"Original email content:.*?(?=Dear|Hi|Hello)",
            r"Write a professional and helpful response:",
        ]
        
        text = generated_text
        for pattern in patterns_to_remove:
            text = re.sub(pattern, "", text, flags=re.DOTALL).strip()
        
        # Remove any explanatory text after the email (usually starts with ---)
        if "---" in text:
            text = text.split("---")[0].strip()
        
        # Remove any lines that appear to be comments about the email
        lines = text.split('\n')
        cleaned_lines = []
        skip_line = False
        
        for line in lines:
            # Skip lines that look like analysis of the email
            if re.match(r"^This (email|response|revised|approach)", line):
                skip_line = True
                continue
            if skip_line and not line.strip():
                continue
            if skip_line and re.match(r"^[A-Z]", line.strip()):
                skip_line = False
            if not skip_line:
                cleaned_lines.append(line)
        
        return '\n'.join(cleaned_lines).strip()
    
    def get_user_email(self):
        """Get the authenticated user's email address."""
        if not self.user_email:
            try:
                profile = self.service.users().getProfile(userId='me').execute()
                self.user_email = profile.get('emailAddress', '')
                return self.user_email
            except Exception as e:
                print(f"Error getting user email: {e}")
                return ''
        return self.user_email

    def get_user_name(self):
        """Get the user's display name from config or default to their email username."""
        user_config = self.config.get('user', {})
        user_name = user_config.get('name')
        
        if not user_name:
            # If no user name configured, try to extract it from email
            user_email = self.get_user_email()
            if user_email and '@' in user_email:
                # Use part before @ as username
                user_name = user_email.split('@')[0]
                # Capitalize first letter of each word
                user_name = ' '.join(word.capitalize() for word in user_name.split('.'))
            else:
                user_name = "Emmy User"
        
        return user_name
    
    def mark_as_read(self, email_id):
        """Mark an email as read by removing the UNREAD label."""
        try:
            self.service.users().messages().modify(
                userId=self.user_id,
                id=email_id,
                body={'removeLabelIds': ['UNREAD']}
            ).execute()
            return True
        except Exception as e:
            print(f"Error marking email as read: {e}")
            return False
            
    def display_logo(self):
        """Display the logo from the Logo.png file."""
        logo_path = os.path.join(os.path.dirname(__file__), 'Logo.png')
        if os.path.exists(logo_path):
            try:
                # For console output, just notify that the logo exists
                print(f"[INFO] Logo found at: {logo_path}")
                return logo_path
            except Exception as e:
                print(f"[ERROR] Failed to load logo: {e}")
        else:
            print(f"[WARNING] Logo file not found at: {logo_path}")
        return None

def main():
    # GPU diagnostics (not directly relevant for OpenAI API but kept for info)
    print("\n--- System Information ---")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        print(f"CUDA version: {torch.version.cuda}")
        print(f"GPU device: {torch.cuda.get_device_name(0)}")
    print("---------------------\n")
    
    print("[DEBUG] Initializing Gmail Assistant...")
    assistant = GmailAssistant()
    
    # Display the logo
    logo_path = assistant.display_logo()
    if logo_path:
        print(f"[INFO] Using logo from: {logo_path}")
    
    # Get user's email address
    user_email = assistant.get_user_email()
    print(f"Authenticated as: {user_email}")
    
    # Setup OpenAI directly from environment without prompting the user
    print("[DEBUG] Setting up OpenAI from environment variables...")
    setup_success = assistant.setup_openai(no_prompt=args.no_prompt)
    
    if not setup_success:
        print("[ERROR] Failed to initialize OpenAI API. Please check your .env file contains a valid OPENAI_API_KEY.")
        return
    
    print("[DEBUG] Starting email sorting...")
    # Sort emails
    sorted_emails = assistant.sort_emails()
    print("--- Sorted Emails ---")
    for category, emails in sorted_emails.items():
        print(f"\n{category.upper()} ({len(emails)})")
        for email in emails:
            print(f"  - {email['subject']} (From: {email['sender']})")
    
    # Process emails based on auto-response settings from config
    auto_response_config = assistant.config.get('auto_response', {})
    auto_response_enabled = auto_response_config.get('enabled', False)
    
    print(f"\n[DEBUG] Auto-response enabled: {auto_response_enabled}")
    
    if auto_response_enabled:
        auto_response_categories = auto_response_config.get('categories', 'Priority Inbox Only')
        waiting_time = auto_response_config.get('waiting_time', 5)
        
        print(f"[INFO] Auto-response is enabled for: {auto_response_categories}")
        print(f"[INFO] Waiting time before response: {waiting_time} minutes")
        
        # Get categories to process
        categories_to_respond = AUTO_RESPONSE_CATEGORIES.get(auto_response_categories, ['priority_inbox'])
        process_all = categories_to_respond == 'all'
        
        print(f"[DEBUG] Categories to auto-respond: {categories_to_respond if categories_to_respond != 'all' else 'ALL'}")
        
        # Process emails in the selected categories
        processed_emails = 0
        for category, emails in sorted_emails.items():
            if process_all or category in categories_to_respond:
                print(f"[INFO] Processing emails in {CATEGORY_DISPLAY_NAMES.get(category, category)}")
                
                for idx, email in enumerate(emails):
                    print(f"\n[DEBUG] Auto-responding to email {idx+1}/{len(emails)}: {email['subject']}")
                    
                    # Get recipient information
                    sender_email = assistant.extract_email(email['sender'])
                    sender_name = assistant.extract_name(email['sender'])
                    
                    # Wait specified time if needed (converted to seconds)
                    if waiting_time > 0:
                        print(f"[INFO] Waiting {waiting_time} minutes before sending response...")
                        time.sleep(waiting_time * 60)
                    
                    # Generate response
                    print(f"[DEBUG] Generating response to {sender_name} ({sender_email}) using OpenAI...")
                    response_body = assistant.generate_email(
                        recipient_name=sender_name,
                        original_subject=email['subject'],
                        original_content=email['body']
                    )
                    
                    # Send response
                    print("[DEBUG] Response generated successfully.")
                    print(f"[DEBUG] Sending email to {sender_email}...")
                    reply_subject = f"Re: {email['subject']}"
                    response = assistant.send_email(
                        to=sender_email,
                        subject=reply_subject,
                        body=response_body
                    )
                    
                    # Mark as read after processing
                    print(f"[DEBUG] Marking email {email['id']} as read...")
                    assistant.mark_as_read(email['id'])
                    print(f"✓ Response sent to {sender_email} and email marked as read")
                    processed_emails += 1
        
        print(f"[INFO] Auto-responded to {processed_emails} emails from {len(categories_to_respond) if categories_to_respond != 'all' else 'all'} categories")
    else:
        print("[INFO] Auto-response is disabled in config")

    print("\n[DEBUG] Email automation process completed!")
    
    # Return for Streamlit integration
    return sorted_emails

if __name__ == '__main__':
    main()