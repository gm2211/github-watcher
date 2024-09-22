# github_auth.py

import subprocess
import webbrowser
import sys

KEYCHAIN_SERVICE = 'GithubAPIKey'
KEYCHAIN_ACCOUNT = 'github_api'


def get_github_api_key():
    try:
        # Try to retrieve the API key from Keychain
        result = subprocess.run(
            ['security', 'find-generic-password', '-s', KEYCHAIN_SERVICE, '-a', KEYCHAIN_ACCOUNT, '-w'],
            capture_output=True, text=True, check=True
            )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        # If the key is not found, prompt the user to create one
        print("GitHub API key not found in Keychain.")
        create_new_key = input("Would you like to create a new API key? (y/n): ").lower()

        if create_new_key == 'y':
            webbrowser.open('https://github.com/settings/tokens/new')
            api_key = input("Please enter your new GitHub API key: ")

            # Store the new API key in Keychain
            try:
                subprocess.run(
                    ['security', 'add-generic-password', '-s', KEYCHAIN_SERVICE, '-a', KEYCHAIN_ACCOUNT, '-w', api_key],
                    check=True
                    )
                print("API key stored successfully in Keychain.")
                return api_key
            except subprocess.CalledProcessError:
                print("Failed to store API key in Keychain.")
                sys.exit(1)
        else:
            print("Cannot proceed without a GitHub API key.")
            sys.exit(1)


if __name__ == "__main__":
    api_key = get_github_api_key()
    print(f"GitHub API Key: {api_key}")
