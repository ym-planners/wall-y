import os
import sys
import time
import datetime
import requests
import ctypes
import re
import traceback
import socket
from bs4 import BeautifulSoup
from PyQt5 import QtWidgets, QtGui, QtCore
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QMessageBox, QDialog, QVBoxLayout, QCheckBox, QPushButton
from PIL import Image

# Single instance check
def is_already_running():
    """Check if another instance is already running using a socket"""
    try:
        # Try to create a socket on a specific port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 47200))  # Use a unique port number
        sock.listen(1)
        return False
    except socket.error:
        return True

class APODWallpaper:
    def __init__(self):
        self.base_url = "https://apod.nasa.gov/apod/"
        self.archive_url = "https://apod.nasa.gov/apod/archivepixFull.html"
        
        # Change download directory to wall-y under Pictures
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        self.download_dir = os.path.join(pictures_dir, "wall-y")
        
        # Create download directory if it doesn't exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    def get_latest_image_url(self):
        """Scrape the APOD archive page to find the latest image URL"""
        try:
            response = requests.get(self.archive_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Find the first link which should be the most recent image
            links = soup.find_all('a')
            for link in links:
                href = link.get('href')
                if href and href.startswith('ap') and href.endswith('.html'):
                    # Get the image page
                    image_page_url = self.base_url + href
                    image_page = requests.get(image_page_url, timeout=10)
                    image_soup = BeautifulSoup(image_page.text, 'html.parser')
                    
                    # Find image link - typically it's an <a> tag with an <img> inside
                    for img_link in image_soup.find_all('a'):
                        if img_link.find('img'):
                            img_href = img_link.get('href')
                            if img_href and (img_href.endswith('.jpg') or img_href.endswith('.png')):
                                if img_href.startswith('http'):
                                    return img_href
                                else:
                                    return self.base_url + img_href
            
            return None
        except Exception as e:
            print(f"Error getting latest image URL: {e}")
            traceback.print_exc()
            return None
    
    def download_image(self, url):
        """Download the image from the given URL"""
        try:
            response = requests.get(url, stream=True, timeout=30)
            if response.status_code == 200:
                # Extract filename from URL
                filename = url.split('/')[-1]
                filepath = os.path.join(self.download_dir, filename)
                
                # Save the image
                with open(filepath, 'wb') as f:
                    for chunk in response.iter_content(1024):
                        f.write(chunk)
                
                # Verify the image can be opened
                try:
                    with Image.open(filepath) as img:
                        # Check if image is valid and has reasonable dimensions
                        if img.width < 800 or img.height < 600:
                            print(f"Image dimensions too small: {img.width}x{img.height}")
                            return None
                except Exception as e:
                    print(f"Invalid image file: {e}")
                    return None
                
                return filepath
            else:
                print(f"Failed to download image: {response.status_code}")
                return None
        except Exception as e:
            print(f"Error downloading image: {e}")
            traceback.print_exc()
            return None
    
    def set_wallpaper(self, image_path):
        """Set the downloaded image as wallpaper"""
        try:
            # Windows specific code to set wallpaper
            ctypes.windll.user32.SystemParametersInfoW(20, 0, image_path, 3)
            return True
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            traceback.print_exc()
            return False
    
    def update_wallpaper(self):
        """Main function to update the wallpaper"""
        try:
            image_url = self.get_latest_image_url()
            if image_url:
                image_path = self.download_image(image_url)
                if image_path:
                    success = self.set_wallpaper(image_path)
                    return success, image_path
            return False, None
        except Exception as e:
            print(f"Error updating wallpaper: {e}")
            traceback.print_exc()
            return False, None


class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("APOD Wallpaper Settings")
        self.resize(300, 150)
        
        layout = QVBoxLayout()
        
        # Auto-start option
        self.autostart_checkbox = QCheckBox("Start with Windows")
        self.autostart_checkbox.setChecked(self.is_autostart_enabled())
        layout.addWidget(self.autostart_checkbox)
        
        # Save button
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        layout.addWidget(save_button)
        
        self.setLayout(layout)
    
    def is_autostart_enabled(self):
        """Check if auto-start is enabled"""
        import winreg as reg
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run")
            reg.QueryValueEx(key, "APODWallpaper")
            reg.CloseKey(key)
            return True
        except:
            return False
    
    def save_settings(self):
        """Save settings"""
        if self.autostart_checkbox.isChecked():
            self.add_to_startup()
        else:
            self.remove_from_startup()
        self.accept()
    
    def add_to_startup(self):
        """Add the application to Windows startup"""
        import winreg as reg
        try:
            file_path = os.path.abspath(sys.argv[0])
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
            reg.SetValueEx(key, "APODWallpaper", 0, reg.REG_SZ, file_path)
            reg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error adding to startup: {e}")
            return False
    
    def remove_from_startup(self):
        """Remove the application from Windows startup"""
        import winreg as reg
        try:
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
            reg.DeleteValue(key, "APODWallpaper")
            reg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error removing from startup: {e}")
            return False


class SystemTrayApp(QtWidgets.QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        self.setQuitOnLastWindowClosed(False)
        
        # Initialize wallpaper handler
        self.wallpaper = APODWallpaper()
        
        # Create system tray icon
        self.tray = QSystemTrayIcon()
        
        # Set icon - use the specified icon file if it exists
        icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "image-face.ico")
        if os.path.exists(icon_path):
            self.tray.setIcon(QtGui.QIcon(icon_path))
        else:
            # Fallback to a simple icon
            self.tray.setIcon(QtGui.QIcon(QtGui.QPixmap(16, 16)))
        
        self.tray.setVisible(True)
        
        # Create menu
        self.menu = QMenu()
        
        # Add actions
        self.update_action = QAction("Update Wallpaper Now")
        self.update_action.triggered.connect(self.manual_update)
        self.menu.addAction(self.update_action)
        
        self.open_folder_action = QAction("Open Wallpapers Folder")
        self.open_folder_action.triggered.connect(self.open_wallpapers_folder)
        self.menu.addAction(self.open_folder_action)
        
        self.settings_action = QAction("Settings")
        self.settings_action.triggered.connect(self.show_settings)
        self.menu.addAction(self.settings_action)
        
        self.menu.addSeparator()
        
        self.exit_action = QAction("Exit")
        self.exit_action.triggered.connect(self.quit)
        self.menu.addAction(self.exit_action)
        
        # Set the menu
        self.tray.setContextMenu(self.menu)
        
        # Set up timer for checking at midnight ET (6:00 AM CEST)
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.check_scheduled_update)
        
        # Start timer - check every 15 minutes
        self.timer.start(15 * 60 * 1000)  # 15 minutes in milliseconds
        
        # Initial check
        QtCore.QTimer.singleShot(1000, self.initial_check)
    
    def initial_check(self):
        """Check if we need to update on startup"""
        self.check_for_update(show_notification=False)
    
    def is_update_time(self):
        """Check if it's time to update based on midnight ET (6:00 AM CEST)"""
        now = datetime.datetime.now()
        
        # Convert current time to ET (UTC-4 during daylight saving, UTC-5 standard)
        # This is a simplified approach - for production, use pytz for proper timezone handling
        utc_offset = -4  # Assuming EDT (daylight saving time)
        
        # Get current hour in ET
        et_hour = (now.hour + utc_offset) % 24
        
        # Check if we're past midnight ET and haven't updated today
        return et_hour >= 0 and et_hour < 1  # Between midnight and 1 AM ET
    
    def check_scheduled_update(self):
        """Check if it's time for scheduled update"""
        if self.is_update_time():
            self.check_for_update()
    
    def check_for_update(self, show_notification=True):
        """Check if we need to update the wallpaper"""
        now = datetime.datetime.now()
        
        # Get last update time from a simple file
        last_update_file = os.path.join(self.wallpaper.download_dir, "last_update.txt")
        should_update = True
        
        if os.path.exists(last_update_file):
            with open(last_update_file, 'r') as f:
                try:
                    last_update = datetime.datetime.strptime(f.read().strip(), "%Y-%m-%d")
                    if last_update.date() == now.date():
                        should_update = False
                except:
                    pass
        
        if should_update:
            success, image_path = self.wallpaper.update_wallpaper()
            if success:
                if show_notification:
                    self.tray.showMessage("APOD Wallpaper", "Wallpaper updated successfully!", QSystemTrayIcon.Information, 3000)
                
                # Update last update time
                with open(last_update_file, 'w') as f:
                    f.write(now.strftime("%Y-%m-%d"))
            elif show_notification:
                self.tray.showMessage("APOD Wallpaper", "Failed to update wallpaper.", QSystemTrayIcon.Critical, 3000)
    
    def manual_update(self):
        """Manually update the wallpaper"""
        try:
            success, image_path = self.wallpaper.update_wallpaper()
            if success:
                self.tray.showMessage("APOD Wallpaper", "Wallpaper updated successfully!", QSystemTrayIcon.Information, 3000)
                
                # Update last update time
                last_update_file = os.path.join(self.wallpaper.download_dir, "last_update.txt")
                with open(last_update_file, 'w') as f:
                    f.write(datetime.datetime.now().strftime("%Y-%m-%d"))
            else:
                self.tray.showMessage("APOD Wallpaper", "Failed to update wallpaper.", QSystemTrayIcon.Critical, 3000)
        except Exception as e:
            self.tray.showMessage("APOD Wallpaper", f"Error: {str(e)}", QSystemTrayIcon.Critical, 3000)
    
    def open_wallpapers_folder(self):
        """Open the wallpapers folder in explorer"""
        try:
            os.startfile(self.wallpaper.download_dir)
        except Exception as e:
            self.tray.showMessage("APOD Wallpaper", f"Error opening folder: {str(e)}", QSystemTrayIcon.Critical, 3000)
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog()
        dialog.exec_()


if __name__ == "__main__":
    # Check if another instance is already running
    if is_already_running():
        app = QtWidgets.QApplication(sys.argv)
        QMessageBox.warning(None, "APOD Wallpaper", 
                           "Another instance of APOD Wallpaper is already running.\n"
                           "Please check your system tray for the running application.")
        sys.exit(1)
    else:
        app = SystemTrayApp(sys.argv)
        sys.exit(app.exec_())