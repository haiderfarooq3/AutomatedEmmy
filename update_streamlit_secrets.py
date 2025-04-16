"""
Helper script to update Streamlit secrets with token information.
This should only be used locally to prepare for deployment, not on the deployed app.
"""
import os
import json
import pickle
import argparse
import streamlit as st

def main():
    parser = argparse.ArgumentParser(description='Update Streamlit secrets with token information')
    parser.add_argument('--update-token', action='store_true', help='Update token information in secrets.toml')
    parser.add_argument('--export-secrets', action='store_true', help='Export all required secrets for deployment')
    args = parser.parse_args()
    
    # Path to local files
    token_path = 'token.pickle'
    secrets_path = os.path.join('.streamlit', 'secrets.toml')
    export_path = 'streamlit_secrets_for_deployment.toml'
    
    if args.update_token:
        # Check if token.pickle exists
        if not os.path.exists(token_path):
            print(f"Error: {token_path} not found. Please authenticate locally first.")
            return
        
        # Load token from pickle file
        with open(token_path, 'rb') as token_file:
            token_data = pickle.load(token_file)
        
        # Convert token to JSON
        token_json = token_data.to_json()
        
        # Update secrets.toml file
        if not os.path.exists(secrets_path):
            print(f"Error: {secrets_path} not found. Please create it first.")
            return
        
        # Read existing secrets file
        with open(secrets_path, 'r') as f:
            secrets_content = f.read()
        
        # Format the token_json for TOML
        formatted_token = json.dumps(json.loads(token_json), indent=2)
        token_toml = f'\n[google]\ntoken_json = """{formatted_token}"""'
        
        # Check if [google] section already exists
        if '[google]' in secrets_content:
            lines = secrets_content.split('\n')
            updated_lines = []
            in_google_section = False
            token_added = False
            
            for line in lines:
                if line.strip() == '[google]':
                    in_google_section = True
                    updated_lines.append(line)
                elif in_google_section and line.strip().startswith('token_json'):
                    # Replace existing token_json line
                    updated_lines.append(f'token_json = """{formatted_token}"""')
                    token_added = True
                elif line.strip().startswith('[') and line.strip() != '[google]':
                    # End of google section
                    if in_google_section and not token_added:
                        updated_lines.append(f'token_json = """{formatted_token}"""')
                    in_google_section = False
                    updated_lines.append(line)
                else:
                    updated_lines.append(line)
            
            # If still in google section at the end of the file and token not added
            if in_google_section and not token_added:
                updated_lines.append(f'token_json = """{formatted_token}"""')
            
            # Write updated content back to file
            with open(secrets_path, 'w') as f:
                f.write('\n'.join(updated_lines))
        else:
            # Append token information to secrets file
            with open(secrets_path, 'a') as f:
                f.write(token_toml)
        
        print(f"Updated {secrets_path} with token information")
    
    if args.export_secrets:
        # Export all required secrets for deployment
        if not os.path.exists(secrets_path):
            print(f"Error: {secrets_path} not found. Please create it first.")
            return
        
        # Read existing secrets file
        with open(secrets_path, 'r') as f:
            secrets_content = f.read()
        
        # Also add config.json if it exists
        if os.path.exists('config.json'):
            with open('config.json', 'r') as f:
                config_json = f.read()
                config_toml = f'\n[config]\n{config_json}\n'
                secrets_content += config_toml
        
        # Write to export file
        with open(export_path, 'w') as f:
            f.write(secrets_content)
        
        print(f"Exported all secrets to {export_path}")
        print("To deploy:")
        print("1. Go to your Streamlit Cloud dashboard")
        print("2. Select your app")
        print("3. Go to 'Settings' > 'Secrets'")
        print(f"4. Copy the contents of {export_path} into the secrets field")
        print("5. Click 'Save'")

if __name__ == "__main__":
    main()
