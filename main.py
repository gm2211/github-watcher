# main.py

from notifications import notify, NOTIFIER_APP

if __name__ == "__main__":
    notify(NOTIFIER_APP, "Test from Main", "This is a test notification sent from main.py")
