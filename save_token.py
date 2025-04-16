"""
Utility to save token from a successful local authentication to secrets.toml
This helps prepare for deployment by copying token information to your secrets.
"""
import os
import json
import pickle
import argparse
import toml

def update_secrets_with_token():
    """Updates secrets.toml with token information from token.pickle"""
    token_path = 'token.pickle'
    secrets_path = os.path.join('.streamlit', 'secrets.toml')
    
    # Check if files exist
    if not os.path.exists(token_path):
        print(f"Error: {token_path} not found. Please authenticate locally first.")
        return False
    
    if not os.path.exists(secrets_path):
        print(f"Error: {secrets_path} not found. Please create it first.")
        return False
    
    try:
        # Load token from pickle file
        with open(token_path, 'rb') as token_file:
            token_data = pickle.load(token_file)
        
        # Convert token to JSON format
        token_json = json.loads(token_data.to_json())
        token_json_str = json.dumps(token_json, indent=2)
        
        # Read current secrets
        with open(secrets_path, 'r') as f:
            secrets_content = f.read()
        
        # Check if token_json already exists in the file
        if 'token_json' in secrets_content:
            # If it exists, replace it
            lines = secrets_content.split('\n')
            in_google_section = False
            updating_token = False
            updated_content = []
            token_updated = False
            
            for line in lines:
                if line.strip() == '[google]':
                    in_google_section = True
                    updated_content.append(line)
                elif in_google_section and line.strip().startswith('token_json'):
                    # This is the existing token_json line
                    updated_content.append(f'token_json = """{token_json_str}"""')
                    token_updated = True
                    updating_token = True
                elif updating_token and line.strip().startswith('"') and not line.strip().endswith('"'):
                    # Skip lines that are part of the existing token_json
                    continue
                elif updating_token and line.strip().endswith('"""'):
                    # End of existing token_json
                    updating_token = False
                    continue
                elif line.strip().startswith('[') and line.strip() != '[google]':
                    # New section, end of google section
                    in_google_section = False
                    updating_token = False
                    # Add token_json if we haven't updated it yet
                    if in_google_section and not token_updated:
                        updated_content.append(f'token_json = """{token_json_str}"""')
                    updated_content.append(line)
                else:
                    updated_content.append(line)
            
            # Write updated content back to file
            with open(secrets_path, 'w') as f:
                f.write('\n'.join(updated_content))
        else:
            # If token_json doesn't exist, append it to the google section
            if '[google]' in secrets_content:
                # Split the content at the google section
                parts = secrets_content.split('[google]')
                google_section = '[google]' + parts[1]
                
                # Split the google section at the next section if there is one
                if '[' in google_section[8:]:  # Skip the initial [google]
                    next_section_index = google_section[8:].find('[') + 8
                    before_next_section = google_section[:next_section_index]
                    after_next_section = google_section[next_section_index:]
                    
                    # Insert token_json before the next section
                    updated_content = parts[0] + before_next_section + f'\ntoken_json = """{token_json_str}"""\n' + after_next_section
                else:
                    # No more sections, just append to google section
                    updated_content = parts[0] + google_section + f'\ntoken_json = """{token_json_str}"""\n'
            else:
                # If no google section exists, append it to the end
                updated_content = secrets_content + f'\n[google]\ntoken_json = """{token_json_str}"""\n'
            
            # Write updated content back to file
            with open(secrets_path, 'w') as f:
                f.write(updated_content)
        
        print(f"Successfully updated {secrets_path} with token information")
        return True
    
    except Exception as e:
        print(f"Error updating secrets: {str(e)}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Update Streamlit secrets with Gmail token')
    parser.add_argument('--force', action='store_true', help='Force update even if token already exists')
    args = parser.parse_args()
    
    success = update_secrets_with_token()
    
    if success:
        print("\nToken information has been successfully saved to your secrets.toml file.")
        print("When deploying to Streamlit Cloud, make sure to:")
        print("1. Include this token information in your Streamlit Cloud secrets")
        print("2. Keep the redirect_uris properly configured in your Google Cloud console")
        print("3. Ensure the Google API project is properly configured\n")
    else:
        print("\nFailed to update token information.")

if __name__ == "__main__":
    main()
