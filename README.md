
# APOD Wallpaper

APOD Wallpaper is a simple Windows app that automatically downloads NASA's Astronomy Picture of the Day (APOD) and sets it as your desktop (and optionally lock screen) wallpaper. It runs in the system tray and can auto-start with Windows.

## Key Features
- Automatic daily wallpaper updates from NASA APOD
- System tray access: manual update, view description, open wallpapers folder, settings, exit
- Lock screen wallpaper support (optional)
- Auto-start with Windows

## Quick Start (For Users)
1. Download or build the app (see below for building instructions).
2. Run `build_app.bat` to build the executable (if not already built).
3. Deploy the app system-wide:
   - Right-click `deploy_windows.bat` and select **Run as administrator**
   - Or run from an elevated command prompt:
     ```
     deploy_windows.bat
     ```
4. Launch wall-y from the Start Menu, Desktop, or let it auto-start with Windows.

**To remove auto-start:** Delete the shortcut from `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.

## How to Use
- The app runs in the system tray. Right-click the tray icon for options:
  - Update wallpaper/lock screen manually
  - View full image description
  - Open wallpapers folder
  - Access settings (auto-start, lock screen)
  - Visit APOD website
  - Exit
- Images are saved in your `Pictures/wall-y` folder.

## Requirements (For Developers)
- Python 3.7+
- `pip install -r requirements.txt`
- To build: `pip install cx_Freeze` and run `python setup.py build`

## Notes
- The app checks for new wallpapers at NASA's update time (midnight ET)
- Lock screen updates use multiple methods for compatibility
- Image metadata (title, description, date) is saved with each image

---

