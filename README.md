# APOD Wallpaper

A simple Windows application that automatically downloads NASA's Astronomy Picture of the Day (APOD) and sets it as your desktop wallpaper.

## Features

- Automatically downloads the latest APOD image at midnight ET (6:00 AM CEST)
- Sets the image as your desktop wallpaper and optionally as lock screen wallpaper
- Runs in the system tray for easy access
- Option to manually update wallpaper and lock screen
- View full image descriptions with a click
- Preview image descriptions in the system tray menu
- Open wallpapers folder directly from the app
- Auto-start with Windows option
- Robust error handling with multiple fallback methods
- Comprehensive logging for troubleshooting

## Installation

1. Install Python 3.7+ if not already installed
2. Install required packages:
   ```
   pip install -r requirements.txt
   ```
3. For building the executable:
   ```
   pip install cx_Freeze
   python setup.py build
   ```


## Deployment (Windows Executable)

After building the executable, you can deploy the app system-wide and enable auto-start with Windows:

1. Run the build script if you haven't already:
   ```
   build_app.bat
   ```
2. Deploy the application using the deployer script (as Administrator):
   - Right-click `deploy_windows.bat` and select **Run as administrator**
   - Or run from an elevated command prompt:
     ```
     deploy_windows.bat
     ```
   This will:
   - Copy the built files to `C:\Program Files\wall-y`
   - Create shortcuts on your Desktop and in the Start Menu (shortcut will point to `wall_y.exe`)
   - Add the app to Windows Startup so it launches automatically when you log in

You can now launch wall-y from the Start Menu, Desktop, or it will start automatically with Windows. If you need to run the executable directly, use `wall_y.exe`.

To remove auto-start, delete the shortcut from `%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup`.

---

## Usage

Run the application:
```
python apod_wallpaper.py
```

Or use the executable created by cx_Freeze.

The application will run in the system tray. Right-click the tray icon to:
- Update wallpaper and lock screen manually
- View full image descriptions
- Open the wallpapers folder
- Access settings (auto-start, lock screen options)
- Visit the APOD website
- Exit the application

## Notes

- The application checks for new wallpapers at midnight ET (NASA's update time)
- Images are saved in your Pictures folder under "wall-y"
- The application is set to download images at 1920x1080 resolution
- Lock screen updates use multiple methods to ensure compatibility across Windows versions
- Image metadata (title, description, date) is saved with the images
- Description previews are available directly in the system tray menu
