# Email Automation Tool

This tool automatically handles emails by:
1. Sending professionally formatted emails with proper subject fields
2. Automatically signing emails
3. Replying to important unread emails
4. Extracting recipient emails from incoming messages

## Setup

1. Make sure Python 3.6+ is installed
2. Install required dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Set up your email password as an environment variable for security:
   - Windows: `set EMAIL_PASSWORD=your_password`
   - Linux/Mac: `export EMAIL_PASSWORD=your_password`
   
   **Note:** For Gmail, you'll need to use an App Password instead of your regular password.

## Usage

1. Run the script:
   ```
   python email_automation.py
   ```

2. To send a project update, modify the `send_project_update` function with the appropriate recipients.

3. The script will continuously check for important emails and respond to them.

## Customization

- Edit the `check_if_important` function to customize what makes an email "important"
- Modify the `generate_response` function to create more specific automatic responses
- Update the signature in the `send_email` function if needed

## Security Notes

- Never hardcode your email password in the script
- Use environment variables or a secure configuration file
- Consider using OAuth2 for more secure authentication
