"""
Simple OmniParser Server

This is a simplified version of the OmniParser server that provides basic screen analysis.
It can be used when the full ML-based version is not available.
"""

import os
import uvicorn
import base64
import time
import io
import json
import logging
from typing import List, Dict, Any, Tuple
import traceback
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image, ImageDraw, ImageEnhance, ImageFilter

# Try to import OCR libraries - use if available but continue without them
try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    print("Tesseract OCR available - will use for text detection")
except ImportError:
    TESSERACT_AVAILABLE = False
    print("Tesseract OCR not available - will use basic region analysis only")

app = FastAPI(title="Simple OmniParser API")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("simple_omniparser")

# Output directory for debug images
OUTPUT_DIR = "tmp/outputs"
os.makedirs(OUTPUT_DIR, exist_ok=True)

class ParseRequest(BaseModel):
    base64_image: str

def detect_ui_elements(image: Image.Image) -> Tuple[List[Dict[str, Any]], Image.Image]:
    """
    Simple UI element detection based on edge detection and contrast
    """
    # Create a copy to draw on
    width, height = image.size
    som_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(som_image)
    
    # Get grayscale for processing
    gray = image.convert("L")
    
    # Enhance contrast to make elements stand out
    enhanced = ImageEnhance.Contrast(gray).enhance(2.0)
    
    # Apply edge detection
    edges = enhanced.filter(ImageFilter.FIND_EDGES)
    
    # List to store detected elements
    ui_elements = []
    
    # Use OCR if available
    text_regions = []
    if TESSERACT_AVAILABLE:
        try:
            # Get text regions
            ocr_data = pytesseract.image_to_data(image, output_type=pytesseract.Output.DICT)
            
            for i in range(len(ocr_data['text'])):
                # Filter out empty results
                if int(ocr_data['conf'][i]) > 20 and ocr_data['text'][i].strip():
                    x = ocr_data['left'][i]
                    y = ocr_data['top'][i]
                    w = ocr_data['width'][i]
                    h = ocr_data['height'][i]
                    text = ocr_data['text'][i]
                    
                    # Add to our UI elements list
                    normalized_coords = [x/width, y/height, (x+w)/width, (y+h)/height]
                    ui_elements.append({
                        "type": "text",
                        "content": text,
                        "bbox": normalized_coords,
                        "x": x,
                        "y": y,
                        "width": w,
                        "height": h
                    })
                    
                    # Draw rectangle
                    color = (0, 255, 0, 128)  # Green for text
                    draw.rectangle([x, y, x+w, y+h], outline=color, width=2)
                    
                    # Add text above the box
                    draw.text((x, y-15), text[:20], fill=(0, 0, 255, 255))
                    
                    text_regions.append((x, y, x+w, y+h))
        except Exception as e:
            logger.error(f"OCR error: {e}")
            logger.error(traceback.format_exc())
    
    # Simple region detection for buttons and UI elements
    # This is very basic and just creates regions that might be UI elements
    try:
        # Convert back to RGB for analysis
        edges_rgb = edges.convert("RGB")
        pixels = edges_rgb.load()
        
        # Simple approach: scan for horizontal lines that might be UI elements
        # Skip areas already identified by OCR
        y_step = height // 40  # Skip pixels for performance
        x_step = width // 40
        
        for y in range(0, height, y_step):
            in_element = False
            element_start = 0
            
            for x in range(0, width, x_step):
                # Check if this point is in any text region
                in_text_region = False
                for tx, ty, tx2, ty2 in text_regions:
                    if tx <= x <= tx2 and ty <= y <= ty2:
                        in_text_region = True
                        break
                
                if in_text_region:
                    continue
                
                # Get pixel brightness
                r, g, b = pixels[x, y]
                brightness = (r + g + b) / 3
                
                if brightness > 100 and not in_element:
                    # Start of potential UI element
                    in_element = True
                    element_start = x
                elif (brightness <= 100 or x == width-x_step) and in_element:
                    # End of potential UI element
                    element_width = x - element_start
                    if element_width > width / 20:  # Min width threshold
                        # This could be a button or input field
                        element_height = height // 20
                        element_y = max(0, y - element_height // 2)
                        
                        # Add to UI elements
                        normalized_coords = [
                            element_start/width, 
                            element_y/height, 
                            x/width, 
                            (element_y+element_height)/height
                        ]
                        ui_elements.append({
                            "type": "button",
                            "content": f"UI Element at {element_start},{element_y}",
                            "bbox": normalized_coords,
                            "x": element_start,
                            "y": element_y,
                            "width": element_width,
                            "height": element_height
                        })
                        
                        # Draw rectangle
                        color = (255, 0, 0, 128)  # Red for buttons
                        draw.rectangle(
                            [element_start, element_y, x, element_y+element_height], 
                            outline=color, width=2
                        )
                    
                    in_element = False
    
    except Exception as e:
        logger.error(f"Region detection error: {e}")
        logger.error(traceback.format_exc())
    
    # Add ID numbers to each element
    for i, element in enumerate(ui_elements):
        element["id"] = i
        # Add ID text to the image
        draw.text(
            (element["x"], element["y"]), 
            f"ID: {i}", 
            fill=(255, 255, 255, 255)
        )
    
    return ui_elements, som_image

@app.post("/parse/")
async def parse(parse_request: ParseRequest):
    """
    Parse the screenshot and return UI analysis
    """
    try:
        start_time = time.time()
        logger.info("Parse request received")
        
        # Decode the incoming image
        image_data = base64.b64decode(parse_request.base64_image)
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size
        logger.info(f"Image size: {width}x{height}")
        
        # Detect UI elements
        ui_elements, som_image = detect_ui_elements(image)
        
        # Convert SOM image back to base64
        som_buffer = io.BytesIO()
        som_image.save(som_buffer, format="PNG")
        som_image_base64 = base64.b64encode(som_buffer.getvalue()).decode('utf-8')
        
        # Create screen_info string - formatted nicely for display
        screen_info = "\n".join([
            f"ID: {elem['id']}, Type: {elem['type']}, Text: {elem['content']}" 
            for elem in ui_elements
        ])
        
        # Calculate processing time
        latency = time.time() - start_time
        logger.info(f"Parsing completed in {latency:.2f}s. Found {len(ui_elements)} elements")
        
        # Return response in the format expected by the client
        return {
            "status": "success",
            "message": "Simple OmniParser Analysis",
            "latency": latency,
            "som_image_base64": som_image_base64,
            "parsed_content_list": ui_elements,
            "screen_info": screen_info
        }
    except Exception as e:
        logger.error(f"Parse error: {str(e)}")
        logger.error(traceback.format_exc())
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/probe/")
async def root():
    """
    Simple probe endpoint for health check
    """
    logger.info("Probe request received")
    return {"status": "success", "message": "Simple OmniParser server is running"}

if __name__ == "__main__":
    print("Starting Simple OmniParser server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 