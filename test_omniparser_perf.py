import time
import base64
import requests
import os
import sys
from pathlib import Path
import matplotlib.pyplot as plt

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

def run_benchmark(server_url="http://localhost:8000/parse/", num_runs=3):
    """Run a benchmark test against the OmniParser server"""
    print(f"Running benchmark against {server_url} with {num_runs} iterations")
    
    # Find a sample image
    test_image_path = find_sample_image()
    if not os.path.exists(test_image_path):
        print(f"Error: Image not found at {test_image_path}")
        return
    
    print(f"Using test image: {test_image_path}")
    
    # Load the image
    with open(test_image_path, "rb") as f:
        image_data = base64.b64encode(f.read()).decode('utf-8')
    
    # Test server connectivity
    try:
        probe_response = requests.get(server_url.replace("/parse/", "/probe"))
        if probe_response.status_code != 200:
            print(f"Warning: Server probe returned status {probe_response.status_code}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return
    
    # Run the benchmark
    results = []
    component_times = {
        'decode': [],
        'ocr': [],
        'som': []
    }
    
    print("\nStarting benchmark runs:")
    for i in range(num_runs):
        print(f"\nRun {i+1}/{num_runs}...")
        start = time.time()
        
        try:
            response = requests.post(server_url, json={"base64_image": image_data})
            response_json = response.json()
            
            latency = time.time() - start
            results.append(latency)
            
            # Print results from this run
            print(f"  Status: {response_json.get('status', 'unknown')}")
            print(f"  Latency: {latency:.2f}s (server reported: {response_json.get('latency', 'unknown')}s)")
            print(f"  Memory: {response_json.get('memory_usage_mb', 'unknown')} MB")
            
            # Extract component times if available from server logs
            # We'd need to parse the server logs to get these
            
        except Exception as e:
            print(f"  Error in run {i+1}: {e}")
        
        # Pause between runs to allow memory cleanup
        time.sleep(3)
    
    # Display results
    if results:
        avg_latency = sum(results) / len(results)
        print(f"\nBenchmark Results:")
        print(f"Average latency: {avg_latency:.2f} seconds")
        print(f"Min latency: {min(results):.2f} seconds")
        print(f"Max latency: {max(results):.2f} seconds")
        
        # Plot results
        plt.figure(figsize=(10, 6))
        plt.bar(range(1, len(results)+1), results)
        plt.axhline(y=avg_latency, color='r', linestyle='-', label=f'Average: {avg_latency:.2f}s')
        plt.xlabel('Run')
        plt.ylabel('Time (seconds)')
        plt.title('OmniParser Performance Test')
        plt.legend()
        plot_path = 'omniparser_perf.png'
        plt.savefig(plot_path)
        print(f"Results chart saved to {plot_path}")
    else:
        print("No successful benchmark runs completed")

if __name__ == "__main__":
    run_benchmark() 