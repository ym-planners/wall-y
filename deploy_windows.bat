@echo off
REM Windows Deployer for wall-y
REM This script installs the built application to Program Files and sets up shortcuts

setlocal

REM Set variables
set APP_NAME=wall-y
set BUILD_DIR=%~dp0build\dist
set INSTALL_DIR="%ProgramFiles%\%APP_NAME%"
set SHORTCUT_NAME=wall-y.lnk
set DESKTOP_DIR="%USERPROFILE%\Desktop"
set STARTMENU_DIR="%APPDATA%\Microsoft\Windows\Start Menu\Programs"

REM Check if build exists
if not exist %BUILD_DIR% (
    echo Build directory not found! Please run build_app.bat first.
    pause
    exit /b 1
)

REM Create install directory
if not exist %INSTALL_DIR% mkdir %INSTALL_DIR%

REM Copy files
xcopy /E /Y %BUILD_DIR%\* %INSTALL_DIR%\

REM Create desktop shortcut (requires PowerShell)
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%DESKTOP_DIR%\%SHORTCUT_NAME%');$s.TargetPath='%INSTALL_DIR%\\wall_y.exe';$s.IconLocation='%INSTALL_DIR%\\wall-y-round.ico';$s.Save()"

REM Create Start Menu shortcut
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%STARTMENU_DIR%\%SHORTCUT_NAME%');$s.TargetPath='%INSTALL_DIR%\\wall_y.exe';$s.IconLocation='%INSTALL_DIR%\\wall-y-round.ico';$s.Save()"


REM Add to Windows Startup
powershell -Command "$s=(New-Object -COM WScript.Shell).CreateShortcut('%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\%SHORTCUT_NAME%');$s.TargetPath='%INSTALL_DIR%\\wall_y.exe';$s.IconLocation='%INSTALL_DIR%\\wall-y-round.ico';$s.Save()"

echo Deployment complete!
pause
endlocal
