#!/usr/bin/env python3
import requests
import json
import sys
import time
import random
import argparse
from datetime import datetime

def send_mouse_command(vm_ip, action, x=None, y=None, coordinate=None):
    """
    Send a mouse command to the VM.
    
    Args:
        vm_ip (str): IP and port of VM Flask server
        action (str): The action to perform (move, left_click, right_click, double_click)
        x, y (int): Coordinates for the action
        coordinate (list): Alternative coordinate format [x, y]
    
    Returns:
        dict: Response data or None if failed
    """
    url = f"http://{vm_ip}/execute"
    
    # Prepare payload based on input format
    if coordinate:
        payload = {"action": action, "coordinate": coordinate}
    elif x is not None and y is not None:
        if action == "move":
            payload = {"action": "move", "x": x, "y": y}
        elif action == "left_click":
            payload = {"action": "left_click", "x": x, "y": y}
        elif action == "right_click":
            payload = {"action": "right_click", "x": x, "y": y}
        elif action == "double_click":
            payload = {"action": "double_click", "x": x, "y": y}
        else:
            payload = {"action": action, "x": x, "y": y}
    else:
        payload = {"action": action}
    
    # Log the command
    timestamp = datetime.now().strftime("%H:%M:%S")
    print(f"[{timestamp}] Sending: {json.dumps(payload)}")
    
    try:
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers, timeout=5)
        
        status = "✅" if response.status_code == 200 else "❌"
        print(f"[{timestamp}] {status} Status: {response.status_code}")
        
        if response.status_code == 200:
            try:
                return response.json()
            except:
                print(f"Response not JSON: {response.text}")
        else:
            print(f"Error response: {response.text}")
        
        return None
    except Exception as e:
        print(f"[{timestamp}] ❌ Error: {str(e)}")
        return None

def get_screen_size(vm_ip):
    """Get the screen size from the VM"""
    try:
        response = requests.get(f"http://{vm_ip}/info", timeout=5)
        if response.status_code == 200:
            data = response.json()
            if "screen" in data:
                return data["screen"]["width"], data["screen"]["height"]
    except:
        pass
    
    # Default if we can't get the actual size
    return 1920, 1080

def run_mouse_test_loop(vm_ip, num_actions=50, delay=2, random_mode=False):
    """
    Run a loop of mouse movements and clicks.
    
    Args:
        vm_ip (str): VM IP and port
        num_actions (int): Number of actions to perform
        delay (float): Delay between actions in seconds
        random_mode (bool): Whether to use random positions
    """
    print(f"\n===== STARTING MOUSE CONTROL TEST LOOP =====")
    print(f"VM: {vm_ip} | Actions: {num_actions} | Delay: {delay}s | Random: {random_mode}")
    
    # Try both standard and alternative action formats
    standard_format = True
    
    # Get screen dimensions
    width, height = get_screen_size(vm_ip)
    print(f"Screen size: {width}x{height}")
    
    # Define test points for mouse movements
    if not random_mode:
        test_points = [
            # Corners and center
            (100, 100), (width-100, 100), 
            (width-100, height-100), (100, height-100),
            (width//2, height//2),
            # Taskbar area
            (width//2, height-20),
            # Start menu
            (50, height-20),
            # Top areas (close buttons, etc)
            (width-20, 30), (width-60, 30), (width-100, 30)
        ]
    
    print("\nPress Ctrl+C to stop the test loop at any time...\n")
    
    try:
        for i in range(num_actions):
            # Determine coordinates for this action
            if random_mode:
                x = random.randint(50, width-50)
                y = random.randint(50, height-50)
            else:
                x, y = test_points[i % len(test_points)]
            
            # Choose an action (mostly moves, some clicks)
            if i % 5 == 0:
                action = "right_click"
            elif i % 7 == 0:
                action = "double_click"
            elif i % 3 == 0:
                action = "left_click"
            else:
                action = "move"
            
            # Alternate between standard and alternative formats
            if standard_format:
                send_mouse_command(vm_ip, action, x, y)
            else:
                if action == "move":
                    # Use consistent action name across all tests
                    alt_action = "move"
                else:
                    alt_action = action
                send_mouse_command(vm_ip, alt_action, coordinate=[x, y])
            
            # Toggle format for next request
            standard_format = not standard_format
            
            # Sleep between actions
            time.sleep(delay)
            
            # Show progress
            print(f"Completed {i+1}/{num_actions} actions")
            
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
    
    print("\n===== MOUSE CONTROL TEST COMPLETED =====")

def test_connectivity(vm_ip):
    """Test basic connectivity to the VM"""
    print(f"\n=== TESTING BASIC CONNECTIVITY ===")
    probe_url = f"http://{vm_ip}/probe"
    
    try:
        response = requests.get(probe_url, timeout=5)
        if response.status_code == 200:
            print(f"✅ Connected to VM at {vm_ip}")
            # Try to get screen info
            try:
                info_response = requests.get(f"http://{vm_ip}/info", timeout=5)
                if info_response.status_code == 200:
                    data = info_response.json()
                    print(f"✅ VM Info: {json.dumps(data, indent=2)}")
                else:
                    print(f"❌ Couldn't get VM info: {info_response.status_code}")
            except Exception as e:
                print(f"❌ Error getting VM info: {str(e)}")
            return True
        else:
            print(f"❌ Connection failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Connection error: {str(e)}")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test VM mouse control")
    parser.add_argument("--vm", default="10.211.55.3:5000", help="VM IP:port")
    parser.add_argument("--actions", type=int, default=20, help="Number of actions to perform")
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between actions")
    parser.add_argument("--random", action="store_true", help="Use random positions")
    args = parser.parse_args()
    
    print(f"VM Mouse Control Test")
    print(f"--------------------")
    
    # First verify connectivity
    if test_connectivity(args.vm):
        # Run the mouse test loop
        run_mouse_test_loop(args.vm, args.actions, args.delay, args.random)
    else:
        print(f"Cannot continue testing - no connection to VM") 