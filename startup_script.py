import os
import sys
import winreg as reg

def add_to_startup(file_path=""):
    """Add the application to Windows startup"""
    if not file_path:
        file_path = os.path.abspath(sys.argv[0])
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        # Open the registry key
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_SET_VALUE)
        
        # Set the value
        reg.SetValueEx(key, "APODWallpaper", 0, reg.REG_SZ, file_path)
        
        # Close the key
        reg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error adding to startup: {e}")
        return False

def remove_from_startup():
    """Remove the application from Windows startup"""
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    
    try:
        # Open the registry key
        key = reg.OpenKey(reg.HKEY_CURRENT_USER, key_path, 0, reg.KEY_SET_VALUE)
        
        # Delete the value
        reg.DeleteValue(key, "APODWallpaper")
        
        # Close the key
        reg.CloseKey(key)
        return True
    except Exception as e:
        print(f"Error removing from startup: {e}")
        return False

if __name__ == "__main__":
    # Example usage
    if len(sys.argv) > 1:
        if sys.argv[1] == "--add":
            add_to_startup()
            print("Added to startup")
        elif sys.argv[1] == "--remove":
            remove_from_startup()
            print("Removed from startup")
    else:
        print("Usage: python startup_script.py --add|--remove")