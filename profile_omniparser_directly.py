import os
import sys
import time
import torch
from util.omniparser import Omniparser
from PIL import Image
import base64
import io
import cProfile
import pstats
import matplotlib.pyplot as plt

# Set environment variables
os.environ["OMNIPARSER_DEVICE"] = "mps"

def find_sample_image():
    """Find a sample image to use for testing"""
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

def profile_omniparser():
    # Initialize OmniParser
    print("Setting up OmniParser...")
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
    init_time = time.time() - start_time
    print(f"OmniParser initialized in {init_time:.2f} seconds")
    
    # Find and load sample image
    test_image_path = find_sample_image()
    print(f"Using test image: {test_image_path}")
    
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Run OmniParser with profiling
    print("\nRunning OmniParser with profiling...")
    
    # Regular timing
    times = []
    component_times = {
        'decode': [],
        'ocr': [],
        'som': []
    }
    
    # Run multiple iterations
    num_runs = 3
    for i in range(num_runs):
        print(f"\nRun {i+1}/{num_runs}...")
        
        # Run with timing
        start_time = time.time()
        dino_labled_img, parsed_content_list = omniparser.parse(image_base64)
        total_time = time.time() - start_time
        times.append(total_time)
        
        print(f"Total processing time: {total_time:.2f} seconds")
        
        # Collect component times from the most recent run's print output
        # Since we have instrumented omniparser.py to print these
        
        # Wait before next run to let memory clean up
        if i < num_runs - 1:
            print("Waiting for memory cleanup...")
            time.sleep(3)
    
    # Run once with cProfile for detailed profiling
    print("\nRunning with cProfile for detailed breakdown...")
    profiler = cProfile.Profile()
    profiler.enable()
    dino_labled_img, parsed_content_list = omniparser.parse(image_base64)
    profiler.disable()
    
    # Save and print results
    stats = pstats.Stats(profiler).sort_stats('cumtime')
    stats.print_stats(20)  # Print top 20 time-consuming functions
    stats.dump_stats('omniparser_profile.prof')
    
    # Plot results
    plt.figure(figsize=(10, 6))
    plt.bar(range(1, len(times)+1), times)
    plt.axhline(y=sum(times)/len(times), color='r', linestyle='-', label=f'Average: {sum(times)/len(times):.2f}s')
    plt.xlabel('Run')
    plt.ylabel('Time (seconds)')
    plt.title('OmniParser Performance (Direct Call)')
    plt.legend()
    plt.savefig('omniparser_direct_perf.png')
    
    print(f"\nResults Summary:")
    print(f"Average processing time: {sum(times)/len(times):.2f} seconds")
    print(f"Min processing time: {min(times):.2f} seconds")
    print(f"Max processing time: {max(times):.2f} seconds")
    print(f"Detailed profiling saved to omniparser_profile.prof")
    print(f"Chart saved to omniparser_direct_perf.png")

if __name__ == "__main__":
    profile_omniparser() 