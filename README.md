# APOD Wallpaper

A simple Windows application that automatically downloads NASA's Astronomy Picture of the Day (APOD) and sets it as your desktop wallpaper.

## Features

- Automatically downloads the latest APOD image at midnight ET (6:00 AM CEST)
- Sets the image as your desktop wallpaper
- Runs in the system tray for easy access
- Option to manually update wallpaper
- Open wallpapers folder directly from the app
- Auto-start with Windows option
- Error handling for network issues and invalid images

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

## Usage

Run the application:
```
python apod_wallpaper.py
```

Or use the executable created by cx_Freeze.

The application will run in the system tray. Right-click the tray icon to:
- Update wallpaper manually
- Open the wallpapers folder
- Access settings (auto-start)
- Exit the application

## Notes

- The application checks for new wallpapers at midnight ET (NASA's update time)
- Images are saved in your Pictures folder under "wall-y"
- The application is set to download images at 1920x1080 resolution