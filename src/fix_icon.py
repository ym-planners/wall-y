import os
import sys
from PyQt5 import QtWidgets, QtGui, QtCore

def create_icon_test():
    """Test if the icon can be loaded properly"""
    app = QtWidgets.QApplication(sys.argv)
    
    # Get the icon path
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/wall-y-round.ico")
    
    # Try to load the icon
    if os.path.exists(icon_path):
        print(f"Icon file exists at: {icon_path}")
        try:
            # Create a proper icon with multiple sizes
            icon = QtGui.QIcon()
            icon.addFile(icon_path, QtCore.QSize(16, 16))
            icon.addFile(icon_path, QtCore.QSize(24, 24))
            icon.addFile(icon_path, QtCore.QSize(32, 32))
            icon.addFile(icon_path, QtCore.QSize(48, 48))
            
            print(f"Icon loaded successfully: {not icon.isNull()}")
            
            # Create a simple window to show the icon
            window = QtWidgets.QWidget()
            window.setWindowTitle("Icon Test")
            window.setWindowIcon(icon)
            
            # Create a label to show the icon
            label = QtWidgets.QLabel("Icon should be visible in the window title and taskbar")
            layout = QtWidgets.QVBoxLayout()
            layout.addWidget(label)
            
            # Also add the icon as an image
            icon_label = QtWidgets.QLabel()
            pixmap = icon.pixmap(64, 64)
            icon_label.setPixmap(pixmap)
            layout.addWidget(icon_label)
            
            # Create a system tray icon to test
            tray = QtWidgets.QSystemTrayIcon()
            tray.setIcon(icon)
            tray.setVisible(True)
            tray.setToolTip("Icon Test")
            
            # Create a menu with fixed width
            menu = QtWidgets.QMenu()
            menu.setFixedWidth(300)
            
            # Add a test action
            test_action = QtWidgets.QAction("Test Action")
            menu.addAction(test_action)
            
            # Set the menu
            tray.setContextMenu(menu)
            
            window.setLayout(layout)
            window.show()
            
            return app.exec_()
        except Exception as e:
            print(f"Error loading icon: {e}")
    else:
        print(f"Icon file does not exist at: {icon_path}")

if __name__ == "__main__":
    create_icon_test()