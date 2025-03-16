import os
import sys
import time
import torch
import gc
import base64
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from PIL import Image

# Configure path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from util.omniparser import Omniparser
from util.utils import get_som_labeled_img, check_ocr_box

def find_sample_image():
    """Find a sample image to use for testing"""
    # Try to find sample images in common locations
    possible_paths = [
        "tmp/outputs",  # Where screenshots are stored
        ".",  # Current directory
        "imgs",  # Images directory
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            image_files = [f for f in os.listdir(path) if f.endswith(('.png', '.jpg', '.jpeg'))]
            if image_files:
                return os.path.join(path, image_files[0])
    
    print("No sample images found. Please provide a path to a test image.")
    return input("Path to test image: ")

def create_patched_omniparser(batch_size):
    """Create an OmniParser with a patched get_som_labeled_img function that uses the specified batch size"""
    # Initialize OmniParser
    som_model_path = os.path.join(os.getcwd(), 'weights', 'icon_detect', 'model.pt')
    caption_model_path = os.path.join(os.getcwd(), 'weights', 'icon_caption_florence')
    
    config = {
        'som_model_path': som_model_path,
        'caption_model_name': 'florence2',
        'caption_model_path': caption_model_path,
        'device': 'mps',
        'BOX_TRESHOLD': 0.05
    }
    
    # Create OmniParser
    omniparser = Omniparser(config)
    
    # Store the specified batch size
    omniparser.batch_size = batch_size
    
    # Patch the parse method to use the specified batch size
    original_parse = omniparser.parse
    
    def patched_parse(image_base64):
        from util.utils import get_som_labeled_img
        start_total = time.time()
        
        # Image decoding and setup
        start_decode = time.time()
        image_bytes = base64.b64decode(image_base64)
        image = omniparser.image_setup(image_bytes)
        decode_time = time.time() - start_decode
        print(f"⏱️ PERF INTERNAL: Image decoding: {decode_time:.2f}s")

        # OCR processing
        start_ocr = time.time()
        (text, ocr_bbox), _ = omniparser.process_ocr(image)
        ocr_time = time.time() - start_ocr
        print(f"⏱️ PERF INTERNAL: OCR processing: {ocr_time:.2f}s")
        
        # SOM model (combined detection and caption generation)
        start_som = time.time()
        
        # Get dimensions
        w, h = image.size
        box_overlay_ratio = max(image.size) / 3200
        draw_bbox_config = {
            'text_scale': 0.8 * box_overlay_ratio,
            'text_thickness': max(int(2 * box_overlay_ratio), 1),
            'text_padding': max(int(3 * box_overlay_ratio), 1),
            'thickness': max(int(3 * box_overlay_ratio), 1),
        }
        
        # Use the specified batch size
        dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
            image, 
            omniparser.som_model, 
            BOX_TRESHOLD=omniparser.config['BOX_TRESHOLD'], 
            output_coord_in_ratio=True, 
            ocr_bbox=ocr_bbox,
            draw_bbox_config=draw_bbox_config, 
            caption_model_processor=omniparser.caption_model_processor, 
            ocr_text=text,
            use_local_semantics=True, 
            iou_threshold=0.7, 
            scale_img=False, 
            batch_size=omniparser.batch_size  # Use the specified batch size
        )
        som_time = time.time() - start_som
        print(f"⏱️ PERF INTERNAL: SOM model (detection + caption): {som_time:.2f}s")
        
        # Summary of timing
        total_time = time.time() - start_total
        print(f"⏱️ PERF INTERNAL: Total parsing breakdown:")
        print(f"⏱️ PERF INTERNAL:   - Image decoding: {decode_time:.2f}s ({decode_time/total_time*100:.1f}%)")
        print(f"⏱️ PERF INTERNAL:   - OCR processing: {ocr_time:.2f}s ({ocr_time/total_time*100:.1f}%)")
        print(f"⏱️ PERF INTERNAL:   - SOM model: {som_time:.2f}s ({som_time/total_time*100:.1f}%)")
        print(f"⏱️ PERF INTERNAL:   - Total: {total_time:.2f}s (100%)")
        
        return dino_labled_img, parsed_content_list
    
    # Add the image setup and OCR processing methods
    def image_setup(image_bytes):
        from PIL import Image
        import io
        image = Image.open(io.BytesIO(image_bytes))
        image = image.convert("RGB")  # for CLIP
        return image
    
    def process_ocr(image):
        from util.utils import check_ocr_box
        return check_ocr_box(image, display_img=False, output_bb_format='xyxy', easyocr_args={'text_threshold': 0.8}, use_paddleocr=False)
    
    # Attach the methods to the omniparser
    omniparser.patched_parse = patched_parse
    omniparser.image_setup = image_setup
    omniparser.process_ocr = process_ocr
    omniparser.parse = patched_parse
    
    return omniparser

def test_batch_size(batch_sizes=[1, 16, 32, 64, 128, 256], num_runs=3):
    """Test the performance of different batch sizes for the caption model"""
    print("Testing caption model batch sizes")
    
    # Set environment variables
    os.environ["OMNIPARSER_DEVICE"] = "mps"
    
    # Set default dtype to float32 for consistency
    torch.set_default_dtype(torch.float32)
    
    # Find and load sample image
    test_image_path = find_sample_image()
    print(f"Using test image: {test_image_path}")
    
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Test each batch size
    results = {}
    best_batch_size = None
    best_avg_time = float('inf')
    
    for batch_size in batch_sizes:
        print(f"\n=== Testing batch size: {batch_size} ===")
        
        # Clean up memory before testing a new batch size
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if hasattr(torch.mps, 'empty_cache'):
            torch.mps.empty_cache()
            
        try:
            # Initialize OmniParser with proper device handling
            config = {
                'som_model_path': os.path.join(os.getcwd(), 'weights', 'icon_detect', 'model.pt'),
                'caption_model_name': 'florence2',
                'caption_model_path': os.path.join(os.getcwd(), 'weights', 'icon_caption_florence'),
                'device': 'mps',
                'BOX_TRESHOLD': 0.05
            }
            
            omniparser = Omniparser(config)
            
            # Run tests
            times = []
            for run in range(num_runs):
                print(f"\nRun {run+1}/{num_runs}:")
                start_time = time.time()
                
                # Process image
                image = Image.open(test_image_path)
                ocr_bbox_rslt, _ = check_ocr_box(test_image_path, display_img=False)
                text, ocr_bbox = ocr_bbox_rslt
                
                box_overlay_ratio = max(image.size) / 3200
                draw_bbox_config = {
                    'text_scale': 0.8 * box_overlay_ratio,
                    'text_thickness': max(int(2 * box_overlay_ratio), 1),
                    'text_padding': max(int(3 * box_overlay_ratio), 1),
                    'thickness': max(int(3 * box_overlay_ratio), 1),
                }
                
                dino_labled_img, label_coordinates, parsed_content_list = get_som_labeled_img(
                    test_image_path,
                    omniparser.som_model,
                    BOX_TRESHOLD=0.05,
                    output_coord_in_ratio=True,
                    ocr_bbox=ocr_bbox,
                    draw_bbox_config=draw_bbox_config,
                    caption_model_processor=omniparser.caption_model_processor,
                    ocr_text=text,
                    use_local_semantics=True,
                    iou_threshold=0.7,
                    batch_size=batch_size
                )
                
                elapsed_time = time.time() - start_time
                times.append(elapsed_time)
                print(f"Processing time: {elapsed_time:.2f}s")
            
            # Calculate average time
            avg_time = sum(times) / len(times)
            results[batch_size] = avg_time
            
            # Update best batch size
            if avg_time < best_avg_time:
                best_avg_time = avg_time
                best_batch_size = batch_size
                
        except Exception as e:
            print(f"Error testing batch size {batch_size}: {str(e)}")
            continue
    
    # Plot results if we have any
    if results:
        plot_batch_size_results(results, best_batch_size)
    else:
        print("No results to plot")

def plot_batch_size_results(results, best_batch_size):
    """Plot the batch size optimization results"""
    if not results:
        print("No results to plot")
        return
        
    batch_sizes = sorted(results.keys())
    avg_times = [results[bs] for bs in batch_sizes]
    
    plt.figure(figsize=(10, 6))
    plt.plot(batch_sizes, avg_times, 'b-o')
    plt.axvline(x=best_batch_size, color='r', linestyle='--', label=f'Best batch size: {best_batch_size}')
    
    plt.xlabel('Batch Size')
    plt.ylabel('Average Processing Time (s)')
    plt.title('Batch Size vs Processing Time')
    plt.grid(True)
    plt.legend()
    
    # Save the plot
    plt.savefig('batch_size_optimization.png')
    plt.close()
    
    # Print summary
    print("\n=== Batch Size Optimization Results ===")
    for batch_size in batch_sizes:
        print(f"Batch size {batch_size}: {results[batch_size]:.2f}s")
    print(f"\nBest batch size: {best_batch_size} with {results[best_batch_size]:.2f}s average")

if __name__ == "__main__":
    test_batch_size() 