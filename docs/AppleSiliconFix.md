# PaddleOCR Fix for Apple Silicon Macs

## Issue

PaddleOCR has a known issue on Apple Silicon Macs (M1, M2, M3) where the process hangs indefinitely when trying to run OCR operations. This issue has been reported in the [PaddleOCR GitHub repository](https://github.com/PaddlePaddle/PaddleOCR/issues/11706) and affects multiple versions of PaddlePaddle and PaddleOCR.

The core problem appears to be that the standard PaddlePaddle package uses OpenBLAS libraries that are incompatible with Apple Silicon architecture. When PaddleOCR attempts to run inference, it gets stuck in a computational routine related to the BLAS library.

## Solution

The solution is to use a development version of PaddlePaddle that has been built with proper support for Apple Silicon. This version uses Apple's own BLAS implementation instead of OpenBLAS, which allows it to run properly on M1, M2, and M3 Macs.

We've provided a setup script (`setup_apple_silicon.sh`) that:

1. Uninstalls any existing PaddlePaddle and PaddleOCR packages
2. Installs the development version of PaddlePaddle that supports Apple Silicon
3. Installs a compatible version of PaddleOCR
4. Verifies the installation to ensure it works correctly

### Manual Installation Steps

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

After installing the fixed version, you can run the Gradio demo with GPU acceleration (MPS) using the provided script:

```bash
./run_gradio_with_gpu.sh
```

This script sets the `OMNIPARSER_DEVICE` environment variable to `mps`, which tells OmniParser to use Metal Performance Shaders for GPU acceleration wherever possible.

## Performance

With this fix applied, PaddleOCR operations that previously would hang indefinitely now complete in a matter of milliseconds. Our testing showed OCR operations on a simple image completing in less than 100ms.

## Technical Details

This issue affects PaddlePaddle versions 2.4.x, 2.5.x, and 2.6.x when running on Apple Silicon architecture. The development version we're using has PaddlePaddle maintainers' improvements to use Apple's Accelerate framework and BLAS libraries, which properly support the ARM64 architecture of Apple Silicon.

The main change is in how matrix operations are handled during inference. The PaddlePaddle maintainer jzhang533 figured out how to use Apple's BLAS library in place of OpenBLAS, which resolved the hanging issue (see [PR #64408](https://github.com/PaddlePaddle/Paddle/pull/64408)).

## Troubleshooting

If you still experience issues after applying this fix:

1. Verify that you're running an arm64 version of Python:
   ```bash
   python -c "import platform; print(platform.machine())"
   ```
   This should output `arm64`.

2. Confirm that PaddlePaddle is using the correct device:
   ```bash
   python -c "import paddle; print(paddle.device.get_device())"
   ```

3. Check for any error messages during the import of paddle or paddleocr packages.

If problems persist, please open an issue on the [OmniParser GitHub repository](https://github.com/microsoft/OmniParser/issues) with details about your environment and the specific error you're encountering. 