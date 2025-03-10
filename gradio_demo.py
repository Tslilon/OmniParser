from typing import Optional, Tuple
import gradio as gr
import numpy as np
import torch
from PIL import Image
import io
import os
import time
import traceback
import sys
import threading
import multiprocessing
from functools import partial

import base64, os
from util.utils import check_ocr_box, get_yolo_model, get_caption_model_processor, get_som_labeled_img
import torch
from PIL import Image

# Force immediate output flushing (no buffering)
print("Setting up stdout to flush immediately after each print...", flush=True)
sys.stdout.reconfigure(line_buffering=True)

# Configure PyTorch to handle the float/half precision issues on MPS
if hasattr(torch, 'set_default_dtype'):
    print("Setting default PyTorch dtype to float32 for consistency", flush=True)
    torch.set_default_dtype(torch.float32)

# Always use MPS (Metal Performance Shaders) by default if available on Mac
if torch.backends.mps.is_available():
    DEVICE = torch.device("mps")
    print(f"Using MPS acceleration on Mac: {DEVICE}", flush=True)
    
    # Configure MPS for mixed precision compatibility
    if hasattr(torch.backends.mps, 'enable_mixed_precision'):
        print("Enabling mixed precision for MPS", flush=True)
        torch.backends.mps.enable_mixed_precision = True
    
    # Verify MPS is working with a simple test
    print("Verifying MPS functionality with a test computation...", flush=True)
    try:
        # Create test tensors on MPS
        test_tensor1 = torch.randn(1000, 1000, device=DEVICE)
        test_tensor2 = torch.randn(1000, 1000, device=DEVICE)
        
        # Run a test computation
        start_time = time.time()
        result = torch.matmul(test_tensor1, test_tensor2)
        test_time = time.time() - start_time
        
        # Verify the result came from MPS
        print(f"✅ MPS test complete: Matrix multiplication took {test_time*1000:.2f}ms on {result.device}", flush=True)
        
        # Clean up test memory
        del test_tensor1, test_tensor2, result
        torch.mps.empty_cache()
    except Exception as e:
        print(f"⚠️ MPS test failed: {e}", flush=True)
        print("Falling back to CPU", flush=True)
        DEVICE = torch.device("cpu")
elif torch.cuda.is_available():
    DEVICE = torch.device('cuda')
    print(f"Using CUDA acceleration: {DEVICE}", flush=True)
else:
    DEVICE = torch.device('cpu')
    print(f"Using CPU: {DEVICE}", flush=True)

# Override device with environment variable if set
if os.environ.get("OMNIPARSER_DEVICE") == "cpu":
    DEVICE = torch.device("cpu")
    print(f"Overriding to CPU based on environment variable: {DEVICE}", flush=True)

# Configure pytorch to use consistent float types
print("Ensuring consistent tensor types for MPS compatibility", flush=True)
if DEVICE.type == 'mps':
    # This is necessary to avoid float/half precision mismatch errors
    torch.mps.set_per_process_memory_fraction(0.8)  # Allow using more GPU memory

# Load models in global scope to avoid reloading with each call
print("Loading models...", flush=True)
try:
    yolo_model = get_yolo_model(model_path='weights/icon_detect/model.pt')
    
    # Complete fix for the half-precision model issue
    print("Setting up caption model with correct precision handling...", flush=True)
    
    # First try to load with CPU to avoid precision issues, then transfer to MPS
    temp_cpu_device = torch.device("cpu")
    caption_model_processor = get_caption_model_processor(
        model_name="florence2", 
        model_name_or_path="weights/icon_caption_florence", 
        device=temp_cpu_device
    )
    
    # Examine the structure of caption_model_processor
    print(f"Caption processor type: {type(caption_model_processor)}", flush=True)
    if isinstance(caption_model_processor, dict):
        print(f"Caption processor keys: {list(caption_model_processor.keys())}", flush=True)
        
        # Now ensure all model parameters are converted to float32
        if DEVICE.type == 'mps' and 'model' in caption_model_processor:
            print("Converting model from CPU to MPS with float32 precision...", flush=True)
            
            # Get the model from the processor dictionary
            model = caption_model_processor['model']
            
            # Explicitly convert ALL model parameters to float32
            for param in model.parameters():
                param.data = param.data.to(dtype=torch.float32)
                
            # Transfer the model to MPS after conversion
            model = model.to(device=DEVICE)
            
            # Update the processor with the converted model
            caption_model_processor['model'] = model
            
            print(f"Model successfully converted to float32 and moved to {DEVICE}", flush=True)
    
    print("Models loaded successfully!", flush=True)
except Exception as e:
    print(f"Error loading models: {e}", flush=True)
    print(traceback.format_exc(), flush=True)
    yolo_model = None
    caption_model_processor = None

MARKDOWN = """
# OmniParser for Pure Vision Based General GUI Agent 🔥
<div>
    <a href="https://arxiv.org/pdf/2408.00203">
        <img src="https://img.shields.io/badge/arXiv-2408.00203-b31b1b.svg" alt="Arxiv" style="display:inline-block;">
    </a>
</div>

OmniParser is a screen parsing tool to convert general GUI screen to structured elements. 
"""

# Helper function to force tensor to MPS if available and handle type conversion
def to_device(tensor, dtype=torch.float32):
    """Helper to ensure tensors are on the correct device with consistent type"""
    if tensor is not None and hasattr(tensor, 'to'):
        # Always convert to float32 first to avoid mixed precision issues
        return tensor.to(device=DEVICE, dtype=dtype)
    return tensor

# Patched version of get_som_labeled_img that ensures consistent tensor types
def patched_get_som_labeled_img(*args, **kwargs):
    try:
        # Get the caption processor from kwargs for special handling
        caption_processor = kwargs.get('caption_model_processor', None)
        
        if caption_processor is not None and DEVICE.type == 'mps':
            if isinstance(caption_processor, dict) and 'model' in caption_processor:
                # Get the model and ensure it's using float32
                model = caption_processor['model']
                
                # Make sure model is in eval mode
                model.eval()
                
                # Verify model parameters are float32
                for name, param in model.named_parameters():
                    if param.dtype != torch.float32:
                        print(f"Converting parameter {name} from {param.dtype} to float32", flush=True)
                        param.data = param.data.to(dtype=torch.float32)
                
                # Update the processor in kwargs
                caption_processor['model'] = model
                kwargs['caption_model_processor'] = caption_processor
        
        # Process other tensor args consistently as float32
        new_args = []
        for arg in args:
            if torch.is_tensor(arg):
                new_args.append(to_device(arg, dtype=torch.float32))
            else:
                new_args.append(arg)
                
        # Call original function with type-consistent args
        print("Calling SOM labeled img with consistent tensor types", flush=True)
        result = get_som_labeled_img(*new_args, **kwargs)
        return result
    except Exception as e:
        print(f"Error in patched SOM: {e}", flush=True)
        # Just pass through to original function if our patch fails
        return get_som_labeled_img(*args, **kwargs)

# Function with timeout capability
def run_with_timeout(func, args=(), kwargs={}, timeout_duration=30):
    """Run a function with a timeout"""
    result = [None]
    exception = [None]
    
    def target():
        try:
            result[0] = func(*args, **kwargs)
        except Exception as e:
            exception[0] = e
    
    thread = threading.Thread(target=target)
    thread.daemon = True
    
    print(f"Starting function with {timeout_duration}s timeout", flush=True)
    thread.start()
    thread.join(timeout_duration)
    
    if thread.is_alive():
        print("Function timed out!", flush=True)
        return None, True  # None result, timed out = True
    
    if exception[0] is not None:
        print(f"Function raised exception: {exception[0]}", flush=True)
        raise exception[0]
    
    return result[0], False  # Return result, timed out = False

# Ensure OCR results have valid format
def ensure_valid_ocr_format(text, ocr_bbox, image_size):
    """Ensure OCR results are in a valid format"""
    if text is None:
        text = []
    if ocr_bbox is None:
        ocr_bbox = []
    
    # Debug OCR results
    print(f"Raw OCR results - text: {len(text)} items, bbox: {len(ocr_bbox)} items", flush=True)
    if len(text) > 0 and len(ocr_bbox) == 0:
        print("OCR returned text but no bounding boxes - creating empty boxes", flush=True)
        # Create empty bounding boxes for each text item
        w, h = image_size
        # Create minimal bounding boxes in the corner to avoid affecting detection
        ocr_bbox = [[0, 0, 1, 1] for _ in text]
        
    # Ensure both lists have the same length
    if len(text) != len(ocr_bbox):
        print(f"⚠️ Warning: OCR text and bbox have different lengths ({len(text)} vs {len(ocr_bbox)})", flush=True)
        # Use the shorter length
        min_len = min(len(text), len(ocr_bbox))
        text = text[:min_len]
        ocr_bbox = ocr_bbox[:min_len]
    
    # Verify each bbox is valid
    valid_text = []
    valid_bbox = []
    for i, (t, b) in enumerate(zip(text, ocr_bbox)):
        if b is not None and isinstance(b, (list, tuple)) and len(b) >= 4:
            valid_text.append(t)
            valid_bbox.append(b)
        else:
            print(f"⚠️ Skipping invalid bbox at index {i}: {b}", flush=True)
    
    print(f"OCR results: {len(valid_text)} valid items out of {len(text)} detected", flush=True)
    
    # If we still have no valid OCR data, create a dummy item to avoid errors
    # This is important because some downstream functions expect at least empty lists, not None
    if valid_text == [] or valid_bbox == []:
        print("Creating empty OCR data structures to avoid NoneType errors", flush=True)
        return [], []
        
    return valid_text, valid_bbox

# Add timeout handling for processing
def process_with_timeout(
    image_input,
    box_threshold,
    iou_threshold,
    use_paddleocr,
    imgsz,
    timeout=120  # 2 minute timeout
) -> Tuple[Optional[Image.Image], str]:
    """Wrapper with timeout and error handling"""
    
    if yolo_model is None or caption_model_processor is None:
        return None, "ERROR: Models failed to load. Please check console for details."
    
    try:
        start_time = time.time()
        
        # Create a status message for debugging
        status_msg = "Starting processing...\n"
        print("==== NEW PROCESSING REQUEST ====", flush=True)
        print("Starting image processing...", flush=True)
        
        # Save the image
        image_save_path = 'imgs/saved_image_demo.png'
        image_input.save(image_save_path)
        image = Image.open(image_save_path)
        print(f"Image saved and loaded. Size: {image.size}", flush=True)
        status_msg += f"Image saved and loaded. Size: {image.size}\n"
        
        # Optimize image size if it's too large
        if image.width > 1024 or image.height > 1024:
            print(f"Image is large, resizing for better performance", flush=True)
            ratio = min(1024/image.width, 1024/image.height)
            new_size = (int(image.width * ratio), int(image.height * ratio))
            image = image.resize(new_size, Image.LANCZOS)
            print(f"Resized to: {new_size}", flush=True)
            image.save(image_save_path)
        
        # Configure box overlay ratio
        box_overlay_ratio = image.size[0] / 3200
        draw_bbox_config = {
            'text_scale': 0.8 * box_overlay_ratio,
            'text_thickness': max(int(2 * box_overlay_ratio), 1),
            'text_padding': max(int(3 * box_overlay_ratio), 1),
            'thickness': max(int(3 * box_overlay_ratio), 1),
        }
        
        # Display current device and memory usage
        if DEVICE.type == 'mps':
            print(f"Current device: {DEVICE}", flush=True)
        
        # Process OCR with timeout
        print("Running OCR...", flush=True)
        status_msg += "Running OCR...\n"
        ocr_start = time.time()
        
        # OCR can hang, so we add a specific timeout just for this step
        ocr_timeout = 30  # 30 seconds timeout for OCR
        if use_paddleocr:
            print(f"Using PaddleOCR (can be slow, timeout: {ocr_timeout}s)", flush=True)
            print("PaddleOCR debug: Importing PaddleOCR class...", flush=True)
            try:
                from paddleocr import PaddleOCR
                print("PaddleOCR debug: Import successful", flush=True)
                
                # Check if we should use GPU (MPS) for PaddleOCR
                use_gpu = os.environ.get('OMNIPARSER_DEVICE', '').lower() == 'mps'
                if use_gpu:
                    print(f"PaddleOCR will attempt to use GPU: {use_gpu}", flush=True)
                
                # Test PaddleOCR initialization
                print("PaddleOCR debug: Testing initialization...", flush=True)
                test_ocr = PaddleOCR(lang='en', use_angle_cls=False, use_gpu=use_gpu, show_log=True)
                print("PaddleOCR debug: Initialization successful", flush=True)
            except Exception as e:
                print(f"PaddleOCR debug: Error during import/init: {e}", flush=True)
                print(traceback.format_exc(), flush=True)
                print("Falling back to EasyOCR due to PaddleOCR error", flush=True)
                use_paddleocr = False
        else:
            print("Using EasyOCR", flush=True)
        
        # Define a direct OCR function to handle potential errors
        def safe_ocr():
            try:
                result = check_ocr_box(
                    image_save_path, 
                    display_img=False, 
                    output_bb_format='xyxy', 
                    goal_filtering=None, 
                    easyocr_args={'paragraph': False, 'text_threshold':0.9}, 
                    use_paddleocr=use_paddleocr
                )
                return result
            except Exception as e:
                print(f"OCR error: {e}", flush=True)
                return ([], [])  # Return empty lists on error
        
        ocr_result, ocr_timed_out = run_with_timeout(safe_ocr, timeout_duration=ocr_timeout)
        
        if ocr_timed_out:
            print(f"⚠️ OCR timed out after {ocr_timeout}s, proceeding with empty OCR results", flush=True)
            # Create empty results to allow processing to continue
            text, ocr_bbox = [], []
            status_msg += f"OCR timed out after {ocr_timeout}s\n"
        else:
            ocr_time = time.time() - ocr_start
            if ocr_result is None or len(ocr_result) != 2:
                print(f"⚠️ OCR returned unexpected format: {ocr_result}", flush=True)
                text, ocr_bbox = [], []
            else:
                text, ocr_bbox = ocr_result
            
            print(f"OCR completed in {ocr_time:.2f}s, found {len(text)} text regions", flush=True)
            status_msg += f"OCR completed in {ocr_time:.2f}s\n"
        
        # Ensure OCR results are in a valid format
        text, ocr_bbox = ensure_valid_ocr_format(text, ocr_bbox, image.size)
        
        # Check if we're running out of time
        if (time.time() - start_time) > timeout:
            print(f"Process timed out after {timeout}s", flush=True)
            return None, f"Processing timed out after {timeout} seconds. Progress: {status_msg}"
        
        # Run SOM labeling
        print("Running icon detection and labeling...", flush=True)
        status_msg += "Running icon detection and labeling...\n"
        som_start = time.time()
        
        try:
            # Special handling for empty OCR results
            if len(ocr_bbox) == 0:
                print("⚠️ No valid OCR bounding boxes - running simplified detection", flush=True)
                # Force empty lists instead of None to avoid errors
                text = []
                ocr_bbox = []
                
            # Use our patched version that handles type consistency
            print("Using patched SOM function to ensure type consistency", flush=True)
            dino_labled_img, label_coordinates, parsed_content_list = patched_get_som_labeled_img(
                image_save_path, 
                yolo_model, 
                BOX_TRESHOLD=box_threshold, 
                output_coord_in_ratio=True, 
                ocr_bbox=ocr_bbox,
                draw_bbox_config=draw_bbox_config, 
                caption_model_processor=caption_model_processor, 
                ocr_text=text,
                iou_threshold=iou_threshold, 
                imgsz=imgsz,
            )
            som_time = time.time() - som_start
            print(f"Icon detection completed in {som_time:.2f}s", flush=True)
            status_msg += f"Icon detection completed in {som_time:.2f}s\n"
            
            # Create final image
            print("Creating final output image...", flush=True)
            image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
            
            # Format results
            parsed_content_list = '\n'.join([f'icon {i}: ' + str(v) for i,v in enumerate(parsed_content_list)])
        except Exception as e:
            print(f"Error in icon detection: {e}", flush=True)
            print(traceback.format_exc(), flush=True)
            
            # Try to fall back to CPU as a last resort
            print("Attempting fallback to CPU for icon detection...", flush=True)
            try:
                # Create a temporary CPU-based processor
                temp_processor = get_caption_model_processor(
                    model_name="florence2", 
                    model_name_or_path="weights/icon_caption_florence", 
                    device=torch.device("cpu")
                )
                
                # Run on CPU
                dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
                    image_save_path, 
                    yolo_model, 
                    BOX_TRESHOLD=box_threshold, 
                    output_coord_in_ratio=True, 
                    ocr_bbox=ocr_bbox,
                    draw_bbox_config=draw_bbox_config, 
                    caption_model_processor=temp_processor, 
                    ocr_text=text,
                    iou_threshold=iou_threshold, 
                    imgsz=imgsz,
                )
                
                image = Image.open(io.BytesIO(base64.b64decode(dino_labled_img)))
                parsed_content_list = '\n'.join([f'icon {i}: ' + str(v) for i,v in enumerate(parsed_content_list)])
                print("CPU fallback successful!", flush=True)
                
            except Exception as fallback_error:
                print(f"CPU fallback also failed: {fallback_error}", flush=True)
                # Return a simplified result with the original image
                return image_input, f"ERROR in icon detection: {str(e)}\n\nPartial progress: {status_msg}"
        
        total_time = time.time() - start_time
        print(f"Total processing completed in {total_time:.2f}s", flush=True)
        status_msg += f"Total processing completed in {total_time:.2f}s\n"
        print("==== PROCESSING COMPLETE ====", flush=True)
        
        return image, parsed_content_list
    
    except Exception as e:
        error_message = f"Error during processing: {str(e)}\n{traceback.format_exc()}"
        print(error_message, flush=True)
        return None, f"ERROR: {error_message}"

# Main processing function (now a simple wrapper around the timeout version)
def process(
    image_input,
    box_threshold,
    iou_threshold,
    use_paddleocr,
    imgsz
) -> Tuple[Optional[Image.Image], str]:
    print(f"Process function called with image: {image_input is not None}", flush=True)
    if image_input is None:
        print("No image provided", flush=True)
        return None, "ERROR: No image provided"
    
    return process_with_timeout(
        image_input,
        box_threshold,
        iou_threshold,
        use_paddleocr,
        imgsz
    )

with gr.Blocks() as demo:
    gr.Markdown(MARKDOWN)
    with gr.Row():
        with gr.Column():
            image_input_component = gr.Image(
                type='pil', label='Upload image')
            # set the threshold for removing the bounding boxes with low confidence, default is 0.05
            box_threshold_component = gr.Slider(
                label='Box Threshold', minimum=0.01, maximum=1.0, step=0.01, value=0.05)
            # set the threshold for removing the bounding boxes with large overlap, default is 0.1
            iou_threshold_component = gr.Slider(
                label='IOU Threshold', minimum=0.01, maximum=1.0, step=0.01, value=0.1)
            use_paddleocr_component = gr.Checkbox(
                label='Use PaddleOCR', value=False)  # Default to False for better performance
            imgsz_component = gr.Slider(
                label='Icon Detect Image Size', minimum=320, maximum=1280, step=32, value=320)
            submit_button_component = gr.Button(
                value='Submit', variant='primary')
        with gr.Column():
            image_output_component = gr.Image(type='pil', label='Image Output')
            text_output_component = gr.Textbox(label='Parsed screen elements', placeholder='Text Output')

    submit_button_component.click(
        fn=process,
        inputs=[
            image_input_component,
            box_threshold_component,
            iou_threshold_component,
            use_paddleocr_component,
            imgsz_component
        ],
        outputs=[image_output_component, text_output_component]
    )

print("Launching Gradio interface...", flush=True)
demo.launch(share=True, server_port=7861, server_name='0.0.0.0')
