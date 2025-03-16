# OmniParser: Screen Parsing tool for Pure Vision Based GUI Agent

<p align="center">
  <img src="imgs/logo.png" alt="Logo">
</p>

[![arXiv](https://img.shields.io/badge/Paper-green)](https://arxiv.org/abs/2408.00203)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

📢 [[Project Page](https://microsoft.github.io/OmniParser/)] [[V2 Blog Post](https://www.microsoft.com/en-us/research/articles/omniparser-v2-turning-any-llm-into-a-computer-use-agent/)] [[Models V2](https://huggingface.co/microsoft/OmniParser-v2.0)] [[Models V1.5](https://huggingface.co/microsoft/OmniParser)] [[HuggingFace Space Demo](https://huggingface.co/spaces/microsoft/OmniParser-v2)]

**OmniParser** is a comprehensive method for parsing user interface screenshots into structured and easy-to-understand elements, which significantly enhances the ability of GPT-4V to generate actions that can be accurately grounded in the corresponding regions of the interface. 

## News
- [2025/4] Added Mac GPU support via MPS (Metal Performance Shaders) and cross-platform setup scripts.
- [2025/3] We are gradually adding multi agents orchestration and improving user interface in OmniTool for better experience.
- [2025/2] We release OmniParser V2 [checkpoints](https://huggingface.co/microsoft/OmniParser-v2.0). [Watch Video](https://1drv.ms/v/c/650b027c18d5a573/EWXbVESKWo9Buu6OYCwg06wBeoM97C6EOTG6RjvWLEN1Qg?e=alnHGC)
- [2025/2] We introduce OmniTool: Control a Windows 11 VM with OmniParser + your vision model of choice. OmniTool supports out of the box the following large language models - OpenAI (4o/o1/o3-mini), DeepSeek (R1), Qwen (2.5VL) or Anthropic Computer Use. [Watch Video](https://1drv.ms/v/c/650b027c18d5a573/EehZ7RzY69ZHn-MeQHrnnR4BCj3by-cLLpUVlxMjF4O65Q?e=8LxMgX)
- [2025/1] V2 is coming. We achieve new state of the art results 39.5% on the new grounding benchmark [Screen Spot Pro](https://github.com/likaixin2000/ScreenSpot-Pro-GUI-Grounding/tree/main) with OmniParser v2 (will be released soon)! Read more details [here](https://github.com/microsoft/OmniParser/tree/master/docs/Evaluation.md).
- [2024/11] We release an updated version, OmniParser V1.5 which features 1) more fine grained/small icon detection, 2) prediction of whether each screen element is interactable or not. Examples in the demo.ipynb. 
- [2024/10] OmniParser was the #1 trending model on huggingface model hub (starting 10/29/2024). 
- [2024/10] Feel free to checkout our demo on [huggingface space](https://huggingface.co/spaces/microsoft/OmniParser)! (stay tuned for OmniParser + Claude Computer Use)
- [2024/10] Both Interactive Region Detection Model and Icon functional description model are released! [Hugginface models](https://huggingface.co/microsoft/OmniParser)
- [2024/09] OmniParser achieves the best performance on [Windows Agent Arena](https://microsoft.github.io/WindowsAgentArena/)! 

## Install 
First clone the repo, and then install environment:
```python
cd OmniParser
conda create -n "omni" python==3.12
conda activate omni
pip install -r requirements.txt
```

### Special Instructions for Apple Silicon Macs (M1/M2/M3)

If you're using an Apple Silicon Mac, PaddleOCR requires a special installation to avoid hanging issues. We've provided a setup script to make this process easy:

```bash
# Run the special setup script for Apple Silicon
./setup_apple_silicon.sh

# Afterwards, you can use GPU acceleration with MPS
./run_gradio_with_gpu.sh
```

This special setup installs a development version of PaddlePaddle that properly supports Apple Silicon and fixes a known issue where PaddleOCR would hang indefinitely on M1/M2/M3 Macs.

### Model Weights

Ensure you have the V2 weights downloaded in weights folder (ensure caption weights folder is called icon_caption_florence). If not download them with:
```
   # download the model checkpoints to local directory OmniParser/weights/
   for f in icon_detect/{train_args.yaml,model.pt,model.yaml} icon_caption/{config.json,generation_config.json,model.safetensors}; do huggingface-cli download microsoft/OmniParser-v2.0 "$f" --local-dir weights; done
   mv weights/icon_caption weights/icon_caption_florence
```

<!-- ## [deprecated]
Then download the model ckpts files in: https://huggingface.co/microsoft/OmniParser, and put them under weights/, default folder structure is: weights/icon_detect, weights/icon_caption_florence, weights/icon_caption_blip2. 

For v1: 
convert the safetensor to .pt file. 
```python
python weights/convert_safetensor_to_pt.py

For v1.5: 
download 'model_v1_5.pt' from https://huggingface.co/microsoft/OmniParser/tree/main/icon_detect_v1_5, make a new dir: weights/icon_detect_v1_5, and put it inside the folder. No weight conversion is needed. 
``` -->

## Mac GPU Support

OmniParser now supports accelerated processing on Apple Silicon Macs using Metal Performance Shaders (MPS). To enable MPS support:

1. Set the environment variable before running:
   ```bash
   export OMNIPARSER_DEVICE="mps"
   ```

2. Or use the provided setup script which automatically configures MPS:
   ```bash
   chmod +x run_omniparser_ml.sh
   ./run_omniparser_ml.sh
   ```

For detailed instructions on setting up and running OmniParser with Windows VM integration, see [Getting Started Guide](GETTING_STARTED.md).

## Cross-platform Setup

### Mac/Unix Setup
Use the included setup script to start all necessary services:

```bash
# Make the script executable
chmod +x run_omniparser_ml.sh

# Start with default settings (Windows VM at 10.211.55.3:5000)
./run_omniparser_ml.sh

# Or specify custom Windows VM URL
./run_omniparser_ml.sh 192.168.1.100:5000
```

### Windows VM Setup
On your Windows VM, use the PowerShell script to set up the server:

```powershell
# Run the setup script as administrator
.\windows_setup.ps1
```

This will start the Flask server on port 5000 and display the VM's IP address, which you'll need to configure on the Mac side.

## Examples:
We put together a few simple examples in the demo.ipynb. 

## Gradio Demo
To run gradio demo, simply run:
```python
python gradio_demo.py
```

## Model Weights License
For the model checkpoints on huggingface model hub, please note that icon_detect model is under AGPL license since it is a license inherited from the original yolo model. And icon_caption_blip2 & icon_caption_florence is under MIT license. Please refer to the LICENSE file in the folder of each model: https://huggingface.co/microsoft/OmniParser.

## 📚 Citation
Our technical report can be found [here](https://arxiv.org/abs/2408.00203).
If you find our work useful, please consider citing our work:
```
@misc{lu2024omniparserpurevisionbased,
      title={OmniParser for Pure Vision Based GUI Agent}, 
      author={Yadong Lu and Jianwei Yang and Yelong Shen and Ahmed Awadallah},
      year={2024},
      eprint={2408.00203},
      archivePrefix={arXiv},
      primaryClass={cs.CV},
      url={https://arxiv.org/abs/2408.00203}, 
}
```

## Apple Silicon Compatibility

When running OmniParser on Apple Silicon Macs (M1/M2/M3), there are specific considerations to ensure optimal performance:

### Key Features

1. **EasyOCR Integration**: 
   - We've integrated EasyOCR as an alternative to PaddleOCR to avoid segmentation faults on Apple Silicon
   - This provides stable OCR capabilities without compatibility issues

2. **MPS Acceleration**:
   - Metal Performance Shaders (MPS) acceleration for PyTorch is enabled by default
   - This provides GPU acceleration for the icon detection and caption models

3. **Streamlined Startup**:
   - A dedicated script `run_omniparser_ml.sh` handles all the setup for Apple Silicon Macs
   - This script automatically configures the environment and launches both the server and UI

### Running on Apple Silicon

To run OmniParser with full ML capabilities on Apple Silicon:

```bash
# Make the script executable
chmod +x run_omniparser_ml.sh

# Run with default Windows VM address (10.211.55.3:5000)
./run_omniparser_ml.sh

# Or specify a custom Windows VM address
./run_omniparser_ml.sh 192.168.1.100:5000
```

This script:
- Configures the environment for MPS acceleration
- Launches the debug server with EasyOCR instead of PaddleOCR
- Starts the Gradio UI and connects it to your Windows VM
- Provides clean shutdown with Ctrl+C

### Documentation

For more detailed information:
- See [APPLE_SILICON_NOTES.md](APPLE_SILICON_NOTES.md) for implementation details
- See [docs/AppleSiliconFix.md](docs/AppleSiliconFix.md) for PaddleOCR-specific fixes (if needed)
- See [GETTING_STARTED.md](GETTING_STARTED.md) for general setup instructions

## Documentation

- [Getting Started](GETTING_STARTED.md) - Installation and basic usage
- [Apple Silicon Notes](APPLE_SILICON_NOTES.md) - Specific notes for M1/M2 Macs
- [Testing and Performance](TESTING_AND_PERFORMANCE.md) - Testing tools and performance optimization
- [Security](SECURITY.md) - Security guidelines and best practices
