@echo off
echo Installing required packages...
pip install -r requirements.txt

echo Building executable...
python setup.py build

echo Done!
echo Executable should be in the 'build\dist' directory.

pause