#!/usr/bin/env python
# Test script to verify MPS support in OmniParser

import os
import torch
from util.utils import get_device

# Test different environment configurations
def test_device_selection():
    # Save current environment
    original_env = os.environ.get("OMNIPARSER_DEVICE", None)
    
    # Test 1: Default behavior (no env var)
    if "OMNIPARSER_DEVICE" in os.environ:
        del os.environ["OMNIPARSER_DEVICE"]
    
    device = get_device()
    print(f"Test 1 - Default behavior: {device}")
    
    # Test 2: With MPS explicitly set
    os.environ["OMNIPARSER_DEVICE"] = "mps"
    device = get_device()
    print(f"Test 2 - MPS explicitly set: {device}")
    
    # Test 3: With CPU explicitly set
    os.environ["OMNIPARSER_DEVICE"] = "cpu"
    device = get_device()
    print(f"Test 3 - CPU explicitly set: {device}")
    
    # Restore original environment
    if original_env is not None:
        os.environ["OMNIPARSER_DEVICE"] = original_env
    elif "OMNIPARSER_DEVICE" in os.environ:
        del os.environ["OMNIPARSER_DEVICE"]

# Test tensor operations
def test_tensor_operations():
    # Save current environment
    original_env = os.environ.get("OMNIPARSER_DEVICE", None)
    
    # Set MPS as device
    os.environ["OMNIPARSER_DEVICE"] = "mps"
    device = get_device()
    
    print(f"\nRunning tensor operations on {device}...")
    
    # Create tensor on device
    x = torch.rand(1000, 1000, device=device)
    y = torch.rand(1000, 1000, device=device)
    
    # Perform operation
    import time
    start_time = time.time()
    z = torch.matmul(x, y)
    end_time = time.time()
    
    print(f"Matrix multiplication shape: {z.shape}")
    print(f"Operation completed in {(end_time - start_time)*1000:.2f} ms")
    
    # Restore original environment
    if original_env is not None:
        os.environ["OMNIPARSER_DEVICE"] = original_env
    elif "OMNIPARSER_DEVICE" in os.environ:
        del os.environ["OMNIPARSER_DEVICE"]

if __name__ == "__main__":
    print("=== Testing MPS Support in OmniParser ===")
    print(f"PyTorch version: {torch.__version__}")
    print(f"MPS available: {torch.backends.mps.is_available()}")
    print(f"MPS built: {torch.backends.mps.is_built()}")
    
    test_device_selection()
    
    if torch.backends.mps.is_available():
        test_tensor_operations()
    else:
        print("\nSkipping tensor operations test - MPS not available")
    
    print("\n=== Test Complete ===") 