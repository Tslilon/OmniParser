from pathlib import Path
from uuid import uuid4
import requests
from PIL import Image, ImageDraw, ImageFont
from .base import BaseAnthropicTool, ToolError
from io import BytesIO
import os
import time

OUTPUT_DIR = "./tmp/outputs"

def get_screenshot(resize: bool = False, target_width: int = 1920, target_height: int = 1080, windows_host_url: str = 'localhost:5001'):
    """Capture screenshot by requesting from HTTP endpoint - returns native resolution unless resized"""
    output_dir = Path(OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"screenshot_{uuid4().hex}.png"
    
    start_time = time.time()
    
    try:
        print(f"Attempting to capture screenshot from Windows VM at {windows_host_url}...")
        
        # Try to get screenshot from the API endpoint
        try:
            # Time the API request specifically
            api_start_time = time.time()
            response = requests.get(f'http://{windows_host_url}/screenshot', timeout=5)
            api_time = time.time() - api_start_time
            
            if response.status_code == 200:
                # Time image processing
                process_start_time = time.time()
                screenshot = Image.open(BytesIO(response.content))
                screenshot.save(path)
                process_time = time.time() - process_start_time
                
                total_time = time.time() - start_time
                print(f"⏱️ PERF: Screenshot API request: {api_time:.2f}s")
                print(f"⏱️ PERF: Screenshot processing: {process_time:.2f}s")
                print(f"⏱️ PERF: Screenshot total: {total_time:.2f}s")
                
                print(f"Screenshot captured successfully and saved to {path}")
                return screenshot, path
        except Exception as e:
            print(f"Error capturing screenshot via API: {e}")
            
        # If API fails, create a placeholder image
        print("Creating placeholder screenshot...")
        assets_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "assets")
        os.makedirs(assets_dir, exist_ok=True)
        
        # Create a simple placeholder image
        img = Image.new('RGB', (target_width, target_height), color=(240, 240, 240))
        draw = ImageDraw.Draw(img)
        
        # Add explanatory text
        try:
            # Try to use a standard font, if available
            font = ImageFont.truetype("Arial", 24)
        except IOError:
            font = ImageFont.load_default()
            
        text = f"Screenshot service unavailable.\n\nCheck VM connection at {windows_host_url}"
        draw.text((target_width//2, target_height//2), text, fill=(0, 0, 0), font=font, align="center", anchor="mm")
        
        img.save(path)
        total_time = time.time() - start_time
        print(f"⏱️ PERF: Placeholder creation: {total_time:.2f}s")
        print(f"Placeholder image created and saved to {path}")
        return img, path
        
    except Exception as e:
        total_time = time.time() - start_time
        print(f"⏱️ PERF: Failed screenshot attempt: {total_time:.2f}s")
        raise ToolError(f"Failed to capture screenshot: {str(e)}")