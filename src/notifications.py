import atexit

from PyQt6.QtCore import QProcess

NOTIFIER_APP = "gh_notify"


def tell_app(app: str, command: str):
    process = QProcess()
    process.start("osascript", ["-e", f'tell application "{app}" to {command}'])
    process.waitForFinished()


def notify(title: str, message: str, notifier_app: str = NOTIFIER_APP):
    # Start the app hidden
    process = QProcess()
    process.start(
        "osascript",
        [
            "-e",
            f'tell application "{notifier_app}" to run',
            "-e",
            f'tell application "{notifier_app}" to set visible to false',
        ],
    )
    process.waitForFinished()
    # Send notification
    tell_app(notifier_app, f'notify("{title}", "{message}")')
    # Kill the app after sending notification
    kill_notifier()


def kill_notifier():

    tell_app(NOTIFIER_APP, "quit")


# Always register the kill_notifier function to run when the script exits
atexit.register(kill_notifier)
