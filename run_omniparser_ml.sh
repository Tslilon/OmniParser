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

# Set environment variables for optimal performance on Apple Silicon
export OMNIPARSER_DEVICE="mps"
export PYTORCH_ENABLE_MPS_FALLBACK=1
export MPS_ENABLE_SHARED_MEM=1

# Load custom environment variables if present
if [ -f .env ]; then
  echo "Loading environment variables from .env file..."
  export $(grep -v '^#' .env | xargs)
fi

# Allow custom Windows VM URL
WINDOWS_HOST_URL="${1:-10.211.55.3:5000}"
echo "Using Windows VM URL: $WINDOWS_HOST_URL"

# Kill any existing servers
echo "Stopping any existing servers..."
pkill -f "python.*debug_server.py" 2>/dev/null
pkill -f "python.*app.py" 2>/dev/null
lsof -ti:8000,7888 | xargs kill -9 2>/dev/null

# Clear any leftover shared memory
echo "Cleaning up shared memory..."
rm -f /tmp/torch* 2>/dev/null

# Start our debug server directly with optimized settings
echo "Starting ML-based OmniParser server..."
python debug_server.py > /tmp/omniparser_server.log 2>&1 &
SERVER_PID=$!
echo "Server started with PID: $SERVER_PID"

# Wait for server to be ready
echo "Waiting for server to initialize..."
MAX_RETRIES=30
RETRY_COUNT=0
while ! curl -s http://localhost:8000/probe > /dev/null; do
    sleep 1
    RETRY_COUNT=$((RETRY_COUNT + 1))
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "Server failed to start after $MAX_RETRIES seconds"
        cleanup
        exit 1
    fi
    echo -n "."
done
echo "Server is ready!"

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

# Setup trap to clean up processes and shared memory
function cleanup {
    echo "Cleaning up..."
    kill $SERVER_PID $GRADIO_PID 2>/dev/null
    rm -f /tmp/torch* 2>/dev/null
    exit
}
trap cleanup INT TERM

# Keep script running
wait
