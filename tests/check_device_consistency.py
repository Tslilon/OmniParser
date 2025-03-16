import os
import sys
import time
import torch
import gc
from pathlib import Path
import base64

# Configure path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from util.omniparser import Omniparser
from tests.model_device_monitor import ModelDeviceMonitor

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

def test_device_consistency(num_runs=5):
    """Test if models stay on the same device across multiple processing requests"""
    print("Testing model device consistency across multiple processing requests")
    
    # Set environment variables
    device = "mps"
    os.environ["OMNIPARSER_DEVICE"] = device
    print(f"Using device: {device}")
    
    # Find and load sample image
    test_image_path = find_sample_image()
    print(f"Using test image: {test_image_path}")
    
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Initialize model monitoring
    monitor = ModelDeviceMonitor()
    
    # Initialize OmniParser
    print("\nInitializing OmniParser...")
    som_model_path = os.path.join(os.getcwd(), 'weights', 'icon_detect', 'model.pt')
    caption_model_path = os.path.join(os.getcwd(), 'weights', 'icon_caption_florence')
    
    config = {
        'som_model_path': som_model_path,
        'caption_model_name': 'florence2',
        'caption_model_path': caption_model_path,
        'device': device,
        'BOX_TRESHOLD': 0.05
    }
    
    start_time = time.time()
    omniparser = Omniparser(config)
    init_time = time.time() - start_time
    print(f"OmniParser initialized in {init_time:.2f} seconds")
    
    # Initial device check
    print("\nInitial device check:")
    device_info = monitor.log_model_devices(omniparser)
    print_device_info(device_info)
    
    # Process image multiple times
    for i in range(num_runs):
        print(f"\nRun {i+1}/{num_runs}:")
        
        # Process image and track timings
        start_time = time.time()
        with torch.inference_mode():
            dino_labled_img, parsed_content_list = omniparser.parse(image_base64)
        elapsed = time.time() - start_time
        
        print(f"Processing completed in {elapsed:.2f} seconds")
        
        # Check devices after processing
        device_info = monitor.log_model_devices(omniparser)
        print_device_info(device_info)
        
        # Check memory and force garbage collection
        memory_info = monitor.log_memory_usage()
        print(f"Memory usage: {memory_info.get('system_memory_mb', 'unknown'):.2f} MB")
        
        memory_info = monitor.force_gc()
        print(f"Memory after GC: {memory_info.get('system_memory_mb', 'unknown'):.2f} MB")
        
        # Brief pause between runs
        time.sleep(1)
    
    # Final summary
    print("\n=== Device Consistency Summary ===")
    monitor.print_summary()
    
    # Check for device consistency
    is_consistent = check_device_consistency(monitor.device_logs)
    if is_consistent:
        print("\n✅ Models maintained consistent device placement across all runs")
    else:
        print("\n❌ Models changed devices across runs - this is likely causing performance issues")

def print_device_info(device_info):
    """Print relevant device information"""
    som_device = device_info.get("som_model_device", "unknown")
    caption_device = device_info.get("caption_model_device", "unknown")
    
    print(f"  SOM model device: {som_device}")
    print(f"  Caption model device: {caption_device}")
    print(f"  Caption model dtype: {device_info.get('caption_model_dtype', 'unknown')}")

def check_device_consistency(device_logs):
    """Check if devices remained consistent across runs"""
    if not device_logs or len(device_logs) < 2:
        return True
    
    # Get initial devices
    initial = device_logs[0]
    initial_som_device = initial.get("som_model_device", "")
    initial_caption_device = initial.get("caption_model_device", "")
    
    # Check all logs for consistency
    for log in device_logs[1:]:
        som_device = log.get("som_model_device", "")
        caption_device = log.get("caption_model_device", "")
        
        if som_device != initial_som_device or caption_device != initial_caption_device:
            print(f"Device change detected:")
            print(f"  Initial SOM: {initial_som_device} → Current: {som_device}")
            print(f"  Initial Caption: {initial_caption_device} → Current: {caption_device}")
            return False
    
    return True

if __name__ == "__main__":
    test_device_consistency() 