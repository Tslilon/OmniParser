import os
import sys
import time
import traceback
import psutil
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

# Function to log memory usage
def log_memory_usage(label=""):
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)
    logger.info(f"Memory usage {label}: {memory_mb:.2f} MB")
    return memory_mb

# Print diagnostics
logger.info(f"Python version: {sys.version}")
logger.info(f"PyTorch version: {torch.__version__}")
logger.info(f"MPS available: {torch.backends.mps.is_available()}")
logger.info(f"Current directory: {os.getcwd()}")
log_memory_usage("at startup")

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
    
    # After initialization
    if hasattr(omniparser, 'som_model'):
        device = next(omniparser.som_model.parameters()).device
        logger.info(f"SOM model is running on device: {device}")
    
    if hasattr(omniparser, 'caption_model'):
        try:
            device = next(omniparser.caption_model.parameters()).device
            logger.info(f"Caption model is running on device: {device}")
        except:
            logger.info("Could not determine caption model device")
    
    log_memory_usage("after initialization")
    
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
        memory_before = log_memory_usage("before parsing")
        
        if omniparser is None:
            return {"error": "OmniParser was not properly initialized"}
        
        # Parse the image with timing for each major step
        dino_labled_img, parsed_content_list = omniparser.parse(parse_request.base64_image)
        latency = time.time() - start
        memory_after = log_memory_usage("after parsing")
        memory_increase = memory_after - memory_before
        
        logger.info(f'Parsing completed in {latency:.2f} seconds')
        logger.info(f'Memory increased by {memory_increase:.2f} MB during parsing')
        
        # Track memory leak potential by forcing garbage collection and measuring again
        import gc
        gc.collect()
        torch.cuda.empty_cache() if torch.cuda.is_available() else None
        if hasattr(torch.mps, 'empty_cache'):
            torch.mps.empty_cache()
        memory_after_gc = log_memory_usage("after garbage collection")
        memory_retained = memory_after_gc - memory_before
        
        logger.info(f'Memory retained after GC: {memory_retained:.2f} MB (potential leak: {memory_retained > 10})')
        
        return {
            "som_image_base64": dino_labled_img, 
            "parsed_content_list": parsed_content_list,
            "latency": latency,
            "memory_usage_mb": memory_after,
            "memory_increase_mb": memory_increase,
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