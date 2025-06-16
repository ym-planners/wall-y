import sys
import os
from cx_Freeze import setup, Executable



# Define the source and assets directories
SRC_DIR = "src"
ASSETS_DIR = "assets"
MAIN_SCRIPT = os.path.join(SRC_DIR, "apod_wallpaper.py")
ICON_FILE = os.path.join(ASSETS_DIR, "wall-y-round.ico")

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": [
        "os", "sys", "ctypes", "requests", "bs4", "PyQt5", "PIL", "urllib3", "chardet", "datetime", "traceback"
    ],
    "excludes": [
        "PyQt5.QtQml", "PyQt5.QtQuick", "pytest", "html5lib", "lxml", "tkinter"
    ],
    # Copy settings.py to the src folder in the build output
    "include_files": [
        (os.path.join(SRC_DIR, "settings.env"), os.path.join("src", "settings.env")),
        ICON_FILE
    ],
    "include_msvcr": True,
    "build_exe": "build/dist", # Output to build/dist/
    "zip_include_packages": ["*"],
    "zip_exclude_packages": [],
    "optimize": 2
}

# GUI applications require a different base on Windows
base = None
if sys.platform == "win32":
    base = "Win32GUI"

setup(
    name="WALL-Y",
    version="0.1",
    description="Wall-y -NASA APOD Wallpaper Changer",
    options={"build_exe": build_exe_options},
    executables=[
        Executable(
            MAIN_SCRIPT,
            base=base,
            icon=ICON_FILE,
            shortcut_name="wall-y",
            shortcut_dir="DesktopFolder",
            target_name="wall_y.exe"
        )
    ]
)