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
    echo "Using simplified OmniParser server..."
    python simple_omniparser_server.py &
    OMNIPARSER_PID=$!
    echo "OmniParser server started with PID: $OMNIPARSER_PID"
  else
    echo "Using full ML-based OmniParser server..."
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
    sleep 2
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
    fi
    
    echo "OmniParser server started with PID: $OMNIPARSER_PID"
  fi
fi

# Wait for OmniParser to start
echo "Waiting for OmniParser server to initialize..."
sleep 5

# Start Gradio UI
echo "Starting Gradio UI..."
cd "$WORKSPACE_DIR/omnitool/gradio"
python app.py --windows_host_url $WINDOWS_HOST_URL --omniparser_server_url $OMNIPARSER_URL

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