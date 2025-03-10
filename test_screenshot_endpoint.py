#!/usr/bin/env python
# Test script to verify cross-platform screenshot functionality

import os
import sys
import requests
from PIL import Image
from io import BytesIO
from omnitool.gradio.tools.screen_capture import get_screenshot

def test_screenshot_capture(windows_host_url):
    """Test capturing a screenshot from the specified endpoint"""
    print(f"Testing screenshot capture from: {windows_host_url}")
    
    try:
        # Test direct endpoint access
        print("Test 1: Direct endpoint access...")
        response = requests.get(f'http://{windows_host_url}/screenshot')
        if response.status_code != 200:
            print(f"❌ Failed to access screenshot endpoint: HTTP {response.status_code}")
            return False
        
        # Try to open the image
        try:
            img = Image.open(BytesIO(response.content))
            print(f"✅ Successfully retrieved screenshot: {img.size}")
        except Exception as e:
            print(f"❌ Failed to parse screenshot: {str(e)}")
            return False
        
        # Test through our utility function
        print("\nTest 2: Using get_screenshot() function...")
        try:
            screenshot, path = get_screenshot(windows_host_url=windows_host_url)
            print(f"✅ Screenshot captured and saved to: {path}")
            print(f"   Size: {screenshot.size}")
        except Exception as e:
            print(f"❌ Failed to capture screenshot: {str(e)}")
            return False
        
        print("\nAll tests passed successfully!")
        return True
    
    except Exception as e:
        print(f"❌ Error during testing: {str(e)}")
        return False

if __name__ == "__main__":
    # Default endpoint
    windows_host_url = "localhost:5000"
    
    # Check if a custom endpoint was provided
    if len(sys.argv) > 1:
        windows_host_url = sys.argv[1]
    
    print("=== Testing Cross-Platform Screenshot Functionality ===")
    print(f"Using Windows host URL: {windows_host_url}")
    
    if test_screenshot_capture(windows_host_url):
        print("\n✅ All screenshot tests completed successfully")
    else:
        print("\n❌ Some screenshot tests failed")
    
    print("\n=== Test Complete ===") 