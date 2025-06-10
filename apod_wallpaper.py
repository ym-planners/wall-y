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
from PyQt5.QtWidgets import QSystemTrayIcon, QMenu, QAction, QMessageBox, QDialog, QVBoxLayout, QCheckBox, QPushButton, QTextBrowser, QLabel
from PIL import Image, ExifTags
from PIL.PngImagePlugin import PngInfo

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
        self.today_url = "https://apod.nasa.gov/apod/astropix.html"
        self.current_image_url = None
        self.current_description = None
        self.current_title = None
        
        # Change download directory to wall-y under Pictures
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        self.download_dir = os.path.join(pictures_dir, "wall-y")
        
        # Create download directory if it doesn't exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
    
    def get_latest_image_info(self):
        """Scrape the APOD today page to find the latest image URL and description"""
        try:
            response = requests.get(self.today_url, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Get the title - it's typically in the center tag
            title = None
            title_elem = soup.find('title')
            if title_elem:
                title = title_elem.text.strip()
            
            # Get the description - it's typically in the paragraph after the image
            description = None
            explanation = None
            paragraphs = soup.find_all('p')
            if len(paragraphs) >= 2:
                description = paragraphs[1].text.strip()
                # Look for "Explanation:" text which is common in APOD
                for p in paragraphs:
                    text = p.text.strip()
                    if text.startswith("Explanation:"):
                        explanation = text
                        break
            
            # If we found an explanation, use it, otherwise use the description
            if explanation:
                description = explanation
            
            # Find image link - typically it's an <a> tag with an <img> inside
            image_url = None
            for img_link in soup.find_all('a'):
                if img_link.find('img'):
                    img_href = img_link.get('href')
                    if img_href and (img_href.endswith('.jpg') or img_href.endswith('.png')):
                        if img_href.startswith('http'):
                            image_url = img_href
                        else:
                            image_url = self.base_url + img_href
                        break
            
            if image_url:
                return {
                    'url': image_url,
                    'title': title,
                    'description': description,
                    'page_url': self.today_url,
                    'date': datetime.datetime.now().strftime("%Y-%m-%d")
                }
            
            return None
        except Exception as e:
            print(f"Error getting latest image info: {e}")
            traceback.print_exc()
            return None
    
    def download_image(self, url, image_info):
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
                        
                        # Save metadata to the image
                        if filename.lower().endswith('.jpg') or filename.lower().endswith('.jpeg'):
                            # For JPEG, save as a new file with metadata
                            self.save_metadata_to_jpeg(filepath, image_info)
                        elif filename.lower().endswith('.png'):
                            # For PNG, save metadata directly
                            self.save_metadata_to_png(filepath, image_info)
                        
                        # Also save metadata to a separate text file with the same date
                        self.save_metadata_to_file(image_info)
                        
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
    
    def save_metadata_to_jpeg(self, filepath, image_info):
        """Save metadata to JPEG image using EXIF"""
        try:
            # Create a copy of the image to add metadata
            img = Image.open(filepath)
            
            # EXIF data must be added before saving
            exif_data = img.getexif() if hasattr(img, 'getexif') else None
            
            if exif_data is not None:
                # Add metadata to EXIF
                exif_data[0x9286] = image_info.get('description', '')  # UserComment
                exif_data[0x010e] = image_info.get('title', '')  # ImageDescription
                exif_data[0x9003] = image_info.get('date', '')  # DateTimeOriginal
                
                # Save with EXIF data
                img.save(filepath, exif=exif_data)
            else:
                print("EXIF data not supported for this image")
            
            img.close()
        except Exception as e:
            print(f"Error saving metadata to JPEG: {e}")
    
    def save_metadata_to_png(self, filepath, image_info):
        """Save metadata to PNG image"""
        try:
            # Open the image
            img = Image.open(filepath)
            
            # Create PNG info object
            metadata = PngInfo()
            
            # Add metadata
            metadata.add_text("Title", image_info.get('title', ''))
            metadata.add_text("Description", image_info.get('description', ''))
            metadata.add_text("Date", image_info.get('date', ''))
            
            # Save with metadata
            img.save(filepath, pnginfo=metadata)
            img.close()
        except Exception as e:
            print(f"Error saving metadata to PNG: {e}")
    
    def save_metadata_to_file(self, image_info):
        """Save metadata to a text file with the date in the filename"""
        try:
            date_str = image_info.get('date', datetime.datetime.now().strftime("%Y-%m-%d"))
            metadata_file = os.path.join(self.download_dir, f"apod_{date_str}.txt")
            
            with open(metadata_file, 'w', encoding='utf-8') as f:
                f.write(f"Title: {image_info.get('title', '')}\n\n")
                f.write(f"Date: {date_str}\n\n")
                f.write(f"Description: {image_info.get('description', '')}\n\n")
                f.write(f"URL: {image_info.get('page_url', '')}")
        except Exception as e:
            print(f"Error saving metadata to file: {e}")
    
    def read_metadata_from_image(self, image_path):
        """Read metadata from an image file"""
        try:
            if not os.path.exists(image_path):
                return None
            
            img = Image.open(image_path)
            metadata = {}
            
            if image_path.lower().endswith(('.jpg', '.jpeg')):
                # Read EXIF data from JPEG
                exif_data = img.getexif() if hasattr(img, 'getexif') else None
                if exif_data:
                    metadata['description'] = exif_data.get(0x9286, '')  # UserComment
                    metadata['title'] = exif_data.get(0x010e, '')  # ImageDescription
                    metadata['date'] = exif_data.get(0x9003, '')  # DateTimeOriginal
            
            elif image_path.lower().endswith('.png'):
                # Read metadata from PNG
                if 'Title' in img.info:
                    metadata['title'] = img.info['Title']
                if 'Description' in img.info:
                    metadata['description'] = img.info['Description']
                if 'Date' in img.info:
                    metadata['date'] = img.info['Date']
            
            img.close()
            return metadata
        except Exception as e:
            print(f"Error reading metadata from image: {e}")
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
    
    def get_current_wallpaper(self):
        """Get the path of the current wallpaper"""
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop")
            wallpaper_path = winreg.QueryValueEx(key, "WallPaper")[0]
            winreg.CloseKey(key)
            return wallpaper_path
        except Exception as e:
            print(f"Error getting current wallpaper: {e}")
            return None
    
    def update_wallpaper(self):
        """Main function to update the wallpaper"""
        try:
            image_info = self.get_latest_image_info()
            if not image_info or 'url' not in image_info:
                return False, None
            
            # Store the image info
            self.current_image_url = image_info['url']
            self.current_description = image_info.get('description', 'No description available')
            self.current_title = image_info.get('title', 'NASA APOD')
            
            # Download and set the image
            image_path = self.download_image(image_info['url'], image_info)
            if image_path:
                success = self.set_wallpaper(image_path)
                return success, image_path
            
            return False, None
        except Exception as e:
            print(f"Error updating wallpaper: {e}")
            traceback.print_exc()
            return False, None
    
    def is_new_image_available(self):
        """Check if a new image is available compared to what we have"""
        try:
            # Get the latest image info
            image_info = self.get_latest_image_info()
            if not image_info or 'url' not in image_info:
                return False
            
            # Extract filename from URL
            latest_filename = image_info['url'].split('/')[-1]
            
            # Check if we already have this image
            current_wallpaper = self.get_current_wallpaper()
            if current_wallpaper:
                current_filename = os.path.basename(current_wallpaper)
                
                # If the current wallpaper is from our app and has the same filename, it's not new
                if current_filename == latest_filename and os.path.dirname(current_wallpaper) == self.download_dir:
                    return False
            
            # Also check if we have a record of the last downloaded image
            last_image_file = os.path.join(self.download_dir, "last_image.txt")
            if os.path.exists(last_image_file):
                with open(last_image_file, 'r') as f:
                    last_image_url = f.read().strip()
                    if last_image_url == image_info['url']:
                        return False
            
            # If we got here, a new image is available
            return True
        except Exception as e:
            print(f"Error checking for new image: {e}")
            return False


class DescriptionDialog(QDialog):
    def __init__(self, title, description, parent=None):
        super().__init__(parent)
        self.setWindowTitle(title or "Image Description")
        self.resize(600, 400)
        
        layout = QVBoxLayout()
        
        # Description text browser
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setHtml(f"<h2>{title}</h2><p>{description}</p>")
        layout.addWidget(self.text_browser)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        layout.addWidget(close_button)
        
        self.setLayout(layout)


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
            # Create a proper icon from the file
            icon = QtGui.QIcon()
            icon.addFile(icon_path, QtCore.QSize(16, 16))
            icon.addFile(icon_path, QtCore.QSize(24, 24))
            icon.addFile(icon_path, QtCore.QSize(32, 32))
            icon.addFile(icon_path, QtCore.QSize(48, 48))
            self.tray.setIcon(icon)
            # Also set as window icon
            self.setWindowIcon(icon)
        else:
            # Fallback to a simple icon
            self.tray.setIcon(QtGui.QIcon(QtGui.QPixmap(16, 16)))
        
        self.tray.setVisible(True)
        
        # Create menu with fixed width
        self.menu = QMenu()
        self.menu.setFixedWidth(300)  # Set a fixed width for the menu
        
        # Add actions
        self.update_action = QAction("Update Wallpaper Now")
        self.update_action.triggered.connect(self.manual_update)
        self.menu.addAction(self.update_action)
        
        # Add description preview with "View Full Description" option
        self.description_preview = QAction("Loading description...")
        self.description_preview.setEnabled(False)
        self.menu.addAction(self.description_preview)
        
        self.view_full_description = QAction("View Full Description")
        self.view_full_description.triggered.connect(self.show_full_description)
        self.menu.addAction(self.view_full_description)
        
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
        
        # Initial check - always check for new image on startup
        QtCore.QTimer.singleShot(1000, self.initial_check)
    
    def initial_check(self):
        """Check if we need to update on startup - always check for new image"""
        if self.wallpaper.is_new_image_available():
            self.check_for_update(show_notification=True)
        else:
            # Load the current description if available
            self.load_current_description()
    
    def load_current_description(self):
        """Load the current description from the current wallpaper or file"""
        try:
            # First try to get the current wallpaper path
            current_wallpaper = self.wallpaper.get_current_wallpaper()
            if current_wallpaper and os.path.exists(current_wallpaper):
                # Try to read metadata from the image
                metadata = self.wallpaper.read_metadata_from_image(current_wallpaper)
                if metadata and 'description' in metadata and metadata['description']:
                    self.wallpaper.current_description = metadata['description']
                    self.wallpaper.current_title = metadata.get('title', 'NASA APOD')
                    self.update_description_preview()
                    return
            
            # If we couldn't get metadata from the image, try the latest text file
            files = [f for f in os.listdir(self.wallpaper.download_dir) if f.startswith('apod_') and f.endswith('.txt')]
            if files:
                # Sort by date (which is in the filename)
                files.sort(reverse=True)
                latest_file = os.path.join(self.wallpaper.download_dir, files[0])
                
                with open(latest_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    title_match = re.search(r'Title: (.*?)\n', content)
                    desc_match = re.search(r'Description: (.*?)(?:\n\n|$)', content, re.DOTALL)
                    
                    if title_match:
                        self.wallpaper.current_title = title_match.group(1)
                    if desc_match:
                        self.wallpaper.current_description = desc_match.group(1)
                    
                    self.update_description_preview()
                    return
            
            # If all else fails, fetch from the website
            self.fetch_description()
        except Exception as e:
            print(f"Error loading description: {e}")
            traceback.print_exc()
    
    def get_preview_text(self, text, max_words=30):
        """Get a preview of the text with a maximum number of words"""
        if not text:
            return "No description available"
        
        words = text.split()
        if len(words) <= max_words:
            return text
        
        return " ".join(words[:max_words]) + "..."
    
    def update_description_preview(self):
        """Update the description preview in the menu"""
        if self.wallpaper.current_description:
            # Get a preview of the description (first 30 words)
            preview = self.get_preview_text(self.wallpaper.current_description)
            
            # Set the description in the menu
            self.description_preview.setText(preview)
            self.description_preview.setEnabled(False)  # Disable to prevent clicking
            self.view_full_description.setEnabled(True)
        else:
            self.description_preview.setText("No description available")
            self.description_preview.setEnabled(False)
            self.view_full_description.setEnabled(False)
    
    def show_full_description(self):
        """Show the full description in a dialog"""
        if self.wallpaper.current_description:
            dialog = DescriptionDialog(
                self.wallpaper.current_title, 
                self.wallpaper.current_description
            )
            dialog.exec_()
    
    def fetch_description(self):
        """Fetch the description from the website"""
        try:
            image_info = self.wallpaper.get_latest_image_info()
            if image_info:
                self.wallpaper.current_title = image_info.get('title', 'NASA APOD')
                self.wallpaper.current_description = image_info.get('description', 'No description available')
                self.update_description_preview()
                
                # Save description to file
                self.wallpaper.save_metadata_to_file(image_info)
        except Exception as e:
            print(f"Error fetching description: {e}")
            traceback.print_exc()
    
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
        if self.is_update_time() or self.wallpaper.is_new_image_available():
            self.check_for_update()
    
    def check_for_update(self, show_notification=True):
        """Check if we need to update the wallpaper"""
        try:
            success, image_path = self.wallpaper.update_wallpaper()
            if success:
                if show_notification:
                    self.tray.showMessage("APOD Wallpaper", "Wallpaper updated successfully!", QSystemTrayIcon.Information, 3000)
                
                # Update description in menu
                self.update_description_preview()
                
                # Save the current image URL
                last_image_file = os.path.join(self.wallpaper.download_dir, "last_image.txt")
                with open(last_image_file, 'w') as f:
                    f.write(self.wallpaper.current_image_url)
                
                # Update last update time
                last_update_file = os.path.join(self.wallpaper.download_dir, "last_update.txt")
                with open(last_update_file, 'w') as f:
                    f.write(datetime.datetime.now().strftime("%Y-%m-%d"))
            elif show_notification:
                self.tray.showMessage("APOD Wallpaper", "Failed to update wallpaper.", QSystemTrayIcon.Critical, 3000)
        except Exception as e:
            if show_notification:
                self.tray.showMessage("APOD Wallpaper", f"Error updating wallpaper: {str(e)}", QSystemTrayIcon.Critical, 3000)
    
    def manual_update(self):
        """Manually update the wallpaper"""
        try:
            success, image_path = self.wallpaper.update_wallpaper()
            if success:
                self.tray.showMessage("APOD Wallpaper", "Wallpaper updated successfully!", QSystemTrayIcon.Information, 3000)
                
                # Update description in menu
                self.update_description_preview()
                
                # Save the current image URL
                last_image_file = os.path.join(self.wallpaper.download_dir, "last_image.txt")
                with open(last_image_file, 'w') as f:
                    f.write(self.wallpaper.current_image_url)
                
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