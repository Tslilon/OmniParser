# PaddleOCR Fix for Apple Silicon Macs

## Issue

PaddleOCR has a known issue on Apple Silicon Macs (M1, M2, M3) where the process hangs indefinitely or causes segmentation faults when trying to run OCR operations. This issue has been reported in the [PaddleOCR GitHub repository](https://github.com/PaddlePaddle/PaddleOCR/issues/11706) and affects multiple versions of PaddlePaddle and PaddleOCR.

The core problem appears to be that the standard PaddlePaddle package uses OpenBLAS libraries that are incompatible with Apple Silicon architecture. When PaddleOCR attempts to run inference, it gets stuck in a computational routine related to the BLAS library.

## Solution Options

### Option 1: Switch to EasyOCR (Recommended)

We've found that the most reliable solution is to bypass PaddleOCR entirely and use EasyOCR instead:

1. This is automatically configured in our `run_omniparser_ml.sh` script
2. No additional setup is required
3. See `APPLE_SILICON_NOTES.md` in the project root for detailed information

```bash
# Run OmniParser with EasyOCR and MPS acceleration
./run_omniparser_ml.sh
```

### Option 2: Attempt PaddleOCR Fix

If you prefer to try using PaddleOCR, we've provided a setup script that attempts to fix the compatibility issues:

1. Uninstalls any existing PaddlePaddle and PaddleOCR packages
2. Installs the development version of PaddlePaddle that supports Apple Silicon
3. Installs a compatible version of PaddleOCR
4. Verifies the installation to ensure it works correctly

To use this approach:

```bash
./setup_apple_silicon.sh
```

#### Manual Installation Steps

If you prefer to perform the installation manually, follow these steps:

1. Uninstall existing paddle packages:
   ```bash
   pip uninstall -y paddlepaddle paddleocr
   ```

2. Install the development version of paddlepaddle:
   ```bash
   python -m pip install paddlepaddle==0.0.0 -f https://www.paddlepaddle.org.cn/whl/mac/cpu/develop.html
   ```

3. Install paddleocr:
   ```bash
   pip install paddleocr
   ```

4. Verify the installation:
   ```bash
   python -c "import paddle; paddle.utils.run_check()"
   ```

### Running OmniParser with GPU Acceleration

Regardless of which OCR solution you choose, you'll want to enable MPS acceleration for optimal performance:

```bash
# Set environment variable for MPS acceleration
export OMNIPARSER_DEVICE="mps"
```

This tells OmniParser to use Metal Performance Shaders for GPU acceleration wherever possible.

## Performance Comparison

- **EasyOCR**: Consistent and stable performance on Apple Silicon, slightly slower for complex text
- **PaddleOCR (when working)**: Potentially faster OCR operations, but with stability issues

Our testing shows that EasyOCR provides sufficient performance for most use cases while avoiding the stability issues of PaddleOCR on Apple Silicon.

## Technical Details

This issue affects PaddlePaddle versions 2.4.x, 2.5.x, and 2.6.x when running on Apple Silicon architecture. The development version uses PaddlePaddle maintainers' improvements to use Apple's Accelerate framework and BLAS libraries, which should better support the ARM64 architecture of Apple Silicon.

However, even with the development version, we've observed segmentation faults within OmniParser's context, which is why we recommend the EasyOCR approach.

## Troubleshooting

If you still experience issues after applying either fix:

1. Verify that you're running an arm64 version of Python:
   ```bash
   python -c "import platform; print(platform.machine())"
   ```
   This should output `arm64`.

2. Confirm that PyTorch is using the correct device:
   ```bash
   python -c "import torch; print(torch.backends.mps.is_available())"
   ```

3. Check for any error messages during import of packages.

If problems persist, please open an issue on the [OmniParser GitHub repository](https://github.com/microsoft/OmniParser/issues) with details about your environment and the specific error you're encountering. 