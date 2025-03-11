"""
Simple OmniParser Server

This is a simplified version of the OmniParser server that just responds to the /probe endpoint.
It can be used for debugging connection issues.
"""

import os
import uvicorn
import base64
import time
import io
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from PIL import Image, ImageDraw

app = FastAPI(title="Simple OmniParser API")

class ParseRequest(BaseModel):
    base64_image: str

@app.post("/parse/")
async def parse(parse_request: ParseRequest):
    """
    Simple parse endpoint that returns dummy data for testing
    """
    try:
        start_time = time.time()
        
        # Create a simple SOM (Spatial Object Memory) image
        # First, decode the incoming image
        image_data = base64.b64decode(parse_request.base64_image)
        image = Image.open(io.BytesIO(image_data))
        width, height = image.size
        
        # Create a blank image for the SOM overlay
        som_image = Image.new('RGBA', (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(som_image)
        
        # Draw some sample UI elements
        draw.rectangle([100, 100, 300, 150], outline=(255, 0, 0, 128), width=2)
        draw.rectangle([200, 200, 500, 250], outline=(0, 255, 0, 128), width=2)
        
        # Convert SOM image back to base64
        som_buffer = io.BytesIO()
        som_image.save(som_buffer, format="PNG")
        som_image_base64 = base64.b64encode(som_buffer.getvalue()).decode('utf-8')
        
        # Calculate processing time
        latency = time.time() - start_time
        
        # Return response in the format expected by the client
        return {
            "status": "success",
            "message": "Simple OmniParser (dummy mode)",
            "latency": latency,
            "som_image_base64": som_image_base64,
            "parsed_content_list": [
                {"type": "text", "content": "Example Button", "x": 100, "y": 100, "width": 200, "height": 50},
                {"type": "text", "content": "Example Text", "x": 200, "y": 200, "width": 300, "height": 50}
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/probe/")
async def root():
    """
    Simple probe endpoint for health check
    """
    return {"status": "success", "message": "Simple OmniParser server is running"}

if __name__ == "__main__":
    print("Starting Simple OmniParser server...")
    uvicorn.run(app, host="0.0.0.0", port=8000) 