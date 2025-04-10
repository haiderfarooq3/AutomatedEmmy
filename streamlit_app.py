__import__('streamlit').config.set_option('server.fileWatcherType', 'none')
import streamlit as st
import os
import torch
from datetime import datetime
import pandas as pd
import time
import openai
from dotenv import load_dotenv
from Automation import GmailAssistant, SCOPES

# Load environment variables
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

def authenticate():
    """Authenticate the Gmail assistant and load emails automatically."""
    st.session_state.auth_attempted = True
    with st.spinner("Authenticating with Gmail..."):
        try:
            st.session_state.assistant = GmailAssistant()
            user_email = st.session_state.assistant.get_user_email()
            st.session_state.authenticated = True
            # Auto-load emails after successful authentication
            get_emails()
            return user_email
        except Exception as e:
            st.error(f"Authentication failed: {e}")
            return None

def setup_model():
    """Set up the OpenAI model."""
    if not st.session_state.hf_model_loaded:
        with st.spinner("Setting up OpenAI integration... This may take a moment..."):
            try:
                # Get OpenAI API key from session state or environment
                openai_key = st.session_state.get('openai_api_key', None)
                # Get selected model from session state
                selected_model = st.session_state.get('openai_model', None)
                
                success = st.session_state.assistant.setup_openai(
                    api_key=openai_key,
                    model=selected_model,  # Pass the selected model here
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
        'marketing_promotions': 'Marketing',
        'team_internal': 'Team Internal',
        'projects_clients': 'Projects & Clients',
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
    
    # Header with Emmy branding
    st.markdown("<h1 class='main-header'>Emmy</h1>", unsafe_allow_html=True)
    st.markdown("<p class='app-subtitle'>Your Intelligent Email Assistant</p>", unsafe_allow_html=True)
    
    # Check if we need to refresh the UI
    if st.session_state.needs_refresh:
        st.session_state.needs_refresh = False
        st.rerun()
    
    # Sidebar
    with st.sidebar:
        # Custom logo or default Gmail logo
        st.image("https://upload.wikimedia.org/wikipedia/commons/thumb/7/7e/Gmail_icon_%282020%29.svg/2560px-Gmail_icon_%282020%29.svg.png", width=100)
        st.markdown("## Emmy Settings")
        
        # Authentication
        if not st.session_state.authenticated:
            st.markdown("### Authentication")
            st.markdown(f"Emmy needs access to your Gmail account with the following permissions:")
            for scope in SCOPES:
                st.markdown(f"- {scope.split('/')[-1]}")
            
            if st.button("Authenticate Emmy with Gmail") or (st.session_state.auth_attempted and not st.session_state.authenticated):
                user_email = authenticate()
                if user_email:
                    st.success(f"Emmy authenticated as: {user_email}")
                    # We'll reload the page to update the UI
                    st.session_state.needs_refresh = True
                    st.rerun()
        else:
            user_email = st.session_state.assistant.get_user_email()
            st.success(f"Emmy authenticated as: {user_email}")
            
            # OpenAI API settings
            st.markdown("### Emmy's AI Brain")
            openai_api_key = st.text_input("OpenAI API Key", type="password", 
                                          value=os.getenv("OPENAI_API_KEY", ""))
            if openai_api_key:
                st.session_state.openai_api_key = openai_api_key
            
            openai_model = st.selectbox(
                "Select OpenAI Model",
                ["gpt-3.5-turbo", "gpt-4", "gpt-4-turbo"],
                index=0
            )
            st.session_state.openai_model = openai_model
            
            if not st.session_state.hf_model_loaded:
                if st.button("Connect to OpenAI API"):
                    setup_model()
            else:
                st.success("Emmy's AI brain is connected and ready!")
            
            # Email refresh
            st.markdown("### Email Management")
            if st.button("Refresh Emails"):
                get_emails()
                st.session_state.needs_refresh = True
                st.rerun()
    
    # Main content
    if st.session_state.authenticated:
        # Content tabs
        tab1, tab2 = st.tabs(["Emmy Dashboard", "Auto-Response Settings"])
        
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
            
            # Future implementation for personalized response templates
            auto_respond = st.toggle("Enable Emmy's Auto-Responses for Important Emails", value=False)
            
            if auto_respond:
                st.markdown("#### Auto-Response Settings")
                
                # Options for auto-responder
                st.selectbox(
                    "Email Categories for Emmy to Auto-Respond", 
                    ["Priority Inbox Only", "Priority & Main Inbox", "All Categories"],
                    index=0
                )
                
                waiting_time = st.slider(
                    "Waiting Time Before Emmy Auto-Responds (minutes)", 
                    min_value=0, 
                    max_value=60, 
                    value=5
                )
                
                if st.button("Save Emmy's Auto-Response Settings"):
                    st.success("Emmy's auto-response settings saved!")
                    # In a full implementation, save these settings to a configuration
                
                st.info("Emmy will use AI to generate contextual responses for your emails.")
    else:
        st.info("Please authenticate Emmy with your Gmail account using the button in the sidebar to get started.")

if __name__ == "__main__":
    main()
