import sys, os
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

def load_settings(env_path=None):
    settings = {}
    # Try to find settings.env in the right place depending on frozen/script mode
    possible_paths = []
    if env_path:
        possible_paths.append(env_path)
    if getattr(sys, 'frozen', False):
        # If frozen, look next to the executable (build output)
        exe_dir = os.path.dirname(sys.executable)
        possible_paths.append(os.path.join(exe_dir, "src", "settings.env"))
        possible_paths.append(os.path.join(exe_dir, "settings.env"))
    # Always try script dir (src/)
    possible_paths.append(os.path.join(os.path.dirname(__file__), "settings.env"))

    env_found = False
    for path in possible_paths:
        if os.path.exists(path):
            env_found = True
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        k, v = line.split('=', 1)
                        settings[k.strip()] = v.strip()
            break

    if not env_found:
        msg = ("ERROR: Could not find settings.env!\n" +
               "Searched paths:\n" +
               "\n".join(possible_paths) +
               "\nPlease ensure settings.env is present next to the executable or in the src/ folder.")
        print(msg)
        sys.exit(1)

    # Convert types
    settings["DEBUG_MODE"] = settings.get("DEBUG_MODE", "False") == "True"
    settings["ENABLE_WALLPAPER"] = settings.get("ENABLE_WALLPAPER", "True") == "True"
    settings["ENABLE_SCREENSAVER"] = settings.get("ENABLE_SCREENSAVER", "False") == "True"
    return settings

settings = load_settings()

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

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for cx_Freeze """
    if getattr(sys, 'frozen', False):
        # If the application is run as a bundle (e.g., by cx_Freeze),
        # base_path is the directory of the executable.
        base_path = os.path.dirname(sys.executable)
        print(f"Frozen mode: sys.executable dir: {base_path}")
        # In frozen mode, cx_Freeze copies files from 'include_files' to the root of the build_exe directory.
        # So, the icon will be alongside the executable, not in an 'assets' subfolder within the build.
    else:
        # If run in a normal Python environment
        # Go up one level from src to the project root, then to assets
        # __file__ is src/apod_wallpaper.py
        # os.path.dirname(__file__) is src/
        # os.path.dirname(os.path.dirname(__file__)) is project_root/
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        base_path = os.path.join(project_root, "assets") # Assuming icon is in project_root/assets
        print(f"Development mode: assets dir: {base_path}")
    resolved_path = os.path.join(base_path, relative_path.lstrip("assets/"))
    print(f"Resolved resource path for '{relative_path}': {resolved_path}")
    return resolved_path # Return the fully resolved path

class APODWallpaper:
    # [Rest of the APODWallpaper class remains unchanged]
    def __init__(self):
        # Use settings for URLs
        self.base_url = settings["APOD_BASE_URL"]
        self.archive_url = settings["APOD_ARCHIVE_URL"]
        self.today_url = settings["APOD_TODAY_URL"]

        # Set default download directory to wall-y under Pictures
        pictures_dir = os.path.join(os.path.expanduser("~"), "Pictures")
        self.download_dir = os.path.join(pictures_dir, "wall-y")
        # Create download directory if it doesn't exist
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)

        # Debug logging
        if settings["DEBUG_MODE"]:
            print("Debug mode enabled")
            print(f"Base URL: {self.base_url}")
            print(f"Download directory: {self.download_dir}")

        # Screensaver toggle
        self.enable_screensaver = settings["ENABLE_SCREENSAVER"]

        self.current_image_url = None
        self.current_description = None
        self.current_title = None
    
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

            # Get the description/explanation
            description = None
            explanation = None
            paragraphs = soup.find_all('p')
            for p in paragraphs:
                # Look for any tag or text containing 'Explanation:'
                if p.find(string=lambda s: s and 'Explanation:' in s):
                    # Get all text after 'Explanation:'
                    full_text = p.get_text(separator=' ', strip=True)
                    idx = full_text.find('Explanation:')
                    if idx != -1:
                        explanation = full_text[idx + len('Explanation:'):].strip()
                        break
            # Fallback: use the second paragraph as description if no explanation found
            if not explanation and len(paragraphs) >= 2:
                description = paragraphs[1].get_text(separator=' ', strip=True)
            else:
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
    
    def set_wallpaper(self, image_url):
        """Download the image if needed and set as wallpaper using the local file path."""
        import ctypes
        import requests
        import os
        if image_url.startswith("http"):
            local_path = os.path.join(self.download_dir, os.path.basename(image_url))
            try:
                response = requests.get(image_url, stream=True)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded wallpaper to: {local_path}")
                else:
                    print(f"Failed to download image: {response.status_code}")
                    return False
            except Exception as e:
                print(f"Error downloading wallpaper: {e}")
                return False
        else:
            local_path = image_url
        try:
            ctypes.windll.user32.SystemParametersInfoW(20, 0, local_path, 3)
            print(f"Wallpaper set successfully: {local_path}")
            return True
        except Exception as e:
            print(f"Error setting wallpaper: {e}")
            return False
    
    def set_screensaver_wallpaper(self, image_url):
        """Download the image if needed and prompt user to set as lock screen wallpaper manually."""
        import os
        import requests
        import subprocess
        from PyQt5.QtWidgets import QMessageBox
        if image_url.startswith("http"):
            local_path = os.path.join(self.download_dir, "lockscreen_wallpaper.jpg")
            try:
                response = requests.get(image_url, stream=True)
                if response.status_code == 200:
                    with open(local_path, 'wb') as f:
                        for chunk in response.iter_content(1024):
                            f.write(chunk)
                    print(f"Downloaded lock screen wallpaper to: {local_path}")
                else:
                    print(f"Failed to download image: {response.status_code}")
                    return False
            except Exception as e:
                print(f"Error downloading lock screen wallpaper: {e}")
                return False
        else:
            local_path = image_url
        # Open Windows lock screen settings
        try:
            subprocess.run(["start", "ms-settings:lockscreen"], shell=True)
            QMessageBox.information(None, "Lock Screen Wallpaper", f"Lock screen wallpaper downloaded to:\n{local_path}\n\nPlease set it manually in Windows Settings.")
            return True
        except Exception as e:
            print(f"Error opening lock screen settings: {e}")
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
            # Ensure current_image_url is set when fetching the latest image
            image_info = self.get_latest_image_info()
            if image_info and 'url' in image_info:
                self.current_image_url = image_info['url']
                print(f"Current image URL set: {self.current_image_url}")
            else:
                print("Failed to fetch the latest image info")

            # Apply wallpaper
            if settings["ENABLE_WALLPAPER"]:
                print("Applying wallpaper...")
                self.set_wallpaper(self.current_image_url)
            else:
                print("Wallpaper functionality disabled")
                
            return True, self.current_image_url
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
        self.resize(700, 500)

        layout = QVBoxLayout()

        # Title label (bold, larger font)
        title_label = QLabel(title or "")
        title_label.setWordWrap(True)
        title_label.setAlignment(QtCore.Qt.AlignCenter)
        title_label.setStyleSheet("font-size: 18pt; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)

        # Description text browser (scrollable, monospaced font for APOD style)
        self.text_browser = QTextBrowser()
        self.text_browser.setOpenExternalLinks(True)
        self.text_browser.setStyleSheet(
            "QTextBrowser { font-family: 'Segoe UI', 'Consolas', 'monospace'; font-size: 12pt; background: #fafafa; border: 1px solid #ccc; padding: 10px; }"
        )
        # Format description with line breaks for readability
        formatted_desc = description.replace('\n', '<br>')
        self.text_browser.setHtml(f"<div style='white-space:pre-wrap;'>{formatted_desc}</div>")
        layout.addWidget(self.text_browser, stretch=1)

        # Copyright label (bottom, smaller font)
        copyright_label = QLabel("Copyright © wall-y")
        copyright_label.setAlignment(QtCore.Qt.AlignRight)
        copyright_label.setStyleSheet("font-size: 9pt; color: #888; margin-top: 8px;")
        layout.addWidget(copyright_label)

        # Button row (horizontal)
        button_row = QtWidgets.QHBoxLayout()
        button_row.addStretch(1)
        close_button = QPushButton("Close")
        close_button.setFixedWidth(100)
        close_button.clicked.connect(self.accept)
        button_row.addWidget(close_button)
        layout.addLayout(button_row)

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
        
        # Screensaver toggle option
        self.screensaver_checkbox = QCheckBox("Enable Screensaver")
        self.screensaver_checkbox.setChecked(settings["ENABLE_SCREENSAVER"])
        layout.addWidget(self.screensaver_checkbox)

        # Wallpaper toggle option
        self.wallpaper_checkbox = QCheckBox("Enable Wallpaper")
        self.wallpaper_checkbox.setChecked(settings["ENABLE_WALLPAPER"])
        layout.addWidget(self.wallpaper_checkbox)

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

        # Update settings based on checkboxes
        settings["ENABLE_WALLPAPER"] = self.wallpaper_checkbox.isChecked()
        settings["ENABLE_SCREENSAVER"] = self.screensaver_checkbox.isChecked()

        self.accept()
    
    def add_to_startup(self):
        """Add the application to Windows startup"""
        import winreg as reg
        try:
            # Get the executable path
            if getattr(sys, 'frozen', False):
                # If running as exe (PyInstaller or cx_Freeze)
                file_path = sys.executable
            else:
                # If running as script
                file_path = os.path.abspath(sys.argv[0])
                
            print(f"Adding to startup: {file_path}")
            key = reg.OpenKey(reg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run", 0, reg.KEY_SET_VALUE)
            reg.SetValueEx(key, "APODWallpaper", 0, reg.REG_SZ, file_path)
            reg.CloseKey(key)
            return True
        except Exception as e:
            print(f"Error adding to startup: {e}")
            traceback.print_exc()
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
        self.tray = QSystemTrayIcon(self) # Pass parent
        
        # --- Robust Icon Loading ---
        icon_path = resource_path("assets/wall-y-round.ico")
        if os.path.exists(icon_path):
            print(f"Attempting to load icon from: {icon_path}")
            app_icon = QtGui.QIcon(icon_path) # Simpler way to load if path is correct
            
            if app_icon.isNull():
                print(f"Warning: Icon at {icon_path} loaded but isNull() returned True. File might be invalid or unreadable by Qt. Using fallback.")
                self._set_fallback_icon()
            else:
                self.tray.setIcon(app_icon)
                self.setWindowIcon(app_icon) 
        else:
            print(f"Icon file not found at {icon_path}, using fallback icon.")
            self._set_fallback_icon()
        # --- End Icon Loading ---

        self.tray.setVisible(True)
        
        # Create menu with better size (1/6th of screen width)
        self.menu = QMenu()
        screen_size = QtWidgets.QDesktopWidget().screenGeometry()
        menu_width = screen_size.width() // 6  # 1/6th of screen width
        self.menu.setFixedWidth(menu_width)
        
        # Add actions
        self.open_folder_action = QAction("Open Wallpapers Folder")
        self.open_folder_action.triggered.connect(self.open_wallpapers_folder)
        self.settings_action = QAction("Settings")
        self.settings_action.triggered.connect(self.show_settings)
        self.exit_action = QAction("Exit")
        self.exit_action.triggered.connect(self.quit)
        
        self.update_action = QAction("Update Wallpaper Now")
        self.update_action.triggered.connect(self.manual_update)
        self.menu.addAction(self.update_action)
        
        # --- QWidgetAction for Description Preview ---
        self.description_preview_label = QLabel("Loading description...")
        self.description_preview_label.setWordWrap(True)
        # Let the label expand horizontally and vertically to fit more text
        self.description_preview_label.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        self.description_preview_label.setMinimumWidth(int(menu_width * 0.95)) # Use about 95% of menu width
        self.description_preview_label.setMaximumWidth(int(menu_width * 0.98))
        self.description_preview_label.setMinimumHeight(300)  # Double the height for better readability
        self.description_preview_label.setMaximumHeight(350)  # Limit maximum height
        self.description_preview_label.setStyleSheet("QLabel { padding: 12px; font-size: 10pt; color: #333333; background-color: #ffffff; border: 1px solid #cccccc; border-radius: 8px; font-family: 'Segoe UI'; }") # Reduced font size and consistent font
        self.description_preview_label.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction | QtCore.Qt.TextSelectableByMouse)
        self.description_preview_label.mousePressEvent = lambda event: self.show_full_description()

        self.description_preview_action = QtWidgets.QWidgetAction(self.menu)
        self.description_preview_action.setDefaultWidget(self.description_preview_label)
        self.menu.addAction(self.description_preview_action)

        # Add a link to the APOD site
        self.apod_link_action = QAction("Visit APOD Website")
        self.apod_link_action.triggered.connect(lambda: QtGui.QDesktopServices.openUrl(QtCore.QUrl(self.wallpaper.base_url)))
        self.menu.addAction(self.apod_link_action)

        # Move buttons to the last rows
        self.menu.addSeparator()
        self.menu.addAction(self.open_folder_action)
        self.menu.addAction(self.settings_action)
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

    def _set_fallback_icon(self):
        """Sets a simple, programmatically generated fallback icon."""
        pixmap = QtGui.QPixmap(32, 32)
        pixmap.fill(QtGui.QColor("blue")) # A distinct blue color
        fallback_icon = QtGui.QIcon(pixmap)
        self.tray.setIcon(fallback_icon)
        self.setWindowIcon(fallback_icon)
        print("Fallback icon (blue square) has been set.")

    
    def initial_check(self):
        """Check for new images and update description on startup"""
        # Always fetch latest description first
        try:
            image_info = self.wallpaper.get_latest_image_info()
            if image_info:
                self.wallpaper.current_description = image_info.get('description', '')
                self.wallpaper.current_title = image_info.get('title', 'NASA APOD')
                self.update_description_preview()

                # Check if we need to update the wallpaper
                if self.wallpaper.is_new_image_available():
                    self.check_for_update(show_notification=True)
            else:
                # Fallback: try loading from local files
                self.load_current_description()
        except Exception as e:
            print(f"Error in initial check: {e}")
            traceback.print_exc()
            self.load_current_description()  # Fallback to local files
    
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
    
    def get_preview_text(self, text, max_words=200):
        """Get a preview of the text with a much larger number of words (or full text)"""
        if not text:
            return "No description available"
        words = text.split()
        if len(words) <= max_words:
            return text
        return " ".join(words[:max_words]) + "..."
    
    def update_description_preview(self):
        """Update the description preview in the menu"""
        if self.wallpaper.current_description:
            # Show a much longer preview (or full text)
            preview_text = self.get_preview_text(self.wallpaper.current_description, max_words=200)
            self.description_preview_label.setText(preview_text)
        else:
            self.description_preview_label.setText("No description available")

    
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
        # APOD updates daily, typically around midnight US Eastern Time.
        # Midnight ET is ~04:00-05:00 UTC depending on DST.
        # This check is a general window. is_new_image_available() is more definitive.
        now_utc = datetime.datetime.utcnow()
        # Check if current UTC hour is in a window that's likely post-midnight ET.
        # e.g., 4, 5, 6 UTC (covers midnight to 2 AM ET approx)
        return now_utc.hour in [4, 5, 6]
    
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