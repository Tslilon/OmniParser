# Getting Started with OmniParser and OmniTool

This guide will walk you through setting up and running OmniParser and OmniTool to control a Windows 11 virtual machine using natural language commands.

## Prerequisites

- MacOS host with Apple Silicon (for MPS acceleration) or Intel processor
- Parallels Desktop with Windows 11 VM installed
- Python 3.12 installed on both Mac and Windows
- Required model weights downloaded (see main README.md)

## Quick Start with Setup Scripts

We provide convenience scripts for both Windows and Mac that automate most of the setup process:

1. **On Windows VM**: Run the PowerShell script
2. **On Mac**: Run the bash script with the VM's IP address
3. Start using OmniTool through the Gradio interface

## Detailed Setup Instructions

### 1. Setting Up the Windows VM Server

First, you need to start the server on your Windows 11 VM that will receive commands from the Mac host:

1. Open your Windows 11 VM in Parallels
2. Find the VM's IP address:
   - Open PowerShell and run `ipconfig`
   - Look for "IPv4 Address" under "Ethernet adapter" (typically 10.211.55.X)
   - Note this address for use on the Mac side

3. **Method 1: Using the Setup Script (Recommended)**
   ```powershell
   # Download the repository to your VM or copy the script
   # Navigate to the script location
   # Run the script as Administrator
   .\windows_setup.ps1
   ```

4. **Method 2: Manual Setup**
   - Ensure the `C:\omniserver` directory exists:
   ```powershell
   New-Item -ItemType Directory -Force -Path "C:\omniserver"
   ```
   
   - Copy these files from your Mac repository to the Windows VM:
     - `omnitool/omnibox/vm/win11setup/setupscripts/server/main.py` → `C:\omniserver\main.py`
     - Any other required server files
   
   - Install required Python packages on Windows:
   ```powershell
   pip install flask pyautogui pillow
   ```
   
   - Start the server:
   ```powershell
   cd C:\omniserver
   python main.py --port 5000
   ```

5. Verify the server is running by opening a browser on the Windows VM and navigating to `http://localhost:5001/probe/`

### 2. Starting OmniParser on Mac

#### Basic Gradio Demo (Without VM Control)

If you just want to test OmniParser's screenshot parsing capabilities (without VM control):

```bash
# Navigate to the project root
cd /path/to/OmniParser

# Activate your Python environment (if using conda/venv)
conda activate omni  # or source venv/bin/activate

# Run the gradio demo
python gradio_demo.py
```

This will start a simple Gradio web interface on http://localhost:7860 where you can upload screenshots for parsing.

#### Full OmniTool with Windows VM Control

To use OmniTool with your Windows VM for complete natural language control:

1. **Method 1: Using the Setup Script (Recommended)**
   ```bash
   # Navigate to the project root
   cd /path/to/OmniParser
   
   # Make the script executable (if you haven't already)
   chmod +x start_hybrid_setup.sh
   
   # Start with your Windows VM's IP address
   ./start_hybrid_setup.sh 10.211.55.3:5000
   ```

2. **Method 2: Manual Setup**
   
   a. Start the OmniParser server:
   ```bash
   # Set environment variable for MPS acceleration (on Apple Silicon)
   export OMNIPARSER_DEVICE="mps"
   
   # Start the OmniParser server
   python -m omnitool.omniparserserver.omniparserserver \
     --device $OMNIPARSER_DEVICE \
     --som_model_path "$(pwd)/weights/icon_detect/model.pt" \
     --caption_model_path "$(pwd)/weights/icon_caption_florence"
   ```
   
   b. In a new terminal, start the Gradio UI:
   ```bash
   cd /path/to/OmniParser/omnitool/gradio
   python app.py --windows_host_url 10.211.55.3:5000 --omniparser_server_url localhost:8000
   ```

3. Access the OmniTool interface at http://localhost:7888 in your browser

## Using OmniTool

The full OmniTool interface offers:

1. **Text Input Area**: Enter natural language commands to control the Windows VM
2. **Model Selection**: Choose from different LLMs:
   - OpenAI models (gpt-4o, o1, o3-mini)
   - Groq models (R1)
   - DashScope models (qwen2.5vl)
   - Anthropic models (claude-3-5-sonnet)
3. **Screenshot Preview**: Shows the current Windows VM screen with element highlighting
4. **Response Area**: Displays the AI assistant's responses and actions

### Sample Commands

Try these examples to get started:
- "Open Notepad and type 'Hello World'"
- "Open the Start menu and search for Settings"
- "Open the browser and go to bing.com"
- "Find and click on the Recycle Bin on the desktop"

## Troubleshooting

### Windows VM Connection Issues

- Verify the Windows server is running with `curl http://10.211.55.3:5000/probe/`
- Check that the IP address is correct in your OmniTool startup command
- Ensure no firewall is blocking port 5000 on the Windows VM

### OmniParser ML Model Issues

If you encounter issues with the ML models:

```bash
# Use the simplified OmniParser (no ML models, for testing)
./start_hybrid_setup.sh 10.211.55.3:5000 localhost:8000 simple
```

### Mac GPU Acceleration Issues

If MPS is not working properly:

```bash
# Run our test script to check MPS availability
python test_mps_support.py

# Force CPU mode if MPS is unavailable
export OMNIPARSER_DEVICE="cpu"
```

## Additional Resources

- [OmniParser Main Documentation](https://microsoft.github.io/OmniParser/)
- [Video Demo of OmniTool](https://1drv.ms/v/c/650b027c18d5a573/EehZ7RzY69ZHn-MeQHrnnR4BCj3by-cLLpUVlxMjF4O65Q?e=8LxMgX)
- [OmniParser GitHub Repository](https://github.com/microsoft/OmniParser) 