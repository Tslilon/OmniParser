#!/bin/bash
# =============================================================
# OmniParser ML with Florence - Setup Script
# =============================================================
# 
# This script runs OmniParser with ML-based icon recognition
# and connects to a Windows VM for computer control.
#
# Usage: ./run_omniparser_ml.sh [windows_vm_ip:port]
#
# Example: ./run_omniparser_ml.sh 10.211.55.3:5000
#
# Notes:
# - Uses EasyOCR instead of PaddleOCR to avoid segmentation faults on Apple Silicon
# - Runs the OmniParser server with ML and the Gradio UI
# - Press Ctrl+C to stop all services
# =============================================================

# Set environment variables
export OMNIPARSER_DEVICE="mps"
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  export $(grep -v '^#' .env | xargs)
fi

# Allow custom Windows VM URL
WINDOWS_HOST_URL="${1:-10.211.55.3:5000}"
echo "Using Windows VM URL: $WINDOWS_HOST_URL"

# Kill any existing servers
echo "Stopping any existing servers..."
lsof -ti:8000 | xargs kill -9 2>/dev/null

# Start our debug server directly 
echo "Starting ML-based OmniParser server..."
python debug_server.py > /tmp/omniparser_server.log 2>&1 &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Sleep briefly
sleep 5

# Start the Gradio UI as a standalone process
echo "Starting Gradio UI..."
cd omnitool/gradio
python app.py --windows_host_url $WINDOWS_HOST_URL --omniparser_server_url localhost:8000 &
GRADIO_PID=$!
echo "Gradio UI started with PID: $GRADIO_PID"

echo "====================================================="
echo "OmniParser ML + Florence is now running!"
echo "---------------------------------------------------"
echo "OmniParser server: http://localhost:8000/probe"
echo "Gradio UI: http://localhost:7888"
echo "---------------------------------------------------"
echo "Press CTRL+C to stop all services"
echo "====================================================="

# Setup trap to clean up processes
function cleanup {
    echo "Cleaning up..."
    kill $SERVER_PID $GRADIO_PID 2>/dev/null
    exit
}
trap cleanup INT TERM

# Keep script running
wait
