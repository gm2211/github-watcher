from PyQt6.QtWidgets import QSystemTrayIcon
from PyQt6.QtGui import QIcon

def notify(title, message):
    """Send a system notification"""
    tray = QSystemTrayIcon()
    
    # Create a simple default icon if none exists
    icon = QIcon()
    if not icon.isNull():
        tray.setIcon(icon)
    else:
        # Create a 1x1 pixel icon as fallback
        from PyQt6.QtGui import QPixmap
        px = QPixmap(1, 1)
        px.fill()  # Fills with black by default
        tray.setIcon(QIcon(px))
    
    tray.show()  # Need to show before we can send message
    tray.showMessage(
        title,
        message,
        QSystemTrayIcon.MessageIcon.Information,
        3000  # Display for 3 seconds
    )
    tray.hide()  # Hide after sending
