import sys
import os
from cx_Freeze import setup, Executable

# Dependencies are automatically detected, but it might need fine tuning.
build_exe_options = {
    "packages": ["os", "sys", "ctypes", "requests", "bs4", "PyQt5", "PIL", "urllib3", "chardet", "datetime", "traceback"],
    "excludes": ["PyQt5.QtQml", "PyQt5.QtQuick", "pytest", "html5lib", "lxml"],
    "include_files": ["image-face.ico"],
    "include_msvcr": True,
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
            "apod_wallpaper.py", 
            base=base,
            icon="image-face.ico",  # Using .ico file instead of .png
            shortcut_name="wall-y",
            shortcut_dir="DesktopFolder",
            target_name="wall_y.exe"
        )
    ]
)