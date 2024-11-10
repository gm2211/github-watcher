import subprocess
import webbrowser
import sys
from urllib.parse import urlencode
from PyQt6.QtWidgets import QMessageBox, QInputDialog

KEYCHAIN_SERVICE = "github_api_key"
KEYCHAIN_ACCOUNT = "token"

# Define the required permissions
REQUIRED_SCOPES = [
    "repo",
    "read:org",
    "read:user",
    "read:project",
    "read:discussion",
    "read:packages",
]


def get_github_api_key():
    try:
        # Try to retrieve the API key from Keychain
        print("Attempting to retrieve API key from Keychain...")
        print(f"Service: {KEYCHAIN_SERVICE}")
        print(f"Account: {KEYCHAIN_ACCOUNT}")

        result = subprocess.run(
            [
                "security",
                "find-generic-password",
                "-s",
                KEYCHAIN_SERVICE,
                "-a",
                KEYCHAIN_ACCOUNT,
                "-w",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
        token = result.stdout.strip()
        print("Successfully retrieved token from Keychain")
        return token

    except subprocess.CalledProcessError as e:
        print(f"Error accessing keychain: {e}")
        print(f"stderr: {e.stderr}")

        # Show dialog about creating new token
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Question)
        msg.setText("GitHub API key not found in Keychain.")
        msg.setInformativeText(
            "Would you like to create a new API key?\n\n"
            "This will open GitHub in your browser where you can create a token "
            "with the necessary permissions. After creating the token, you'll be "
            "asked to enter it here."
        )
        msg.setStandardButtons(
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        msg.setDefaultButton(QMessageBox.StandardButton.Yes)

        if msg.exec() == QMessageBox.StandardButton.Yes:
            # Construct the URL with preset permissions
            base_url = "https://github.com/settings/tokens/new"
            params = {
                "description": "GitHub PR Watcher",
                "scopes": ",".join(REQUIRED_SCOPES),
            }
            url = f"{base_url}?{urlencode(params)}"

            # Open browser for token creation
            webbrowser.open(url)

            # Show input dialog for the token
            token, ok = QInputDialog.getText(
                None,
                "GitHub API Token",
                "Please paste your new GitHub API token:",
                echo=QInputDialog.EchoMode.Password,
            )

            if ok and token:
                try:
                    # Store the new API key in Keychain
                    subprocess.run(
                        [
                            "security",
                            "add-generic-password",
                            "-s",
                            KEYCHAIN_SERVICE,
                            "-a",
                            KEYCHAIN_ACCOUNT,
                            "-w",
                            token,
                        ],
                        check=True,
                    )
                    print("Successfully stored new token in Keychain")
                    return token
                except subprocess.CalledProcessError as e:
                    print(f"Error storing in keychain: {e}")
                    QMessageBox.critical(
                        None,
                        "Error",
                        "Failed to store API key in Keychain.\nError: " + str(e),
                    )
                    return None
            else:
                QMessageBox.warning(
                    None, "Warning", "Cannot proceed without a GitHub API key."
                )
                return None
        else:
            QMessageBox.warning(
                None, "Warning", "Cannot proceed without a GitHub API key."
            )
            return None


if __name__ == "__main__":
    # Test the keychain access
    from PyQt6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    api_key = get_github_api_key()
    if api_key:
        print("Successfully retrieved API key")
    else:
        print("Failed to get API key")
