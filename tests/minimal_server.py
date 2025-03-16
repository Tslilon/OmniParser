import os
import sys
import time
import traceback
import torch
import gc
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Set environment variables
os.environ["OMNIPARSER_DEVICE"] = "mps"

# Configure path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

# Configure logging
import logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("minimal_omniparser")

# Import our device monitor
from tests.model_device_monitor import ModelDeviceMonitor
monitor = ModelDeviceMonitor()

# Create FastAPI app with middleware
app = FastAPI(title="Minimal OmniParser Server")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Define request model
class ParseRequest(BaseModel):
    base64_image: str

# Initialize OmniParser with exception handling
from util.omniparser import Omniparser

# Initialize OmniParser once at server startup
try:
    logger.info("Starting OmniParser initialization...")
    som_model_path = os.path.join(os.getcwd(), 'weights', 'icon_detect', 'model.pt')
    caption_model_path = os.path.join(os.getcwd(), 'weights', 'icon_caption_florence')
    
    config = {
        'som_model_path': som_model_path,
        'caption_model_name': 'florence2',
        'caption_model_path': caption_model_path,
        'device': 'mps',
        'BOX_TRESHOLD': 0.05
    }
    
    start_time = time.time()
    omniparser = Omniparser(config)
    logger.info(f"OmniParser initialized in {time.time() - start_time:.2f} seconds")
    
    # Use our monitor to check device placement
    device_info = monitor.log_model_devices(omniparser)
    logger.info(f"Model device info: {device_info}")
    
except Exception as e:
    logger.error(f"OmniParser initialization failed: {str(e)}")
    logger.error(traceback.format_exc())
    omniparser = None

# Track number of requests processed
request_count = 0

# Define API endpoints
@app.post("/parse/")
async def parse(parse_request: ParseRequest):
    global request_count
    request_count += 1
    
    try:
        logger.info(f'Start parsing request #{request_count}...')
        
        # Log model devices before processing
        logger.info("Logging model devices before processing")
        monitor.log_model_devices(omniparser)
        
        memory_before = monitor.log_memory_usage()
        logger.info(f"Memory before processing: {memory_before}")
        
        start = time.time()
        
        if omniparser is None:
            return {"error": "OmniParser was not properly initialized"}
        
        # Process the image
        with torch.inference_mode():
            dino_labled_img, parsed_content_list = omniparser.parse(parse_request.base64_image)
        
        latency = time.time() - start
        logger.info(f'Parsing completed in {latency:.2f} seconds')
        
        # Log model devices after processing
        logger.info("Logging model devices after processing")
        monitor.log_model_devices(omniparser)
        
        # Clean up memory explicitly
        logger.info("Forcing garbage collection")
        memory_after_processing = monitor.log_memory_usage()
        monitor.force_gc()
        memory_after_gc = monitor.log_memory_usage()
        
        # Print a summary every 5 requests
        if request_count % 5 == 0:
            monitor.print_summary()
        
        return {
            "som_image_base64": dino_labled_img, 
            "parsed_content_list": parsed_content_list,
            "latency": latency,
            "memory_before_mb": memory_before.get("system_memory_mb"),
            "memory_after_processing_mb": memory_after_processing.get("system_memory_mb"),
            "memory_after_gc_mb": memory_after_gc.get("system_memory_mb"),
            "request_count": request_count,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Parse error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "status": "error"}

@app.get("/stats")
async def stats():
    """Return current server statistics"""
    try:
        monitor.log_memory_usage()
        monitor.print_summary()
        
        # Get the latest device and memory info
        device_info = monitor.device_logs[-1] if monitor.device_logs else {}
        memory_info = monitor.memory_logs[-1] if monitor.memory_logs else {}
        
        return {
            "request_count": request_count,
            "device_info": device_info,
            "memory_info": memory_info,
            "status": "success"
        }
    except Exception as e:
        return {"error": str(e), "status": "error"}

@app.get("/probe")
@app.get("/probe/")
async def root():
    return {"status": "success"}

# Run the server
if __name__ == "__main__":
    logger.info(f"Starting Minimal OmniParser Server on port 8000...")
    uvicorn.run("minimal_server:app", host="0.0.0.0", port=8000, log_level="info") 