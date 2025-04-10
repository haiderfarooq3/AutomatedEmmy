__import__('streamlit').config.set_option('server.fileWatcherType', 'none')
import os
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
from transformers import AutoModelForCausalLM, AutoTokenizer
from huggingface_hub import login

# Define the scopes required for Gmail API
SCOPES = ['https://www.googleapis.com/auth/gmail.modify',
          'https://www.googleapis.com/auth/gmail.compose',
          'https://www.googleapis.com/auth/gmail.send']

# Parse command line arguments
parser = argparse.ArgumentParser(description='Gmail Automation Tool')
parser.add_argument('--no-prompt', action='store_true', help='Run without interactive prompts')
parser.add_argument('--hf-token', type=str, help='Hugging Face token', default=None)
args = parser.parse_args()

class GmailAssistant:
    def __init__(self):
        self.service = self.authenticate()
        self.user_id = 'me'  # 'me' refers to the authenticated user
        self.hf_model = None
        self.hf_tokenizer = None
        self.user_email = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    
    def authenticate(self):
        """Authenticate with Gmail API and return the service object."""
        creds = None
        token_path = os.path.join(os.path.dirname(__file__), 'token.pickle')
        
        # Load existing credentials from token.pickle if available
        if os.path.exists(token_path):
            with open(token_path, 'rb') as token:
                creds = pickle.load(token)
        
        # If credentials are not valid, refresh or get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                creds_path = os.path.join(os.path.dirname(__file__), 'credentials.json')
                flow = InstalledAppFlow.from_client_secrets_file(
                    creds_path, 
                    SCOPES,
                    redirect_uri='http://localhost:8080'  # Explicitly set redirect URI
                )
                print("Please make sure this redirect URI is registered in your Google Cloud Console:")
                print("http://localhost:8080")
                creds = flow.run_local_server(port=8080)  # Use a consistent port
            
            # Save credentials for next run
            with open(token_path, 'wb') as token:
                pickle.dump(creds, token)
        
        return build('gmail', 'v1', credentials=creds)
    
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
    
    def _extract_domain(self, email_address):
        """Extract domain from email address."""
        match = re.search(r'@([\w.-]+)', email_address)
        if match:
            return match.group(1).lower()
        return ""
    
    def _is_direct_recipient(self, headers):
        """Check if the email is directly addressed to the user."""
        to_field = next((h['value'] for h in headers if h['name'].lower() == 'to'), '')
        return self.user_email and self.user_email.lower() in to_field.lower()
    
    def _is_cc_recipient(self, headers):
        """Check if the user is CC'd on the email."""
        cc_field = next((h['value'] for h in headers if h['name'].lower() == 'cc'), '')
        return self.user_email and self.user_email.lower() in cc_field.lower()
    
    def _get_email_headers(self, email_id):
        """Get headers for an email by ID."""
        try:
            message = self.service.users().messages().get(
                userId=self.user_id,
                id=email_id,
                format='metadata',
                metadataHeaders=['To', 'Cc', 'From', 'Subject']
            ).execute()
            return message.get('payload', {}).get('headers', [])
        except Exception as e:
            print(f"Error fetching email headers: {e}")
            return []
    
    def _is_known_client(self, domain):
        """Check if domain belongs to a known client."""
        # This would be populated with actual client domains
        known_client_domains = ['client1.com', 'client2.org', 'client3.net']
        return domain in known_client_domains
    
    def _is_known_sender(self, sender):
        """Check if sender is a known contact."""
        # This would be populated with known contacts or could check against contacts API
        return True  # Placeholder implementation
    
    def _contains_urgent_language(self, subject, body):
        """Check if email contains urgent language."""
        urgent_terms = ['urgent', 'asap', 'immediately', 'emergency', 'critical']
        for term in urgent_terms:
            if term in subject.lower() or term in body.lower():
                return True
        return False
    
    def _is_alert_email(self, subject, body):
        """Check if email is an alert notification."""
        alert_terms = ['alert', 'notification', 'warning', 'error', 'failed']
        for term in alert_terms:
            if term in subject.lower():
                return True
        return False
    
    def _get_client_domains(self):
        """Return list of client domains."""
        # This would be populated with actual client domains
        return ['client1.com', 'client2.org', 'client3.net']
    
    def _get_project_codes(self):
        """Return list of project codes."""
        # This would be populated with actual project codes
        return ['proj-001', 'proj-002', 'client-a-website', 'seo-campaign']

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
        if template is None:
            # Default response template
            template = (
                f"Hi {self.extract_name(email_info['sender'])},\n\n"
                "Thank you for your email. I've received your message and will get back to you soon.\n\n"
                "Best regards,\n"
                "Your Name"
            )
        
        to = self.extract_email(email_info['sender'])
        subject = f"Re: {email_info['subject']}"
        
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
    
    def setup_huggingface(self, model_name="Qwen/Qwen2.5-0.5B-Instruct", hf_token=None, no_prompt=False):
        """Set up Hugging Face model for content generation."""
        try:
            if hf_token:
                login(hf_token)
                print("Logged in to Hugging Face successfully!")
            
            print(f"Loading model {model_name}...")
            self.hf_tokenizer = AutoTokenizer.from_pretrained(model_name)
            
            # Handle potential SDPA warning by setting attn_implementation
            print("Note: Using eager attention implementation to avoid SDPA warnings")
            
            # Load model with appropriate settings
            if torch.cuda.is_available():
                print("Loading model on GPU...")
                try:
                    self.hf_model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        torch_dtype=torch.float16,
                        device_map="auto",
                        attn_implementation="eager"  # Use eager implementation to avoid SDPA warnings
                    )
                except Exception as e:
                    print(f"Failed with float16, falling back to float32: {e}")
                    self.hf_model = AutoModelForCausalLM.from_pretrained(
                        model_name,
                        device_map="auto",
                        attn_implementation="eager"  # Use eager implementation to avoid SDPA warnings
                    )
            else:
                print("Loading model on CPU...")
                self.hf_model = AutoModelForCausalLM.from_pretrained(
                    model_name,
                    low_cpu_mem_usage=True,
                    attn_implementation="eager"  # Use eager implementation to avoid SDPA warnings
                ).to(self.device)
            
            print(f"Model {model_name} loaded successfully on {self.device}!")
            return True
        except Exception as e:
            print(f"Error setting up Hugging Face model: {e}")
            return False
    
    def generate_text(self, prompt, max_length=100):
        """Generate text using the loaded Hugging Face model."""
        if not self.hf_model or not self.hf_tokenizer:
            print("Hugging Face model not initialized. Call setup_huggingface() first.")
            return None
        
        try:
            # Move inputs to device (GPU if available)
            inputs = self.hf_tokenizer(prompt, return_tensors="pt").to(self.device)
            
            # Configure generation parameters
            generation_config = {
                "max_length": max_length,
                "num_return_sequences": 1,
                "temperature": 0.7,
                "do_sample": True,
                "no_repeat_ngram_size": 2
            }
            
            # Generate text with memory optimization
            with torch.no_grad():  # Disable gradient calculation for inference
                if self.device.type == "cuda":
                    # Use efficient generation for CUDA
                    torch.cuda.empty_cache()  # Clear GPU memory before generation
                
                # Generate text
                outputs = self.hf_model.generate(**inputs, **generation_config)
                
            # Move outputs back to CPU for tokenizer processing
            outputs = outputs.cpu()
            
            generated_text = self.hf_tokenizer.decode(outputs[0], skip_special_tokens=True)
            return generated_text
        except Exception as e:
            print(f"Error generating text: {e}")
            return None
    
    def generate_email(self, topic=None, recipient_name=None, original_subject=None, original_content=None):
        """Generate an email using the Hugging Face model with context from original email."""
        if not self.hf_model:
            print("Hugging Face model not initialized. Using default email text.")
            return f"Thank you for your email regarding '{original_subject}'. I've received your message and will get back to you with a more detailed response soon.\n\nBest regards,\nEmmy"
        
        # Create a prompt for the model with context from original email
        prompt = f"Write a professional email response. I am Haider Farooq a Data Scientist. reply to emails accordingly. Make sure proper formatting is done"
        if recipient_name:
            prompt += f" to {recipient_name}"
        if original_subject:
            prompt += f" regarding '{original_subject}'"
        
        # Add context from original email if available
        if original_content:
            # Truncate the content if it's too long to fit in the prompt
            max_context_length = 200
            context = original_content[:max_context_length] + "..." if len(original_content) > max_context_length else original_content
            prompt += f"\n\nOriginal email content:\n{context}\n\nWrite a professional and helpful response:"
        else:
            prompt += ":\n\n"
        
        generated_text = self.generate_text(prompt, max_length=500)
        if not generated_text:
            return f"Thank you for your email regarding '{original_subject}'. I've received your message and will get back to you with a more detailed response soon.\n\nBest regards,\nEmmy"
            
        # Clean up the generated text to extract only the email body
        clean_email = self._extract_email_body(generated_text)
        
        # Replace [Your Name] placeholder with Emmy
        clean_email = clean_email.replace("[Your Name]", "Emmy")
        
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

def main():
    # GPU diagnostics
    print("\n--- GPU Diagnostics ---")
    print(f"PyTorch version: {torch.__version__}")
    print(f"CUDA available: {torch.cuda.is_available()}")
    print(f"CUDA version: {torch.version.cuda if torch.cuda.is_available() else 'Not available'}")
    if torch.cuda.is_available():
        print(f"Device count: {torch.cuda.device_count()}")
        print(f"Device name: {torch.cuda.get_device_name(0)}")
    else:
        print("No GPU detected. Check CUDA installation or use a smaller model.")
    print("---------------------\n")
    
    assistant = GmailAssistant()
    
    # Get user's email address
    user_email = assistant.get_user_email()
    print(f"Authenticated as: {user_email}")
    
    # Get Hugging Face token
    hf_token = args.hf_token
    if not args.no_prompt and not hf_token:
        try:
            hf_token = input("Enter your Hugging Face token (press Enter to skip): ").strip() or None
        except KeyboardInterrupt:
            print("\nOperation cancelled by user. Using model without token.")
            hf_token = None
    
    # Verify Hugging Face login if token is provided
    if hf_token:
        try:
            login(hf_token)
            print("✓ Successfully logged in to Hugging Face")
        except Exception as e:
            print(f"! Error logging in to Hugging Face: {e}")
            print("  Continuing with limited access...")
    else:
        print("! No Hugging Face token provided. Some models may not be accessible.")
    
    # Use only the Qwen model
    model_name = "Qwen/Qwen2.5-0.5B-Instruct"
    print(f"Using model: {model_name}")
    
    assistant.setup_huggingface(
        model_name=model_name,
        hf_token=hf_token, 
        no_prompt=args.no_prompt
    )
    
    # Sort emails
    sorted_emails = assistant.sort_emails()
    print("--- Sorted Emails ---")
    for category, emails in sorted_emails.items():
        print(f"\n{category.upper()} ({len(emails)})")
        for email in emails:
            print(f"  - {email['subject']} (From: {email['sender']})")
    
    # Process important emails and send automatic replies
    print("\n--- Processing Important Emails ---")
    important_emails = sorted_emails.get('priority_inbox', [])
    if not important_emails:
        print("No important emails to process.")
    else:
        print(f"Found {len(important_emails)} important emails requiring responses.")
        
        for email in important_emails:
            print(f"\nProcessing: {email['subject']}")
            sender_email = assistant.extract_email(email['sender'])
            sender_name = assistant.extract_name(email['sender'])
            
            # Generate appropriate response based on email content
            device_info = "GPU (CUDA)" if torch.cuda.is_available() else "CPU"
            print(f"Generating response to {sender_name} ({sender_email}) using {device_info}...")
            response_body = assistant.generate_email(
                recipient_name=sender_name,
                original_subject=email['subject'],
                original_content=email['body']
            )
            
            print("Sending response...")
            reply_subject = f"Re: {email['subject']}"
            response = assistant.send_email(
                to=sender_email,
                subject=reply_subject,
                body=response_body
            )
            
            # Mark the email as read after processing
            assistant.mark_as_read(email['id'])
            print(f"✓ Response sent to {sender_email} and email marked as read")

    print("\nEmail automation completed successfully!")
    
    # Return for Streamlit integration
    return sorted_emails

if __name__ == '__main__':
    main()
