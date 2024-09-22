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
    tell_app(notifier_app, f'notify("{title}", "{message}")')


def kill_notifier():
    print("Killing notifier..")
    tell_app(NOTIFIER_APP, 'quit')


# Example usage
if __name__ == "__main__":
    is_macos = platform.system() == 'Darwin'
    if not is_macos:
        logging.warning("Notifications are only supported on macOS.")
        sys.exit(-1)

    notify(NOTIFIER_APP, "Hello", "This is a notification")

    atexit.register(kill_notifier)

    time.sleep(1000)
