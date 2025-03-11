from pathlib import Path
from uuid import uuid4
import requests
from PIL import Image
from .base import BaseAnthropicTool, ToolError
from io import BytesIO

OUTPUT_DIR = "./tmp/outputs"

def get_screenshot(resize: bool = False, target_width: int = 1920, target_height: int = 1080, windows_host_url: str = 'localhost:5001'):
    """Capture screenshot by requesting from HTTP endpoint - returns native resolution unless resized"""
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"screenshot_{uuid4().hex}.png"
    
    try:
        print(f"Attempting to capture screenshot from Windows VM at {windows_host_url}...")
        response = requests.get(f'http://{windows_host_url}/screenshot')
        if response.status_code != 200:
            raise ToolError(f"Failed to capture screenshot: HTTP {response.status_code}")
        
        screenshot = Image.open(BytesIO(response.content))
        
        if resize and screenshot.size != (target_width, target_height):
            screenshot = screenshot.resize((target_width, target_height))
        screenshot.save(path)
        return screenshot, path
    except Exception as e:
        raise ToolError(f"Failed to capture screenshot: {str(e)}")