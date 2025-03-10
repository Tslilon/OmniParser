#!/bin/bash

# Start Hybrid Setup Script for Mac/Unix
# This script starts the necessary services for OmniParser with MPS support

# Set environment variables
export OMNIPARSER_DEVICE="mps"

# Define variables
WINDOWS_HOST_URL="${1:-10.211.55.3:5000}"
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
    python -m omnitool.omniparserserver.omniparserserver \
      --device $OMNIPARSER_DEVICE \
      --som_model_path "$WORKSPACE_DIR/weights/icon_detect/model.pt" \
      --caption_model_path "$WORKSPACE_DIR/weights/icon_caption_florence" &
    OMNIPARSER_PID=$!
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