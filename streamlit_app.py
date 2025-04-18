__import__('streamlit').config.set_option('server.fileWatcherType', 'none')
import streamlit as st
import os
import torch
from datetime import datetime
import pandas as pd
import time
import openai
import json
from dotenv import load_dotenv
from Automation import GmailAssistant, SCOPES
from constants import CATEGORY_DISPLAY_NAMES, AUTO_RESPONSE_CATEGORIES, AUTO_RESPONSE_WAITING_TIMES

# Load environment variables for local development
load_dotenv()

# Set page configuration and styling
st.set_page_config(
    page_title="Emmy - Your Email Assistant",
    page_icon="📧",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
    }
    .app-subtitle {
        font-size: 1.2rem;
        color: #5c5c5c;
        margin-top: -15px;
        margin-bottom: 20px;
    }
    .category-header {
        font-size: 1.5rem;
        color: #1E88E5;
        padding: 10px 0;
        border-bottom: 1px solid #e0e0e0;
    }
    .email-card {
        background-color: #f9f9f9;
        border-radius: 10px;
        padding: 15px;
        margin-bottom: 10px;
        border-left: 4px solid #1E88E5;
    }
    .email-subject {
        font-weight: bold;
        color: #333;
    }
    .email-sender {
        color: #666;
        font-style: italic;
    }
    .stButton button {
        background-color: #1E88E5;
        color: white;
    }
    .category-tag {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 12px;
        font-size: 0.8rem;
        font-weight: bold;
        color: white;
        background-color: #1E88E5;
        margin-right: 5px;
    }
</style>
""", unsafe_allow_html=True)

def init_session_state():
    """Initialize session state variables."""
    if 'assistant' not in st.session_state:
        st.session_state.assistant = None
    if 'authenticated' not in st.session_state:
        st.session_state.authenticated = False
    if 'sorted_emails' not in st.session_state:
        st.session_state.sorted_emails = {}
    if 'selected_email' not in st.session_state:
        st.session_state.selected_email = None
    if 'generated_response' not in st.session_state:
        st.session_state.generated_response = None
    if 'hf_model_loaded' not in st.session_state:
        st.session_state.hf_model_loaded = False
    if 'processing' not in st.session_state:
        st.session_state.processing = False
    if 'emails_loaded' not in st.session_state:
        st.session_state.emails_loaded = False
    if 'needs_refresh' not in st.session_state:
        st.session_state.needs_refresh = False
    if 'auth_attempted' not in st.session_state:
        st.session_state.auth_attempted = False
    if 'debug_info' not in st.session_state:
        st.session_state.debug_info = {}
    if 'debug_send' not in st.session_state:
        st.session_state.debug_send = {}
    if 'auth_status' not in st.session_state:
        st.session_state.auth_status = "Not started"

def is_deployed():
    """Check if running in a deployed environment."""
    try:
        # If we can access Streamlit secrets, we're likely in a deployed environment
        _ = st.secrets["openai"]["api_key"]
        return True
    except Exception:
        return False


def authenticate():
    """Authenticate the Gmail assistant and load emails automatically."""
    st.session_state.auth_attempted = True
    with st.spinner("Authenticating with Gmail..."):
        try:
            # Check if we already have a valid assistant
            if 'assistant' in st.session_state and st.session_state.assistant and st.session_state.assistant.service:
                user_email = st.session_state.assistant.get_user_email()
                if user_email:
                    st.session_state.authenticated = True
                    return user_email

            # Initialize the assistant
            if 'assistant' not in st.session_state or st.session_state.assistant is None:
                st.session_state.assistant = GmailAssistant()

            # If service is None, we need to complete OAuth
            if st.session_state.assistant.service is None:
                # Import required libraries for OAuth
                import json
                from google_auth_oauthlib.flow import Flow

                # Get client config from secrets
                creds_json = json.loads(st.secrets["google"]["credentials_json"])

                # Use the correct redirect URI
                redirect_uri = creds_json['web']['redirect_uris'][0]

                # Create a Flow instance
                flow = Flow.from_client_config(
                    client_config=creds_json,
                    scopes=SCOPES,
                    redirect_uri=redirect_uri
                )

                # Check if we have a code in the URL
                if 'code' in st.query_params:
                    code = st.query_params['code']

                    # Exchange authorization code for tokens
                    flow.fetch_token(code=code)
                    creds = flow.credentials

                    # Save credentials to session state
                    st.session_state.google_creds = {
                        'token': creds.token,
                        'refresh_token': creds.refresh_token,
                        'token_uri': creds.token_uri,
                        'client_id': creds.client_id,
                        'client_secret': creds.client_secret,
                        'scopes': creds.scopes
                    }

                    # Clear the URL parameters using the official API
                    st.experimental_set_query_params()

                    # Reinitialize the assistant with the new token
                    st.session_state.assistant = GmailAssistant()

                    if st.session_state.assistant.service:
                        user_email = st.session_state.assistant.get_user_email()
                        if user_email:
                            st.session_state.authenticated = True
                            get_emails()  # Auto-load emails
                            return user_email
                else:
                    # Generate the authorization URL
                    auth_url, _ = flow.authorization_url(
                        access_type='offline',
                        include_granted_scopes='true',
                        prompt='consent'
                    )
                    # Replace the existing authentication link in your authenticate() function with this:
                    # Find lines 201-214 in your streamlit_app.py file

                    # Display authentication button that opens in SAME tab using JavaScript
                    st.markdown("### Gmail Authentication Required")
                    st.markdown("Click the button below to authorize Emmy to access your Gmail account:")

                    # Use HTML/JS to force opening in the same tab
                    st.markdown(f"""
                    <div style="text-align: center; margin-top: 20px;">
                        <a href="{auth_url}" target="_blank" style="
                            text-decoration: none;
                            background-color: #FF4B4B;
                            color: white;
                            padding: 10px 20px;
                            border-radius: 5px;
                            font-weight: bold;
                            display: inline-block;
                        " onclick="window.top.location.href='{auth_url}'; return false;">
                            Authenticate with Gmail
                        </a>
                    </div>
                    """, unsafe_allow_html=True)

                    return None
            else:
                # We have a service, so we're authenticated
                user_email = st.session_state.assistant.get_user_email()
                if user_email:
                    st.session_state.authenticated = True
                    get_emails()  # Auto-load emails
                    return user_email
                else:
                    st.error("Unable to get user email. Authentication may not be complete.")
                    return None

        except Exception as e:
            st.error(f"Authentication failed: {e}")
            return None


def setup_model():
    """Set up the OpenAI model."""
    if not st.session_state.hf_model_loaded:
        with st.spinner("Setting up OpenAI integration... This may take a moment..."):
            try:
                # Get OpenAI API key from Streamlit secrets or session state
                openai_key = None
                selected_model = None
                
                # Try to get from Streamlit secrets first
                try:
                    openai_key = st.secrets["openai"]["api_key"]
                    selected_model = st.secrets["openai"]["model"]
                    st.write(f"Using OpenAI model from secrets: {selected_model}")
                except Exception as e:
                    st.warning(f"Could not load OpenAI credentials from Streamlit secrets: {e}")
                    # Fall back to session state or UI input
                    openai_key = st.session_state.get('openai_api_key', None)
                    selected_model = st.session_state.get('openai_model', None)
                
                # Set up OpenAI
                success = st.session_state.assistant.setup_openai(
                    api_key=openai_key,
                    model=selected_model,
                    no_prompt=True
                )
                
                if success:
                    st.session_state.hf_model_loaded = True
                    st.success("OpenAI integration set up successfully!")
                    time.sleep(0.5)  # Brief pause to show success message
                    st.rerun()  # Refresh UI to update
                    return True
                else:
                    st.warning("OpenAI setup failed. Please check your API key.")
                    return False
            except Exception as e:
                st.error(f"Error setting up OpenAI: {e}")
                return False
    return True

def get_emails():
    """Get and sort emails."""
    with st.spinner("Loading emails..."):
        st.session_state.sorted_emails = st.session_state.assistant.sort_emails()
        st.session_state.emails_loaded = True
        # No need for user to click again, just update the UI automatically

def view_and_respond(email):
    """Handle the view and respond action for an email."""
    st.session_state.selected_email = email
    st.rerun()  # Refresh UI to show the selected email details

def mark_email_read(email_id):
    """Mark an email as read and refresh the email list."""
    with st.spinner("Marking as read..."):
        success = st.session_state.assistant.mark_as_read(email_id)
        if success:
            get_emails()  # Refresh the email list
            st.session_state.selected_email = None  # Clear selection
            st.success("Email marked as read")
            time.sleep(0.5)  # Brief pause to show success message
            st.rerun()  # Update UI
        else:
            st.error("Failed to mark email as read")

def generate_email_response(email):
    """Generate a response for the selected email."""
    with st.spinner("Generating response..."):
        try:
            sender_name = st.session_state.assistant.extract_name(email['sender'])
            
            # Debug information
            st.session_state.debug_info = {
                'sender_name': sender_name,
                'subject': email['subject'],
                'body_length': len(email['body']) if email['body'] else 0
            }
            
            # Check if model is loaded
            if not st.session_state.hf_model_loaded:
                # Use a simpler fallback response if model isn't loaded
                response = f"Hello {sender_name},\n\nThank you for your email regarding \"{email['subject']}\".\nI've received your message and will get back to you soon with a more detailed response.\n\nBest regards,\n{st.session_state.assistant.get_user_name()}"
            else:
                # Use the AI model for response generation
                response = st.session_state.assistant.generate_email(
                    recipient_name=sender_name,
                    original_subject=email['subject'],
                    original_content=email['body']
                )
            
            if not response or "Sorry, I can't assist with that" in response:
                # If the model returned an invalid response, use a safe fallback
                response = f"Hello {sender_name},\n\nThank you for your email regarding \"{email['subject']}\".\nI've received your message and will respond to it shortly.\n\nBest regards,\n{st.session_state.assistant.get_user_name()}"
            
            st.session_state.generated_response = response
            st.rerun()  # Update UI to show the generated response
        except Exception as e:
            st.error(f"Error generating response: {str(e)}")
            # Provide a fallback response
            fallback_response = f"Hello,\n\nThank you for your email. I've received your message and will get back to you soon.\n\nBest regards,\n{st.session_state.assistant.get_user_name()}"
            st.session_state.generated_response = fallback_response
            st.rerun()

def sanitize_for_html(text):
    """
    Sanitize text to be safely used in HTML.
    Replaces special characters that might cause rendering issues.
    """
    if not text:
        return ""
    
    # Replace characters that could cause HTML interpretation issues
    replacements = {
        "<": "&lt;",
        ">": "&gt;",
        "&": "&amp;",
        '"': "&quot;",
        "'": "&#39;",
        "@": "&#64;",  # Replace @ with its HTML entity
    }
    
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    
    return text

def send_email_response(email, response_text):
    """Send a response email and update UI."""
    with st.spinner("Sending email..."):
        try:
            # Extract email properly
            sender_email = st.session_state.assistant.extract_email(email['sender'])
            
            # Check if we have a valid email
            if not sender_email or '@' not in sender_email:
                st.error(f"Invalid email address: {sender_email}")
                return
                
            reply_subject = f"Re: {email['subject']}"
            
            # Check if response is valid before sending
            if not response_text or len(response_text.strip()) < 10:
                st.error("Response is too short or empty. Please provide a proper response.")
                return
            
            # Log what we're about to send (for debugging)
            st.session_state.debug_send = {
                'to': sender_email,
                'subject': reply_subject,
                'body_length': len(response_text)
            }
            
            result = st.session_state.assistant.send_email(
                to=sender_email,
                subject=reply_subject,
                body=response_text
            )
            
            if result:
                # Mark as read after sending
                st.session_state.assistant.mark_as_read(email['id'])
                # Reset selected email
                st.session_state.selected_email = None
                st.session_state.generated_response = None
                # Refresh email list
                get_emails()
                st.success(f"Response sent to {sanitize_for_html(sender_email)}")
                time.sleep(0.5)  # Brief pause
                st.rerun()  # Update UI
            else:
                st.error("Failed to send email. Please check your connection and try again.")
        except Exception as e:
            st.error(f"Error sending email: {str(e)}")

def cancel_response():
    """Cancel the current response generation."""
    st.session_state.generated_response = None
    st.rerun()  # Update UI immediately

def update_config(auto_respond_enabled, auto_respond_categories, waiting_time, user_name=None, custom_prompt=None):
    """Update the configuration in Streamlit secrets or session state."""
    try:
        # Initialize an in-memory config that will mirror what would be in secrets
        config = {
            "auto_response": {
                "enabled": auto_respond_enabled,
                "categories": auto_respond_categories, 
                "waiting_time": waiting_time
            },
            "user": {}
        }
        
        # Update user settings if provided
        if user_name:
            config["user"]["name"] = user_name
            
        # Update custom prompt if provided
        if custom_prompt:
            config["user"]["custom_prompt"] = custom_prompt
        
        # Store in session state (this won't persist between sessions, but works for demo)
        st.session_state.config_override = config
        
        # If we have an assistant instance, update its config directly
        if st.session_state.assistant:
            # Merge the existing config with our updates
            current_config = st.session_state.assistant.config or {}
            
            # Update auto-response settings
            if 'auto_response' not in current_config:
                current_config['auto_response'] = {}
            current_config['auto_response']['enabled'] = auto_respond_enabled
            current_config['auto_response']['categories'] = auto_respond_categories
            current_config['auto_response']['waiting_time'] = waiting_time
            
            # Update user settings
            if 'user' not in current_config:
                current_config['user'] = {}
            if user_name:
                current_config['user']['name'] = user_name
            if custom_prompt:
                current_config['user']['custom_prompt'] = custom_prompt
            
            # Set the updated config on the assistant
            st.session_state.assistant.config = current_config
        
        return True
    except Exception as e:
        st.error(f"Error updating config: {e}")
        return False

def get_current_config():
    """Get the current configuration from session state or defaults."""
    try:
        # If we have an override in session state, use that
        if 'config_override' in st.session_state:
            return st.session_state.config_override
        
        # If we have an assistant with config, use that
        if hasattr(st.session_state, 'assistant') and st.session_state.assistant and hasattr(st.session_state.assistant, 'config'):
            return st.session_state.assistant.config
        
        # Try to get from secrets
        if 'config' in st.secrets:
            config = {}
            
            # Get auto_response settings
            if 'auto_response' in st.secrets.config:
                config['auto_response'] = {
                    'enabled': st.secrets.config.auto_response.get('enabled', False),
                    'categories': st.secrets.config.auto_response.get('categories', 'Priority Inbox Only'),
                    'waiting_time': st.secrets.config.auto_response.get('waiting_time', 5)
                }
            else:
                config['auto_response'] = {
                    'enabled': False,
                    'categories': 'Priority Inbox Only',
                    'waiting_time': 5
                }
            
            # Get user settings
            if 'user' in st.secrets.config:
                config['user'] = {
                    'name': st.secrets.config.user.get('name', 'Emmy User'),
                    'custom_prompt': st.secrets.config.user.get('custom_prompt', None)
                }
            else:
                config['user'] = {
                    'name': 'Emmy User',
                    'custom_prompt': None
                }
            
            return config
        
        # Return defaults if nothing else is available
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
    except Exception as e:
        st.error(f"Error loading config: {e}")
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

def run_auto_responses():
    """Run the auto-response logic for unprocessed emails."""
    if not st.session_state.assistant:
        st.error("No assistant initialized. Please authenticate first.")
        return False
    
    with st.spinner("Processing emails with auto-responder..."):
        try:
            # Get current settings
            config = st.session_state.assistant.config
            auto_response_config = config.get('auto_response', {})
            auto_response_enabled = auto_response_config.get('enabled', False)
            
            if not auto_response_enabled:
                st.info("Auto-response is disabled. Enable it in settings to use this feature.")
                return False
            
            # Get auto-response parameters
            categories_setting = auto_response_config.get('categories', 'Priority Inbox Only')
            waiting_time = auto_response_config.get('waiting_time', 5)
            
            # Sort emails and get the ones to process
            sorted_emails = st.session_state.assistant.sort_emails()
            
            # Determine which categories to process
            categories_to_respond = AUTO_RESPONSE_CATEGORIES.get(categories_setting, ['priority_inbox'])
            process_all = categories_to_respond == 'all'
            
            # Track processed emails
            processed_emails = 0
            
            # Process each category
            for category, emails in sorted_emails.items():
                if process_all or category in categories_to_respond:
                    st.text(f"Processing {len(emails)} emails in {CATEGORY_DISPLAY_NAMES.get(category, category)}")
                    
                    for email in emails:
                        # Extract important info
                        sender_email = st.session_state.assistant.extract_email(email['sender'])
                        sender_name = st.session_state.assistant.extract_name(email['sender'])
                        
                        # Generate response
                        response_body = st.session_state.assistant.generate_email(
                            recipient_name=sender_name,
                            original_subject=email['subject'],
                            original_content=email['body']
                        )
                        
                        # Send response
                        reply_subject = f"Re: {email['subject']}"
                        result = st.session_state.assistant.send_email(
                            to=sender_email,
                            subject=reply_subject,
                            body=response_body
                        )
                        
                        if result:
                            # Mark as read after processing
                            st.session_state.assistant.mark_as_read(email['id'])
                            processed_emails += 1
                            # Brief progress update
                            st.text(f"✓ Processed: {email['subject'][:40]}...")
            
            # Update emails after processing
            st.session_state.sorted_emails = st.session_state.assistant.sort_emails()
            st.session_state.emails_loaded = True
            
            if processed_emails > 0:
                st.success(f"Auto-responded to {processed_emails} emails")
            else:
                st.info("No emails matched the auto-response criteria")
            
            return True
        except Exception as e:
            st.error(f"Error running auto-responder: {str(e)}")
            return False

def display_emails():
    """Display sorted emails in tabs."""
    if not st.session_state.sorted_emails:
        st.info("No emails found. Try refreshing.")
        return
    
    # Create tabs for each category with more user-friendly names
    categories = list(st.session_state.sorted_emails.keys())
    
    # Map category keys to display names
    category_display_names = {
        'priority_inbox': 'Priority Inbox',
        'main_inbox': 'Main Inbox',
        'urgent_alerts': 'Urgent Alerts',
        'basic_alerts': 'Basic Alerts',
        'fyi_cc': 'FYI / CC',
        'billing_finance': 'Billing & Finance',
        'scheduling_calendars': 'Scheduling',
        'team_internal': 'Team Internal',
        'projects_clients': 'Projects & Clients',
        'marketing_promotions': 'Marketing',
        'needs_review': 'Needs Review',
        'rules_in_training': 'Rules in Training'
    }
    
    if categories:
        tabs = st.tabs(["All"] + [category_display_names.get(cat, cat.capitalize()) for cat in categories])
        
        # Create a combined dataframe for "All" tab
        all_emails = []
        for category, emails in st.session_state.sorted_emails.items():
            for email in emails:
                email_copy = email.copy()
                email_copy['category'] = category
                all_emails.append(email_copy)
        
        # Display all emails in first tab
        with tabs[0]:
            if all_emails:
                # Create a safe display version of the dataframe
                safe_emails = []
                for email in all_emails:
                    safe_email = email.copy()
                    # Sanitize sender field which may contain email addresses
                    safe_email['sender'] = sanitize_for_html(email['sender'])
                    safe_email['subject'] = sanitize_for_html(email['subject'])
                    safe_emails.append(safe_email)
                
                df = pd.DataFrame(safe_emails)
                # Format the dataframe
                df = df[['category', 'subject', 'sender', 'date']]
                df = df.rename(columns={
                    'category': 'Category',
                    'subject': 'Subject',
                    'sender': 'Sender',
                    'date': 'Date'
                })
                
                # Convert dates
                df['Date'] = pd.to_datetime(df['Date']).dt.strftime('%Y-%m-%d %H:%M')
                # Use the display names for categories in the dataframe
                df['Category'] = df['Category'].map(lambda x: category_display_names.get(x, x.capitalize()))
                
                # Make the table selectable
                selection = st.dataframe(
                    df,
                    use_container_width=True,
                    column_config={
                        "Subject": st.column_config.TextColumn(width="large"),
                        "Sender": st.column_config.TextColumn(width="medium"),
                        "Date": st.column_config.TextColumn(width="small"),
                        "Category": st.column_config.TextColumn(width="small"),
                    },
                    hide_index=True
                )
                
                # Create a selectbox for email selection with safe display options
                if all_emails:
                    email_options = [f"{sanitize_for_html(e['subject'])} - {sanitize_for_html(e['sender'])}" for e in all_emails]
                    selected_index = st.selectbox("Select an email to view", 
                                                range(len(email_options)), 
                                                format_func=lambda i: email_options[i],
                                                on_change=lambda: view_and_respond(all_emails[st.session_state.widget_selected_index]) 
                                                if 'widget_selected_index' in st.session_state else None,
                                                key='widget_selected_index')
        
        # Display category tabs
        for i, category in enumerate(categories, 1):
            with tabs[i]:
                emails = st.session_state.sorted_emails[category]
                if emails:
                    for idx, email in enumerate(emails):
                        # Sanitize email content for HTML display
                        safe_subject = sanitize_for_html(email['subject'])
                        safe_sender = sanitize_for_html(email['sender'])
                        date_str = email['date'].strftime('%Y-%m-%d %H:%M') if isinstance(email['date'], datetime) else email['date']
                        
                        with st.container():
                            st.markdown(f"""
                            <div class="email-card">
                                <div class="email-subject">{safe_subject}</div>
                                <div class="email-sender">From: {safe_sender}</div>
                                <div>Date: {date_str}</div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            if st.button(f"View & Respond", key=f"view_{category}_{email['id']}"):
                                view_and_respond(email)
                else:
                    st.info(f"No emails in the {category_display_names.get(category, category)} category.")

def display_email_details():
    """Display the details of a selected email."""
    if st.session_state.selected_email:
        email = st.session_state.selected_email
        
        st.markdown("<div class='category-header'>Email Details</div>", unsafe_allow_html=True)
        
        # Sanitize email content
        safe_subject = sanitize_for_html(email['subject'])
        safe_sender = sanitize_for_html(email['sender'])
        date_str = email['date'].strftime('%Y-%m-%d %H:%M') if isinstance(email['date'], datetime) else email['date']
        
        # Email details columns
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Subject:** {safe_subject}")
            st.markdown(f"**From:** {safe_sender}")
            st.markdown(f"**Date:** {date_str}")
            
            # Show category if available with a nice formatted display name
            if 'category' in email:
                category_display_names = {
                    'priority_inbox': 'Priority Inbox',
                    'main_inbox': 'Main Inbox',
                    'urgent_alerts': 'Urgent Alerts',
                    'basic_alerts': 'Basic Alerts',
                    'fyi_cc': 'FYI / CC',
                    'billing_finance': 'Billing & Finance',
                    'scheduling_calendars': 'Scheduling',
                    'marketing_promotions': 'Marketing',
                    'team_internal': 'Team Internal',
                    'projects_clients': 'Projects & Clients',
                    'needs_review': 'Needs Review',
                    'rules_in_training': 'Rules in Training'
                }
                cat_name = category_display_names.get(email['category'], email['category'].capitalize())
                st.markdown(f"""<div class="category-tag">{cat_name}</div>""", unsafe_allow_html=True)
        
        with col2:
            # Action buttons
            if st.button("Mark as Read", use_container_width=True):
                mark_email_read(email['id'])
            
            if st.button("Generate Response", use_container_width=True):
                if not st.session_state.hf_model_loaded:
                    st.warning("OpenAI integration not set up. Using a simple response template.")
                generate_email_response(email)
        
        # Display email body (sanitize it too)
        safe_body = sanitize_for_html(email['body']) if email['body'] else ""
        
        st.markdown("### Email Content")
        with st.expander("Show Email Content", expanded=True):
            st.text_area("Email Body", value=email['body'], height=200, disabled=True)
        
        # Display generated response if available
        if st.session_state.generated_response:
            st.markdown("### Emmy's Generated Response")
            response_text = st.text_area(
                "Edit Response Before Sending", 
                value=st.session_state.generated_response, 
                height=300,
                key="response_editor"
            )
            
            col1, col2 = st.columns([1, 1])
            with col1:
                if st.button("Send Response", use_container_width=True):
                    send_email_response(email, response_text)
            
            with col2:
                if st.button("Cancel", use_container_width=True):
                    cancel_response()
            
            # Add debugging information (only during development)
            with st.expander("Debug Information", expanded=False):
                st.write("Generation Info:", st.session_state.debug_info)
                st.write("Send Info:", st.session_state.debug_send)

def main():
    """Main function to run the Streamlit app."""
    init_session_state()
    
    if 'code' in st.query_params and not st.session_state.authenticated:
        with st.spinner("Completing authentication..."):
            authenticate()
            if st.session_state.authenticated:
                st.rerun()
    # Header with Emmy branding
    st.markdown("<h1 class='main-header'>Emmy</h1>", unsafe_allow_html=True)
    st.markdown("<p class='app-subtitle'>Your Intelligent Email Assistant</p>", unsafe_allow_html=True)
    
    # Check if we need to refresh the UI
    if st.session_state.needs_refresh:
        st.session_state.needs_refresh = False
        st.rerun()
    
    # Sidebar
    with st.sidebar:
        # Add Emmy Settings header before the logo
        st.markdown("## Emmy Settings")
        
        # Display the logo after the header
        logo_path = os.path.join(os.path.dirname(__file__), 'Logo.png')
        if os.path.exists(logo_path):
            st.image(logo_path, width=300, use_container_width=False)
        else:
            st.warning("Logo image not found. Please make sure 'Logo.png' exists in the application directory.")
        
        # Authentication section
        # In your sidebar code where you show the authenticate button:
        if not st.session_state.authenticated:
            st.markdown("### Authentication")
            st.markdown(f"Emmy needs access to your Gmail account with the following permissions:")
            for scope in SCOPES:
                st.markdown(f"- {scope.split('/')[-1]}")
            
            # Use custom HTML for the button to ensure it opens in the same tab
            if st.button("Authenticate with Gmail"):
                authenticate()
                # If authentication was successful, rerun to update UI
                if st.session_state.get('authenticated', False):
                    st.rerun()
            
            # Show authentication help information
            with st.expander("Authentication Help"):
                st.markdown("""
                **For Streamlit Cloud Deployment:**
                1. You must have your Google credentials in the secrets.toml file
                2. You need to authorize access to your Gmail account
                3. Contact your administrator if you need help with authentication
                """)
        else:
            user_email = st.session_state.assistant.get_user_email()
            st.success(f"Emmy authenticated as: {user_email}")
    
    # Main content
    if st.session_state.authenticated:

        if not st.session_state.hf_model_loaded:
            setup_model()
            
        # Content tabs - add a new tab for user profile
        tab1, tab2, tab3 = st.tabs(["Emmy Dashboard", "Auto-Response Settings", "User Profile"])
        
        with tab1:
            # If we've authenticated but haven't loaded emails yet, load them automatically
            if not st.session_state.emails_loaded and st.session_state.authenticated:
                get_emails()
                st.session_state.needs_refresh = True
                st.rerun()
            
            # Show emails
            display_emails()
            
            # Separator
            st.markdown("---")
            
            # Display selected email if available
            if st.session_state.selected_email:
                display_email_details()
            else:
                st.info("Select an email from the list for Emmy to help you manage it.")
        
        with tab2:
            st.markdown("### Emmy Auto-Responder Configuration")
            st.markdown("Configure how Emmy should automatically handle your emails")
            
            # Load current config for default values
            current_config = get_current_config()
            auto_response_config = current_config.get('auto_response', {})
            
            # Options for auto-responder with current settings as defaults
            auto_respond = st.toggle(
                "Enable Emmy's Auto-Responses", 
                value=auto_response_config.get('enabled', False),
                key="auto_respond_toggle"
            )
            
            # Only show these options if auto-respond is enabled
            if auto_respond:
                st.markdown("#### Auto-Response Settings")
                
                # Categories dropdown
                categories_options = [
                    "Priority Inbox Only", 
                    "All Important", 
                    "Business Related", 
                    "Everything"
                ]
                
                current_category = auto_response_config.get('categories', 'Priority Inbox Only')
                selected_category = st.selectbox(
                    "Email Categories for Emmy to Auto-Respond", 
                    categories_options,
                    index=categories_options.index(current_category) if current_category in categories_options else 0,
                    key="auto_respond_categories"
                )
                
                # Waiting time slider
                current_waiting_time = auto_response_config.get('waiting_time', 5)
                waiting_time = st.slider(
                    "Waiting Time Before Emmy Auto-Responds (minutes)", 
                    min_value=0, 
                    max_value=60, 
                    value=current_waiting_time,
                    key="auto_respond_waiting_time"
                )
                
                # Preview what will be processed
                st.markdown("#### Preview Selected Categories")
                
                # Get the actual category keys that will be processed
                categories_to_process = AUTO_RESPONSE_CATEGORIES.get(selected_category, ['priority_inbox'])
                
                if categories_to_process == 'all':
                    st.info("Emmy will respond to emails in ALL categories")
                else:
                    # Show the friendly names of categories
                    friendly_names = [CATEGORY_DISPLAY_NAMES.get(cat, cat.capitalize()) for cat in categories_to_process]
                    st.info(f"Emmy will respond to emails in these categories: {', '.join(friendly_names)}")
                
                # Debug current settings
                st.markdown("#### Current Settings")
                st.json({
                    "auto_response": {
                        "enabled": auto_respond,
                        "categories": selected_category,
                        "waiting_time": waiting_time
                    }
                })
                
                # Split buttons into columns for better UI
                col1, col2 = st.columns(2)
                
                with col1:
                    if st.button("Save Emmy's Auto-Response Settings", key="save_settings"):
                        # Save configuration to file
                        success = update_config(auto_respond, selected_category, waiting_time)
                        if success:
                            st.success("Emmy's auto-response settings saved!")
                            # Force reload of the assistant to pick up new settings
                            if hasattr(st.session_state, 'assistant') and st.session_state.assistant:
                                st.session_state.assistant.config = get_current_config()
                                st.session_state.needs_refresh = True
                                st.rerun()
                        else:
                            st.error("Failed to save Emmy's auto-response settings")
                
                with col2:
                    if st.button("Run Auto-Responder Now", key="run_auto_responder"):
                        # First save the settings to make sure we use the latest
                        success = update_config(auto_respond, selected_category, waiting_time)
                        if success:
                            # Run auto-responder with the updated settings
                            run_success = run_auto_responses()
                            if run_success:
                                # Reload data to reflect changes
                                st.session_state.needs_refresh = True
                                st.rerun()
            else:
                # If auto-respond is disabled, still provide a way to save this setting
                if st.button("Save Settings"):
                    success = update_config(False, "Priority Inbox Only", 5)
                    if success:
                        st.success("Auto-responses disabled successfully")
                        # Force reload of the assistant to pick up new settings
                        if hasattr(st.session_state, 'assistant') and st.session_state.assistant:
                            st.session_state.assistant.config = get_current_config()
                    else:
                        st.error("Failed to update settings")
        
        with tab3:
            st.markdown("### Your Profile Settings")
            st.markdown("Customize how Emmy represents you in emails")
            
            # Load current config for default values
            current_config = get_current_config()
            user_config = current_config.get('user', {})
            
            # Display name setting
            user_name = st.text_input(
                "Your Display Name (used in email signatures)", 
                value=user_config.get('name', ''),
                key="user_display_name"
            )
            
            # Custom prompt setting
            st.markdown("#### Custom Email Style")
            st.markdown("""
            Provide details about yourself and how you want Emmy to represent you when replying to emails.
            For example: "Write a professional email response. I am a marketing manager specializing in digital campaigns."
            """)
            
            default_prompt = "Write a professional email response. Make sure proper formatting is done. DO NOT include the subject line in the email body as it will be added separately."
            custom_prompt = st.text_area(
                "Your Custom Style Prompt", 
                value=user_config.get('custom_prompt', default_prompt),
                height=150,
                key="custom_prompt_input",
                help="This prompt guides Emmy on how to write emails on your behalf"
            )
            
            # Save button
            if st.button("Save Profile Settings", key="save_profile"):
                success = update_config(
                    current_config.get('auto_response', {}).get('enabled', False),
                    current_config.get('auto_response', {}).get('categories', 'Priority Inbox Only'),
                    current_config.get('auto_response', {}).get('waiting_time', 5),
                    user_name=user_name,
                    custom_prompt=custom_prompt
                )
                
                if success:
                    st.success("Profile settings saved successfully!")
                    # Reload the assistant to pick up new settings
                    if hasattr(st.session_state, 'assistant') and st.session_state.assistant:
                        st.session_state.assistant.config = get_current_config()
                else:
                    st.error("Failed to save profile settings")
    else:
        st.info("Please authenticate Emmy with your Gmail account using the button in the sidebar to get started.")

if __name__ == "__main__":
    main()