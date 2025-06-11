import os
import sys
from PyQt5 import QtWidgets, QtGui, QtCore

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    # Create a system tray icon
    tray = QtWidgets.QSystemTrayIcon()
    
    # Use wall-y-round.ico
    icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/wall-y-round.ico")
    
    if os.path.exists(icon_path):
        print(f"Loading icon from: {icon_path}")
        icon = QtGui.QIcon(icon_path)
        tray.setIcon(icon)
        tray.setVisible(True)
        
        # Create a menu
        menu = QtWidgets.QMenu()
        menu.addAction("Test")
        tray.setContextMenu(menu)
        
        return app.exec_()
    else:
        print(f"Icon not found at: {icon_path}")
        return 1

if __name__ == "__main__":
    sys.exit(main())