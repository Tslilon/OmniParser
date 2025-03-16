from flask import Flask, request, jsonify, send_file
from flask_cors import CORS
import pyautogui
import io
from PIL import Image, ImageDraw, ImageFont
import os
import logging
import traceback
import sys
import platform
import time
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,  # Change to DEBUG for more verbose logging
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('C:\\omniserver\\server.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('flask_server')

# Create Flask app
app = Flask(__name__)
CORS(app)

# System info for diagnostics
logger.info(f"Starting OmniParser Flask API Server")
logger.info(f"Python version: {sys.version}")
logger.info(f"Platform: {platform.platform()}")
logger.info(f"Screen size: {pyautogui.size()}")

@app.route('/probe', methods=['GET'])
def probe():
    """Health check endpoint"""
    logger.info("Probe endpoint called")
    return jsonify({'status': 'ok'})

@app.route('/info', methods=['GET'])
def info():
    """Return system information"""
    logger.info("Info endpoint called")
    screen_width, screen_height = pyautogui.size()
    return jsonify({
        'status': 'ok',
        'screen': {
            'width': screen_width,
            'height': screen_height
        },
        'platform': platform.platform(),
        'python_version': sys.version
    })

@app.route('/screensize', methods=['GET'])
def screensize():
    """Return screen dimensions - dedicated endpoint for clients"""
    logger.info("Screensize endpoint called")
    try:
        screen_width, screen_height = pyautogui.size()
        logger.info(f"Successfully retrieved screen size: {screen_width}x{screen_height}")
    except Exception as e:
        logger.warning(f"Failed to get screen size: {str(e)}")
        logger.warning(traceback.format_exc())
        screen_width, screen_height = 1920, 1080
        logger.info(f"Using default screen size: {screen_width}x{screen_height}")
    
    return jsonify({
        'width': screen_width,
        'height': screen_height
    })

@app.route('/screenshot', methods=['GET'])
def screenshot():
    """Take a screenshot and return it"""
    try:
        logger.info("Screenshot endpoint called")
        start_time = time.time()
        
        # Take a screenshot using pyautogui
        img = pyautogui.screenshot()
        
        if img:
            # Log successful capture and image details
            width, height = img.size
            logger.info(f"Screenshot captured successfully: {width}x{height} pixels")
            
            # Check if the image dimensions match expected screen dimensions
            screen_width, screen_height = pyautogui.size()
            if width != screen_width or height != screen_height:
                logger.warning(f"Screenshot dimensions ({width}x{height}) don't match screen size ({screen_width}x{screen_height})")
        
            # Convert PIL Image to bytes
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            # Return image file
            logger.info(f"Returning screenshot (took {time.time() - start_time:.2f}s)")
            return send_file(img_bytes, mimetype='image/png')
        else:
            # This shouldn't happen, but just in case
            logger.error("Screenshot capture returned None")
            return jsonify({'error': 'Failed to capture screenshot - empty image'}), 500
            
    except Exception as e:
        logger.error(f"Screenshot endpoint failed: {str(e)}")
        logger.error(traceback.format_exc())
        
        # Create a placeholder image with error details
        try:
            error_img = Image.new('RGB', (800, 600), color=(255, 0, 0))
            draw = ImageDraw.Draw(error_img)
            font = ImageFont.load_default()
            draw.text((50, 50), f"Screenshot Error: {str(e)}", fill=(255, 255, 255), font=font)
            draw.text((50, 100), traceback.format_exc(), fill=(255, 255, 255), font=font)
            
            # Add system info to error image
            draw.text((50, 300), f"Python: {sys.version}", fill=(255, 255, 255), font=font)
            draw.text((50, 350), f"Platform: {platform.platform()}", fill=(255, 255, 255), font=font)
            
            # Convert to bytes
            img_bytes = io.BytesIO()
            error_img.save(img_bytes, format='PNG')
            img_bytes.seek(0)
            
            logger.info("Returning error image placeholder")
            return send_file(img_bytes, mimetype='image/png')
        except Exception as inner_e:
            logger.error(f"Failed to create error image: {str(inner_e)}")
            return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/execute', methods=['POST'])
def execute():
    """Execute mouse or keyboard actions"""
    try:
        logger.info("Execute endpoint called")
        
        # Debug: Log raw request data
        logger.debug(f"Request data type: {type(request.data)}")
        logger.debug(f"Raw request data: {request.data}")
        
        # Debug: Log parsed JSON
        try:
            data = request.json
            logger.debug(f"Parsed JSON data: {data}")
        except Exception as json_error:
            logger.error(f"Failed to parse JSON: {str(json_error)}")
            return jsonify({'error': 'Invalid JSON data'}), 400
        
        # Handle Python command execution
        if 'command' in data:
            cmd = data.get('command')
            logger.info(f"Executing command: {cmd}")
            
            try:
                # Debug: Log command details
                logger.debug(f"Command type: {type(cmd)}")
                if isinstance(cmd, list):
                    logger.debug(f"Command list items: {len(cmd)}")
                    for i, item in enumerate(cmd):
                        logger.debug(f"  Item {i}: {item} (type: {type(item)})")
                
                # Execute the command
                result = subprocess.run(cmd, capture_output=True, text=True)
                
                # Debug: Log command results
                logger.debug(f"Command stdout: {result.stdout}")
                logger.debug(f"Command stderr: {result.stderr}")
                logger.debug(f"Command return code: {result.returncode}")
                
                return jsonify({'output': result.stdout, 'error': result.stderr})
            except Exception as cmd_error:
                logger.error(f"Command execution failed: {str(cmd_error)}")
                logger.error(traceback.format_exc())
                return jsonify({'error': f'Command execution failed: {str(cmd_error)}'}), 500
        
        # Add this block to handle potential VNC conflicts
        try:
            # Force releasing any keys that might be held down by VNC
            pyautogui.keyUp('alt')
            pyautogui.keyUp('ctrl')
            pyautogui.keyUp('shift')
        except:
            pass
            
        action = data.get('action')
        
        if action == 'left_click':
            # Get coordinates or use current position
            x = data.get('x')
            y = data.get('y')
            if x is not None and y is not None:
                logger.info(f"Clicking at position ({x}, {y})")
                pyautogui.click(x=x, y=y)
            else:
                logger.info("Clicking at current position")
                pyautogui.click()
            return jsonify({'status': 'success', 'action': 'left_click'})
            
        elif action == 'right_click':
            x = data.get('x')
            y = data.get('y')
            if x is not None and y is not None:
                logger.info(f"Right-clicking at position ({x}, {y})")
                pyautogui.rightClick(x=x, y=y)
            else:
                logger.info("Right-clicking at current position")
                pyautogui.rightClick()
            return jsonify({'status': 'success', 'action': 'right_click'})
            
        elif action == 'double_click':
            x = data.get('x')
            y = data.get('y')
            if x is not None and y is not None:
                logger.info(f"Double-clicking at position ({x}, {y})")
                pyautogui.doubleClick(x=x, y=y)
            else:
                logger.info("Double-clicking at current position")
                pyautogui.doubleClick()
            return jsonify({'status': 'success', 'action': 'double_click'})
            
        elif action == 'move':
            x = data.get('x')
            y = data.get('y')
            # Hardcode the duration for smooth movement (in seconds)
            duration = 0.5  # Fixed smooth movement duration
            if x is not None and y is not None:
                logger.info(f"Moving to position ({x}, {y}) with duration {duration}s")
                pyautogui.moveTo(x=x, y=y, duration=duration)
            return jsonify({'status': 'success', 'action': 'move'})
            
        elif action == 'type':
            text = data.get('text', '')
            logger.info(f"Typing text: {text}")
            pyautogui.write(text)
            return jsonify({'status': 'success', 'action': 'type'})
            
        elif action == 'press':
            key = data.get('key', '')
            logger.info(f"Pressing key: {key}")
            pyautogui.press(key)
            return jsonify({'status': 'success', 'action': 'press'})
            
        elif action == 'hotkey':
            keys = data.get('keys', [])
            logger.info(f"Pressing hotkey: {keys}")
            pyautogui.hotkey(*keys)
            return jsonify({'status': 'success', 'action': 'hotkey'})
            
        elif action == 'scroll':
            amount = data.get('amount', 0)
            logger.info(f"Scrolling amount: {amount}")
            pyautogui.scroll(amount)
            return jsonify({'status': 'success', 'action': 'scroll'})
            
        else:
            logger.warning(f"Unsupported action: {action}")
            return jsonify({'error': f'Unsupported action: {action}'}), 400
        
    except Exception as e:
        logger.error(f"Execute endpoint failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e), 'traceback': traceback.format_exc()}), 500

@app.route('/debug-command', methods=['GET'])
def debug_command():
    """Debug endpoint to test command execution"""
    logger.info("Debug command endpoint called")
    try:
        # Execute a simple command to get screen size
        result = subprocess.run(
            ["python", "-c", "import pyautogui; print(pyautogui.size())"], 
            capture_output=True, 
            text=True
        )
        
        # Log results
        logger.info(f"Command test stdout: {result.stdout}")
        logger.info(f"Command test stderr: {result.stderr}")
        logger.info(f"Command test return code: {result.returncode}")
        
        return jsonify({
            'stdout': result.stdout,
            'stderr': result.stderr,
            'returncode': result.returncode
        })
    except Exception as e:
        logger.error(f"Debug command failed: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    logger.info("Starting Flask server on port 5000...")
    print("Starting Flask server on port 5000...")
    print(f"Log file: C:\\omniserver\\server.log")
    print(f"Screen size: {pyautogui.size()}")
    print("Press Ctrl+C to stop the server")
    app.run(host='0.0.0.0', port=5000)