import os
import sys
import time
import traceback
import psutil
import gc
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import uvicorn
import torch
import numpy as np
from PIL import Image
from typing import Dict

# Set environment variables and PyTorch settings
os.environ["OMNIPARSER_DEVICE"] = "mps"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"
os.environ["MPS_ENABLE_SHARED_MEM"] = "1"
os.environ["PYTORCH_MPS_HIGH_WATERMARK_RATIO"] = "0.7"  # Limit MPS memory usage
os.environ["PYTORCH_MPS_LOW_WATERMARK_RATIO"] = "0.5"   # Aggressive memory cleanup

# Configure PyTorch settings
torch.set_default_dtype(torch.float32)
if hasattr(torch.mps, 'set_per_process_memory_fraction'):
    torch.mps.set_per_process_memory_fraction(0.7)  # Reduced from 0.8 to 0.7

# Configure path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

# Configure logging with extended debug info
import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/omniparser_debug.log')
    ]
)
logger = logging.getLogger("omniparser_debug")

# Enhanced memory management with better error handling
class MemoryManager:
    def __init__(self):
        self.last_cleanup = time.time()
        self.cleanup_interval = 15  # Reduced from 30 to 15 seconds
        self.memory_threshold = 1024 * 1024 * 512  # Reduced to 512MB
        self.peak_memory = 0
        self.device = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
        logger.info(f"MemoryManager initialized with device: {self.device}")
        
    async def check_and_cleanup(self, force=False):
        try:
            current_time = time.time()
            current_memory = psutil.Process(os.getpid()).memory_info().rss
            
            # Update peak memory
            self.peak_memory = max(self.peak_memory, current_memory)
            
            # Log memory stats
            if force or current_memory > self.memory_threshold:
                logger.info(f"Memory usage: {current_memory / (1024*1024):.2f}MB")
                logger.info(f"Peak memory: {self.peak_memory / (1024*1024):.2f}MB")
            
            if (force or 
                current_memory > self.memory_threshold or 
                current_time - self.last_cleanup > self.cleanup_interval):
                await run_in_threadpool(self.cleanup)
                
        except Exception as e:
            logger.error(f"Memory check failed: {str(e)}")
            logger.error(traceback.format_exc())
            
    def cleanup(self):
        try:
            logger.info("Starting memory cleanup...")
            gc.collect()
            
            if self.device == 'mps':
                if hasattr(torch.mps, 'empty_cache'):
                    torch.mps.empty_cache()
                if hasattr(torch.mps, 'synchronize'):
                    torch.mps.synchronize()
            elif self.device == 'cuda':
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
            
            self.last_cleanup = time.time()
            current_memory = psutil.Process(os.getpid()).memory_info().rss
            logger.info(f"Memory cleanup completed. Current usage: {current_memory / (1024*1024):.2f}MB")
            
        except Exception as e:
            logger.error(f"Memory cleanup failed: {str(e)}")
            logger.error(traceback.format_exc())

memory_manager = MemoryManager()

# Function to log memory usage
def log_memory_usage(label=""):
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / (1024 * 1024)
    logger.info(f"Memory usage {label}: {memory_mb:.2f} MB")
    return memory_mb

# Model warmup function
def warmup_models(omniparser):
    logger.info("Starting model warmup...")
    try:
        # Create dummy inputs for warmup
        # Generate random values between 0 and 1 for SOM model
        som_input = torch.rand(1, 3, 224, 224, dtype=torch.float32)
        som_input = som_input.to(device=omniparser.device)
        
        # Warmup SOM model
        if hasattr(omniparser, 'som_model'):
            with torch.inference_mode():
                logger.info("Warming up SOM model...")
                _ = omniparser.som_model(som_input)
                logger.info("SOM model warmup completed successfully")
        
        # Warmup caption model
        if hasattr(omniparser, 'caption_model_processor'):
            with torch.inference_mode():
                logger.info("Warming up caption model...")
                try:
                    model = omniparser.caption_model_processor['model']
                    processor = omniparser.caption_model_processor['processor']
                    
                    # Create a dummy PIL image
                    dummy_image = Image.fromarray(
                        (np.random.randint(0, 255, (64, 64, 3))).astype('uint8')
                    )
                    
                    # Process the image through the processor
                    inputs = processor(
                        images=[dummy_image],
                        text=["<CAPTION>"],
                        return_tensors="pt"
                    )
                    
                    # Move tensors to device and ensure correct types
                    # First move integer tensors, then float tensors
                    int_keys = ["input_ids", "attention_mask"]
                    for key in inputs:
                        if torch.is_tensor(inputs[key]):
                            if key in int_keys:
                                # First convert to CPU long, then move to device
                                inputs[key] = inputs[key].cpu().to(dtype=torch.long)
                                inputs[key] = inputs[key].to(device=omniparser.device)
                                logger.info(f"{key} tensor type: {inputs[key].dtype}, device: {inputs[key].device}")
                            else:
                                # Keep other tensors as float32
                                inputs[key] = inputs[key].to(dtype=torch.float32, device=omniparser.device)
                                logger.info(f"{key} tensor type: {inputs[key].dtype}, device: {inputs[key].device}")
                    
                    # Run the model with explicit type checking
                    logger.info("Running caption model generation...")
                    _ = model.generate(
                        input_ids=inputs["input_ids"],
                        pixel_values=inputs["pixel_values"],
                        max_new_tokens=20,
                        num_beams=1,
                        do_sample=False
                    )
                    logger.info("Caption model warmup completed successfully")
                except Exception as e:
                    logger.error(f"Caption model warmup failed: {str(e)}")
                    logger.error(traceback.format_exc())
                    raise
        
        logger.info("Model warmup completed successfully")
        return True
    except Exception as e:
        logger.error(f"Model warmup failed: {str(e)}")
        logger.error(traceback.format_exc())
        return False

# Print diagnostics
logger.info(f"Python version: {sys.version}")
logger.info(f"PyTorch version: {torch.__version__}")
logger.info(f"MPS available: {torch.backends.mps.is_available()}")
logger.info(f"Current directory: {os.getcwd()}")
log_memory_usage("at startup")

# Create FastAPI app with middleware
app = FastAPI(title="Debug OmniParser Server")

# Add timing middleware
@app.middleware("http")
async def add_timing_middleware(request: Request, call_next):
    # Start timer
    start_time = time.time()
    
    # Get request details
    method = request.method
    url = request.url.path
    client = request.client.host if request.client else "unknown"
    content_length = request.headers.get("content-length", "unknown")
    
    logger.info(f"Request received - Method: {method}, URL: {url}, Client: {client}, Size: {content_length}")
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate timing
        process_time = time.time() - start_time
        logger.info(f"Request completed in {process_time:.2f}s - Method: {method}, URL: {url}, Client: {client}")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        return response
    except Exception as e:
        logger.error(f"Request failed - Method: {method}, URL: {url}, Client: {client}")
        logger.error(traceback.format_exc())
        raise

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
    request_id: str = None  # Add request ID for tracking

# Initialize OmniParser with exception handling
from util.omniparser import Omniparser

class OptimizedOmniParser(Omniparser):
    def __init__(self, config: Dict):
        # Ensure device is set in config
        if 'device' not in config:
            config['device'] = 'mps' if torch.backends.mps.is_available() else 'cuda' if torch.cuda.is_available() else 'cpu'
            logger.info(f"Setting default device to: {config['device']}")
        
        # Call parent class initialization
        try:
            super().__init__(config)
            logger.info(f"Successfully initialized parent Omniparser with device: {self.device}")
            
            # Apply additional device-specific optimizations
            if self.device == 'mps':
                # MPS-specific optimizations
                if hasattr(torch.mps, 'empty_cache'):
                    torch.mps.empty_cache()
                if hasattr(torch.mps, 'synchronize'):
                    torch.mps.synchronize()
                logger.info("Applied MPS-specific optimizations")
            elif self.device == 'cuda':
                # CUDA-specific optimizations
                torch.cuda.empty_cache()
                torch.cuda.synchronize()
                logger.info("Applied CUDA-specific optimizations")
        except Exception as e:
            logger.error(f"Failed to initialize OptimizedOmniParser: {str(e)}")
            logger.error(traceback.format_exc())
            raise

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
        'BOX_TRESHOLD': 0.05,
        'batch_size': 16,  # Further reduced batch size for better memory management
        'use_compiled_models': False  # Disable compilation for MPS
    }
    
    # Initialize OmniParser with optimized settings
    logger.info("Starting OmniParser initialization...")
    start_time = time.time()
    try:
        omniparser = OptimizedOmniParser(config)
        init_time = time.time() - start_time
        logger.info(f"OmniParser initialized in {init_time:.2f} seconds")
        
        # Perform model warmup
        warmup_success = warmup_models(omniparser)
        if not warmup_success:
            logger.warning("Model warmup failed (non-critical)")
        
        # Initial cleanup after setup
        memory_manager.cleanup()
        
        # After initialization
        if hasattr(omniparser, 'som_model'):
            device = next(omniparser.som_model.parameters()).device
            logger.info(f"SOM model is running on device: {device}")
        
        if hasattr(omniparser, 'caption_model_processor'):
            try:
                device = next(omniparser.caption_model_processor['model'].parameters()).device
                logger.info(f"Caption model is running on device: {device}")
            except:
                logger.info("Could not determine caption model device")
        
        log_memory_usage("after initialization")
    except Exception as e:
        logger.error(f"OmniParser initialization failed: {str(e)}")
        logger.error(f"Traceback:\n{traceback.format_exc()}")
        raise
except Exception as e:
    logger.error(f"OmniParser initialization failed: {str(e)}")
    logger.error(traceback.format_exc())
    omniparser = None

# Define API endpoints
@app.post("/parse/")
async def parse(parse_request: ParseRequest):
    request_id = parse_request.request_id or str(time.time())
    logger.info(f"Starting parse request {request_id}")
    
    try:
        # Check memory before processing
        memory_manager.check_and_cleanup()
        
        # Log request size
        image_size = len(parse_request.base64_image) / 1024  # KB
        logger.info(f"Request {request_id} - Image size: {image_size:.2f}KB")
        
        # Track memory before processing
        memory_before = log_memory_usage(f"before parsing request {request_id}")
        
        if omniparser is None:
            return {"error": "OmniParser was not properly initialized"}
        
        # Parse the image with detailed timing
        start_total = time.time()
        
        # Process image with inference mode to reduce memory usage
        with torch.inference_mode():
            dino_labled_img, parsed_content_list = omniparser.parse(parse_request.base64_image)
        
        # Calculate timings
        latency = time.time() - start_total
        logger.info(f"Request {request_id} - Processing completed in {latency:.2f}s")
        
        # Track memory after processing
        memory_after = log_memory_usage(f"after parsing request {request_id}")
        memory_increase = memory_after - memory_before
        
        # Force cleanup after processing
        memory_manager.check_and_cleanup(force=True)
        memory_after_gc = log_memory_usage(f"after GC for request {request_id}")
        memory_retained = memory_after_gc - memory_before
        
        logger.info(f"Request {request_id} - Memory stats:")
        logger.info(f"  Initial: {memory_before:.2f}MB")
        logger.info(f"  Peak: {memory_after:.2f}MB (+{memory_increase:.2f}MB)")
        logger.info(f"  After GC: {memory_after_gc:.2f}MB (retained: {memory_retained:.2f}MB)")
        
        return {
            "request_id": request_id,
            "som_image_base64": dino_labled_img, 
            "parsed_content_list": parsed_content_list,
            "latency": latency,
            "memory_usage_mb": memory_after,
            "memory_increase_mb": memory_increase,
            "memory_after_gc_mb": memory_after_gc,
            "status": "success"
        }
    except Exception as e:
        logger.error(f"Request {request_id} failed: {str(e)}")
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
    uvicorn.run("debug_server:app", host="0.0.0.0", port=8000, log_level="debug", workers=1) 