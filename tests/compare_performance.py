import os
import sys
import time
import base64
import requests
import torch
import gc
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# Set environment variables
os.environ["OMNIPARSER_DEVICE"] = "mps"

# Configure path
root_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(root_dir)

from util.omniparser import Omniparser

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

def init_omniparser():
    """Initialize OmniParser for direct calls"""
    print("Setting up OmniParser for direct calls...")
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
    return omniparser

def test_direct_call(omniparser, image_base64, num_runs=3):
    """Test direct calls to OmniParser"""
    print("\nTesting direct calls to OmniParser...")
    direct_times = []
    
    for i in range(num_runs):
        print(f"\nDirect call {i+1}/{num_runs}...")
        
        # Clear memory before run
        gc.collect()
        if hasattr(torch.mps, 'empty_cache'):
            torch.mps.empty_cache()
            
        # Time the call
        start_time = time.time()
        with torch.inference_mode():
            dino_labled_img, parsed_content_list = omniparser.parse(image_base64)
        elapsed = time.time() - start_time
        
        print(f"Direct call completed in {elapsed:.2f} seconds")
        direct_times.append(elapsed)
        
        # Brief pause between runs
        time.sleep(1)
    
    return direct_times

def test_api_call(api_url, image_base64, num_runs=3):
    """Test API calls to OmniParser server"""
    print("\nTesting API calls to OmniParser server...")
    api_times = []
    
    # First check server connection
    try:
        probe_url = api_url.replace("/parse", "/probe").replace("/parse/", "/probe")
        response = requests.get(probe_url, timeout=5)
        if response.status_code != 200:
            print(f"Server probe failed with status {response.status_code}")
            return None
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return None
    
    print("Server connection successful, beginning API tests")
    
    for i in range(num_runs):
        print(f"\nAPI call {i+1}/{num_runs}...")
        
        try:
            start_time = time.time()
            response = requests.post(api_url, json={"base64_image": image_base64}, timeout=120)
            response_json = response.json()
            elapsed = time.time() - start_time
            
            print(f"API call completed in {elapsed:.2f} seconds")
            print(f"Server reported latency: {response_json.get('latency', 'unknown')}s")
            
            api_times.append(elapsed)
            
            # Print memory metrics if available
            if 'memory_before_mb' in response_json and 'memory_after_processing_mb' in response_json:
                memory_increase = response_json['memory_after_processing_mb'] - response_json['memory_before_mb']
                print(f"Memory increase: {memory_increase:.2f} MB")
                
                if 'memory_after_gc_mb' in response_json:
                    memory_retained = response_json['memory_after_gc_mb'] - response_json['memory_before_mb']
                    print(f"Memory retained after GC: {memory_retained:.2f} MB")
        
        except Exception as e:
            print(f"Error in API call: {e}")
        
        # Longer pause between API calls to let server recover
        time.sleep(3)
    
    return api_times

def compare_performance(api_url="http://localhost:8000/parse", num_runs=3):
    """Compare performance between direct calls and API calls"""
    # Find and load sample image
    test_image_path = find_sample_image()
    print(f"Using test image: {test_image_path}")
    
    with open(test_image_path, "rb") as f:
        image_bytes = f.read()
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    # Initialize OmniParser for direct calls
    omniparser = init_omniparser()
    
    # Test direct calls
    direct_times = test_direct_call(omniparser, image_base64, num_runs)
    
    # Test API calls
    api_times = test_api_call(api_url, image_base64, num_runs)
    
    # Generate report
    print("\n=== Performance Comparison Report ===")
    
    if direct_times:
        avg_direct = sum(direct_times) / len(direct_times)
        print(f"Direct calls average: {avg_direct:.2f} seconds")
        print(f"Direct calls min: {min(direct_times):.2f}, max: {max(direct_times):.2f}")
    
    if api_times:
        avg_api = sum(api_times) / len(api_times)
        print(f"API calls average: {avg_api:.2f} seconds")
        print(f"API calls min: {min(api_times):.2f}, max: {max(api_times):.2f}")
    
    if direct_times and api_times:
        slowdown_factor = avg_api / avg_direct
        print(f"\nAPI is {slowdown_factor:.1f}x slower than direct calls")
        
        # Plot comparison
        plot_comparison(direct_times, api_times)

def plot_comparison(direct_times, api_times):
    """Create a comparison plot of the results"""
    avg_direct = sum(direct_times) / len(direct_times)
    avg_api = sum(api_times) / len(api_times)
    
    fig, axs = plt.subplots(1, 2, figsize=(12, 5))
    
    # Individual runs bar chart
    x_direct = np.arange(len(direct_times)) + 1
    x_api = np.arange(len(api_times)) + 1
    
    axs[0].bar(x_direct, direct_times, label='Direct', alpha=0.7, color='blue')
    axs[0].axhline(y=avg_direct, color='blue', linestyle='--', alpha=0.7)
    
    axs[0].bar(x_api + len(direct_times) + 1, api_times, label='API', alpha=0.7, color='orange')
    axs[0].axhline(y=avg_api, color='orange', linestyle='--', alpha=0.7)
    
    axs[0].set_xlabel('Run Number')
    axs[0].set_ylabel('Time (seconds)')
    axs[0].set_title('Performance Per Run')
    axs[0].legend()
    
    # Average comparison
    methods = ['Direct Calls', 'API Calls']
    avgs = [avg_direct, avg_api]
    
    axs[1].bar(methods, avgs, alpha=0.7, color=['blue', 'orange'])
    for i, v in enumerate(avgs):
        axs[1].text(i, v + 0.5, f"{v:.2f}s", ha='center')
        
    axs[1].set_ylabel('Average Time (seconds)')
    axs[1].set_title(f'Average Performance Comparison\nAPI is {avg_api/avg_direct:.1f}x slower')
    
    plt.tight_layout()
    plt.savefig('performance_comparison.png')
    print("Performance comparison chart saved to 'performance_comparison.png'")
    
if __name__ == "__main__":
    if len(sys.argv) > 1:
        api_url = sys.argv[1]
        compare_performance(api_url=api_url)
    else:
        compare_performance() 