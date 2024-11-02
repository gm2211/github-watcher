import logging
import os
import platform
import sys
import atexit
import time

NOTIFIER_APP = "gh_notify"


def tell_app(app: str, command: str):
    os.system(f"osascript -e 'tell application \"{app}\" to {command}'")


def notify(notifier_app: str, title: str, message: str):
    # Start the app hidden
    os.system(f"osascript -e 'tell application \"{notifier_app}\" to run' -e 'tell application \"{notifier_app}\" to set visible to false'")
    # Send notification
    tell_app(notifier_app, f'notify("{title}", "{message}")')
    # Kill the app after sending notification
    kill_notifier()


def kill_notifier():
    print("Killing notifier..")
    tell_app(NOTIFIER_APP, 'quit')


# Always register the kill_notifier function to run when the script exits
atexit.register(kill_notifier)

# Example usage
if __name__ == "__main__":
    is_macos = platform.system() == 'Darwin'
    if not is_macos:
        logging.warning("Notifications are only supported on macOS.")
        sys.exit(-1)

    notify(NOTIFIER_APP, "Test", "This is a test notification")
