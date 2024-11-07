import subprocess
import webbrowser
import sys
from urllib.parse import urlencode
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit, QLabel
from PyQt6.QtCore import Qt

KEYCHAIN_SERVICE = 'github_api_key'
KEYCHAIN_ACCOUNT = 'token'

# Define the required permissions
REQUIRED_SCOPES = [
    'repo',
    'read:org',
    'read:user',
    'read:project',
    'read:discussion',
    'read:packages'
]

class TokenDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("GitHub API Token")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Add explanation text
        info_label = QLabel(
            "A GitHub API token is needed to monitor pull requests.\n\n"
            "Either paste an existing token below, or click 'Create New Token' "
            "to open GitHub with the required permissions pre-selected."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Add token input
        self.token_input = QLineEdit()
        self.token_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.token_input.setPlaceholderText("Paste your GitHub token here")
        layout.addWidget(self.token_input)
        
        # Add buttons
        button_layout = QHBoxLayout()
        
        create_button = QPushButton("Create New Token")
        create_button.clicked.connect(self.open_github)
        button_layout.addWidget(create_button)
        
        button_layout.addStretch()
        
        save_button = QPushButton("Save Token")
        save_button.setDefault(True)
        save_button.clicked.connect(self.accept)
        button_layout.addWidget(save_button)
        
        layout.addLayout(button_layout)
        self.setLayout(layout)
    
    def open_github(self):
        base_url = 'https://github.com/settings/tokens/new'
        params = {
            'description': 'GitHub PR Watcher',
            'scopes': ','.join(REQUIRED_SCOPES)
        }
        url = f"{base_url}?{urlencode(params)}"
        webbrowser.open(url)
    
    def get_token(self):
        return self.token_input.text().strip()

def get_github_api_key():
    try:
        # Try to retrieve the API key from Keychain
        result = subprocess.run(
            ['security', 'find-generic-password', '-s', KEYCHAIN_SERVICE, '-a', KEYCHAIN_ACCOUNT, '-w'],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
        
    except subprocess.CalledProcessError:
        dialog = TokenDialog()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            token = dialog.get_token()
            if token:
                try:
                    subprocess.run(
                        ['security', 'add-generic-password', '-s', KEYCHAIN_SERVICE, 
                         '-a', KEYCHAIN_ACCOUNT, '-w', token],
                        check=True
                    )
                    return token
                except subprocess.CalledProcessError:
                    return None
        
        return None 