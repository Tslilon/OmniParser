#!/bin/bash

# Load environment variables from .env file if it exists
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  export $(grep -v '^#' .env | xargs)
fi

# Start Hybrid Setup Script for Mac/Unix
# This script starts the necessary services for OmniParser with MPS support

# Set environment variables
export OMNIPARSER_DEVICE="mps"
# Explicitly export the OpenAI API key to make sure it's available to subprocesses
export OPENAI_API_KEY="${OPENAI_API_KEY}"
echo "Using OpenAI API Key: ${OPENAI_API_KEY:0:5}..."

# Define variables
WINDOWS_HOST_URL="${1:-localhost:5001}"
OMNIPARSER_URL="${2:-localhost:8000}"
WORKSPACE_DIR="$(pwd)"

# Print banner
echo "============================================================"
echo "OmniParser Hybrid Setup (Mac/Unix)"
echo "============================================================"
echo "Using the following configuration:"
echo "- Windows VM URL: $WINDOWS_HOST_URL"
echo "- OmniParser URL: $OMNIPARSER_URL"
echo "- Device: $OMNIPARSER_DEVICE"
echo "- Workspace: $WORKSPACE_DIR"
echo "============================================================"

# Test Windows VM connection
echo "Testing connection to Windows VM server..."
if curl -s "http://$WINDOWS_HOST_URL/probe" > /dev/null; then
  echo "✅ Windows VM server is running and accessible"
else
  echo "⚠️ Warning: Windows VM server not responding at http://$WINDOWS_HOST_URL/probe"
  echo "Make sure the server is running on your Windows VM"
fi

# Ensure output directories exist
mkdir -p omnitool/gradio/tmp/outputs
mkdir -p tmp/outputs

# Function to check if a process is running on a specific port
check_port() {
  lsof -i:$1 > /dev/null
  return $?
}

# Start OmniParser server (if not already running)
if check_port 8000; then
  echo "OmniParser server is already running on port 8000"
else
  echo "Starting OmniParser server..."
  # Check if simpler OmniParser should be used
  if [ "$3" == "simple" ]; then
    USE_SIMPLE_SERVER=true
  else
    USE_SIMPLE_SERVER=false
  fi
  
  if [ "$USE_SIMPLE_SERVER" = true ]; then
    echo "Using simplified OmniParser server..."
    python simple_omniparser_server.py &
    OMNIPARSER_PID=$!
    echo "OmniParser server started with PID: $OMNIPARSER_PID"
  else
    echo "Attempting to start ML-based OmniParser server..."
    # Add the current directory to PYTHONPATH to help with module imports
    export PYTHONPATH="$WORKSPACE_DIR:$PYTHONPATH"
    echo "Set PYTHONPATH to include workspace: $PYTHONPATH"
    
    # Try to start the server using the module approach first
    echo "Attempting to start OmniParser server using module approach..."
    python -m omnitool.omniparserserver.omniparserserver \
      --device $OMNIPARSER_DEVICE \
      --som_model_path "$WORKSPACE_DIR/weights/icon_detect/model.pt" \
      --caption_model_path "$WORKSPACE_DIR/weights/icon_caption_florence" &
    OMNIPARSER_PID=$!
    
    # Wait a moment and check if server started successfully
    sleep 5
    if ! check_port 8000; then
      echo "Module approach failed. Trying to start directly from the script..."
      kill $OMNIPARSER_PID 2>/dev/null
      
      # Try the direct script approach instead
      cd "$WORKSPACE_DIR/omnitool/omniparserserver"
      python omniparserserver.py \
        --device $OMNIPARSER_DEVICE \
        --som_model_path "$WORKSPACE_DIR/weights/icon_detect/model.pt" \
        --caption_model_path "$WORKSPACE_DIR/weights/icon_caption_florence" &
      OMNIPARSER_PID=$!
      cd "$WORKSPACE_DIR"
      
      # Wait for server to start
      sleep 5
    fi
    
    # Check if server is responding to probe
    echo "Checking if OmniParser server is responding..."
    if ! curl -s "http://$OMNIPARSER_URL/probe" > /dev/null; then
      echo "ML-based OmniParser server is not responding. Falling back to simple server."
      # Kill the non-responsive server
      kill $OMNIPARSER_PID 2>/dev/null
      
      # Start the simple server instead
      echo "Starting simplified OmniParser server..."
      python simple_omniparser_server.py &
      OMNIPARSER_PID=$!
      echo "Simple OmniParser server started with PID: $OMNIPARSER_PID"
    else
      echo "ML-based OmniParser server is responding correctly."
    fi
    
    echo "OmniParser server started with PID: $OMNIPARSER_PID"
  fi
fi

# Wait for OmniParser to start
echo "Waiting for OmniParser server to initialize..."
sleep 5

# Verify OmniParser server is responding
echo "Verifying OmniParser server is responding..."
MAX_ATTEMPTS=30
ATTEMPTS=0
OMNIPARSER_READY=false

while [ $ATTEMPTS -lt $MAX_ATTEMPTS ]; do
  if curl -s "http://$OMNIPARSER_URL/probe" > /dev/null; then
    echo "✅ OmniParser server is running and accessible"
    OMNIPARSER_READY=true
    break
  else
    echo "⏳ OmniParser server not ready yet, waiting (attempt $((ATTEMPTS+1))/$MAX_ATTEMPTS)..."
    ATTEMPTS=$((ATTEMPTS+1))
    sleep 2
  fi
done

if [ "$OMNIPARSER_READY" = false ]; then
  echo "❌ ERROR: OmniParser server failed to respond within the timeout period"
  echo "You can try running the script again or running with the simple server option:"
  echo "  ./start_hybrid_setup.sh $WINDOWS_HOST_URL $OMNIPARSER_URL simple"
  exit 1
fi

# Start Gradio UI
echo "Starting Gradio UI..."
cd "$WORKSPACE_DIR/omnitool/gradio"
python app.py --windows_host_url $WINDOWS_HOST_URL --omniparser_server_url $OMNIPARSER_URL --vnc_port 8006

# Cleanup function
cleanup() {
  echo "Shutting down services..."
  if [ -n "$OMNIPARSER_PID" ]; then
    kill $OMNIPARSER_PID
  fi
  exit 0
}

# Set up cleanup on script termination
trap cleanup SIGINT SIGTERM

# Keep script running
wait 

# Get the VM address from command line argument
if [ -z "$1" ]; then
  echo "Usage: $0 <VM_IP>:<API_PORT>"
  echo "Example: $0 10.211.55.3:5000"
  exit 1
fi

# Parse the VM IP and API port
VM_ADDRESS=$1
VM_IP=$(echo $VM_ADDRESS | cut -d':' -f1)
API_PORT=$(echo $VM_ADDRESS | cut -d':' -f2)
VNC_PORT=8006

echo "======================================================"
echo "OmniParser Hybrid Setup - Starting Services"
echo "======================================================"
echo "Windows VM IP: $VM_IP"
echo "API Port: $API_PORT"
echo "VNC Port: $VNC_PORT"
echo "======================================================"

# Check if VM is reachable
ping -c 1 $VM_IP > /dev/null
if [ $? -ne 0 ]; then
  echo "ERROR: Cannot reach Windows VM at $VM_IP"
  echo "Please ensure the VM is running and reachable from this machine."
  exit 1
fi

# Check if API is accessible
curl -s "http://$VM_IP:$API_PORT/probe" > /dev/null
if [ $? -ne 0 ]; then
  echo "WARNING: API is not responding at http://$VM_IP:$API_PORT/probe"
  echo "Make sure fix_omniparser.bat is running on the Windows VM."
fi

# Check if VNC port is accessible
nc -z -w 2 $VM_IP $VNC_PORT > /dev/null
if [ $? -ne 0 ]; then
  echo "WARNING: VNC service is not responding at $VM_IP:$VNC_PORT"
  echo "Make sure fix_omniparser.bat is running on the Windows VM."
fi

echo "Starting OmniParser with VNC integration..."
echo "You can access the application at http://localhost:7860"
echo "You can access the VNC viewer at http://$VM_IP:$VNC_PORT/vnc.html"
echo ""

# Start the main application with the VM parameters
python omniparser_app.py --vm-ip=$VM_IP --api-port=$API_PORT --vnc-port=$VNC_PORT 