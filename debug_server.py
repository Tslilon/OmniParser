import os
import sys
import time
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import torch

# Set environment variables
os.environ["OMNIPARSER_DEVICE"] = "mps"

# Configure path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

# Configure logging with extended debug info
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("omniparser_debug")

# Print diagnostics
logger.info(f"Python version: {sys.version}")
logger.info(f"PyTorch version: {torch.__version__}")
logger.info(f"MPS available: {torch.backends.mps.is_available()}")
logger.info(f"Current directory: {os.getcwd()}")

# Create FastAPI app with middleware
app = FastAPI(title="Debug OmniParser Server")
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

try:
    # Find weights
    som_model_path = os.path.join(os.getcwd(), 'weights', 'icon_detect', 'model.pt')
    caption_model_path = os.path.join(os.getcwd(), 'weights', 'icon_caption_florence')
    
    # Check if files exist
    if not os.path.exists(som_model_path):
        logger.error(f"SOM model not found at {som_model_path}")
        raise FileNotFoundError(f"SOM model not found at {som_model_path}")
    else:
        logger.info(f"SOM model found at {som_model_path}")
        
    if not os.path.exists(caption_model_path):
        logger.error(f"Caption model not found at {caption_model_path}")
        raise FileNotFoundError(f"Caption model not found at {caption_model_path}")
    else:
        logger.info(f"Caption model found at {caption_model_path}")
    
    config = {
        'som_model_path': som_model_path,
        'caption_model_name': 'florence2',
        'caption_model_path': caption_model_path,
        'device': 'mps',
        'BOX_TRESHOLD': 0.05
    }
    
    # Initialize OmniParser with logging
    logger.info("Starting OmniParser initialization...")
    start_time = time.time()
    omniparser = Omniparser(config)
    logger.info(f"OmniParser initialized in {time.time() - start_time:.2f} seconds")
    
except Exception as e:
    logger.error(f"OmniParser initialization failed: {str(e)}")
    logger.error(traceback.format_exc())
    omniparser = None

# Add middleware for exception handling
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Middleware caught exception: {str(e)}")
        logger.error(traceback.format_exc())
        raise

# Define API endpoints
@app.post("/parse/")
async def parse(parse_request: ParseRequest):
    try:
        logger.info('Start parsing...')
        start = time.time()
        
        if omniparser is None:
            return {"error": "OmniParser was not properly initialized"}
        
        # Parse the image
        dino_labled_img, parsed_content_list = omniparser.parse(parse_request.base64_image)
        latency = time.time() - start
        logger.info(f'Parsing completed in {latency:.2f} seconds')
        
        return {
            "som_image_base64": dino_labled_img, 
            "parsed_content_list": parsed_content_list,
            "latency": latency,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Parse error: {str(e)}")
        logger.error(traceback.format_exc())
        return {"error": str(e), "traceback": traceback.format_exc(), "status": "error"}

@app.get("/probe")
@app.get("/probe/")
async def root():
    logger.info("Probe request received")
    return {"status": "success"}

# Run the server
if __name__ == "__main__":
    logger.info(f"Starting Debug OmniParser Server on port 8000...")
    uvicorn.run("debug_server:app", host="0.0.0.0", port=8000, log_level="debug") 