#!/bin/bash
# Script to set up paddlepaddle and paddleocr on Apple Silicon Macs (M1/M2/M3)
# This addresses the known issue with PaddleOCR hanging on Apple Silicon

echo "==== OmniParser Setup for Apple Silicon Macs ===="
echo "This script will install compatible versions of paddlepaddle and paddleocr for Apple Silicon."

# Check if running on Apple Silicon
if [[ $(uname -m) != "arm64" ]]; then
    echo "⚠️ Warning: This script is intended for Apple Silicon Macs (M1/M2/M3)."
    echo "Your machine appears to be running on $(uname -m) architecture."
    read -p "Do you want to continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Setup cancelled."
        exit 1
    fi
fi

# Uninstall existing paddle packages
echo "Removing any existing paddle packages..."
pip uninstall -y paddlepaddle paddleocr

# Install development version of paddlepaddle with Apple Silicon optimizations
echo "Installing paddlepaddle development version optimized for Apple Silicon..."
python -m pip install paddlepaddle==0.0.0 -f https://www.paddlepaddle.org.cn/whl/mac/cpu/develop.html

# Check if paddlepaddle installation was successful
if [ $? -ne 0 ]; then
    echo "❌ Failed to install paddlepaddle. Please check your internet connection and try again."
    exit 1
fi

# Install paddleocr
echo "Installing paddleocr..."
pip install paddleocr

# Check if paddleocr installation was successful
if [ $? -ne 0 ]; then
    echo "❌ Failed to install paddleocr. Please check your internet connection and try again."
    exit 1
fi

# Verify paddlepaddle installation
echo "Verifying paddlepaddle installation..."
python -c "import paddle; paddle.utils.run_check()" > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ paddlepaddle verification failed. Installation may be incomplete."
    exit 1
fi

echo "==== Setup Complete ===="
echo "✅ paddlepaddle and paddleocr have been installed successfully for Apple Silicon."
echo "You can now run the Gradio demo with MPS acceleration using:"
echo "  ./run_gradio_with_gpu.sh"
echo
echo "If you encounter any issues, please refer to the GitHub issue:"
echo "  https://github.com/PaddlePaddle/PaddleOCR/issues/11706" 