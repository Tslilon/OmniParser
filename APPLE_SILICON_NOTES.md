# OmniParser on Apple Silicon - Implementation Notes

## Background

OmniParser uses several ML models for parsing screenshots:

1. **Icon Detection Model** (YOLO-based model) - Identifies UI elements and icons
2. **Florence Caption Model** - Provides semantic understanding of detected UI elements 
3. **OCR Engine** - For text recognition (PaddleOCR or EasyOCR)

## Issues on Apple Silicon

When running on Apple Silicon Macs (M1/M2/M3), there are two main issues:

1. **PaddleOCR Segmentation Faults**: The most critical issue is that PaddleOCR causes segmentation faults when used within OmniParser on Apple Silicon, even with the nightly build version that uses Apple's BLAS implementation.

2. **Metal Performance Shaders (MPS)**: To get optimal performance, the ML models should use Metal Performance Shaders.

## Our Solution

We addressed these issues with the following changes:

1. **Using EasyOCR Instead of PaddleOCR**:
   - Modified `util/omniparser.py` to use EasyOCR instead of PaddleOCR
   - This change is implemented by setting `use_paddleocr=False` in the check_ocr_box call
   - EasyOCR provides sufficient text recognition capabilities without the stability issues

2. **Enabling MPS Acceleration**:
   - Set the `OMNIPARSER_DEVICE` environment variable to "mps"
   - This enables Metal Performance Shaders for PyTorch operations

3. **Custom Launch Script**:
   - Created `run_omniparser_ml.sh` which correctly configures and launches both the server and UI
   - This script bypasses issues with the original setup scripts on Apple Silicon

## Usage

To run OmniParser with ML capabilities on Apple Silicon:

```bash
# Simple usage with default Windows VM address
./run_omniparser_ml.sh

# Specify custom Windows VM address
./run_omniparser_ml.sh 192.168.1.100:5000
```

## Performance Notes

- **Icon Detection**: Runs well on MPS
- **Florence Caption Model**: Benefits from MPS acceleration
- **Text Recognition**: Uses EasyOCR (CPU-based) instead of GPU-accelerated PaddleOCR, but performance is sufficient

## Files Modified

- `util/omniparser.py`: Changed to use EasyOCR instead of PaddleOCR
- `debug_server.py`: FastAPI server with proper error handling
- `run_omniparser_ml.sh`: Launcher script that ties everything together

## Future Improvements

If PaddleOCR fixes their segmentation issues on Apple Silicon in the future, the code could be modified to use it again for better OCR performance. 