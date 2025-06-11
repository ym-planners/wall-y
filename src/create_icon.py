from PIL import Image
import os

def create_png_icon():
    """Create a simple colored icon as PNG"""
    try:
        # Create a simple colored icon
        img = Image.new('RGBA', (64, 64), color=(0, 120, 212))  # Blue color
        
        # Save as PNG
        icon_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets/simple_icon.png")
        img.save(icon_path)
        print(f"Created simple icon at: {icon_path}")
        return icon_path
    except Exception as e:
        print(f"Error creating icon: {e}")
        return None

if __name__ == "__main__":
    create_png_icon()