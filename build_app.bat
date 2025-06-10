@echo off
echo Installing required packages...
pip install -r requirements.txt

echo Building executable...
python setup.py build

echo Done!
if exist build\exe.win-amd64-3.13 (
    echo Executable created in build\exe.win-amd64-3.13
) else if exist build\exe.win32-3.13 (
    echo Executable created in build\exe.win32-3.13
) else (
    echo Check the build directory for your executable
)
pause