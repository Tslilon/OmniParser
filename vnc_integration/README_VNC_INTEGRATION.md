# OmniParser VNC Integration

This guide explains how to use the integrated VNC viewer in the OmniParser application to directly interact with the Windows VM.

## Prerequisites

1. Windows VM with:
   - TightVNC Server running on port 5900
   - Flask API running on port 5000
   - NoVNC/Websockify running on port 8006

2. Mac with:
   - Python 3.6+
   - Gradio installed (`pip install gradio`)
   - Required dependencies (`pip install requests`)

## Setup Instructions

### 1. On Windows VM

Make sure to run the `run.bat` script first on the vm:

```bash
C:\omniserver\run.bat
```

This script will:
- Set up the Flask API on port 5000
- Start the NoVNC/Websockify service on port 8006
- Ensure TightVNC is running

### 2. On Mac

1. Start the OmniParser with VNC integration:

```bash
./start_hybrid_setup.sh 10.211.55.3:5000
```

Replace `10.211.55.3` with your Windows VM IP address.

2. Access the OmniParser application at:
   - Local: http://localhost:7860
   - Public: The URL displayed in the terminal (if `share=True` is enabled)

## Using the VNC Integration

The OmniParser interface now includes a "Windows VM Control" tab that contains:

1. An embedded NoVNC viewer that allows you to directly interact with the Windows VM
2. Service status information and diagnostics
3. Direct link to open the VNC viewer in a separate browser tab

## Troubleshooting

If the VNC viewer is not loading:

1. Check the services on Windows VM:
   - Make sure TightVNC Server is running
   - Verify that websockify is running correctly on port 8006
   - Check if the Flask API is accessible at http://VM_IP:5000/probe

2. From the Mac, run the diagnostic tool:
   ```
   python test_connections.py
   ```

3. Check your network/firewall settings:
   - Ensure ports 5000, 5900, and 8006 are accessible from Mac to the Windows VM
   - Verify the VM's IP address is correct

## Architecture

```
┌────────────────┐                ┌────────────────┐
│                │                │                │
│   Mac (OSX)    │                │  Windows VM    │
│                │                │                │
│  OmniParser    │◄──API calls────┤  Flask API     │
│  Gradio UI     │    (5000)      │  (5000)        │
│                │                │                │
│  NoVNC Client  │◄──Websockify───┤  NoVNC Server  │
│  (in browser)  │    (8006)      │  (8006)        │
│                │                │                │
└────────────────┘                │  VNC Server    │
                                  │  (5900)        │
                                  │                │
                                  └────────────────┘
```

## Customization

To customize the integration, you can modify:

1. `omniparser_app.py` - Main application with VNC integration
2. `start_hybrid_setup.sh` - Startup script for the application

## Additional Notes

- The VNC password is set to "1234" by default
- All connections are unencrypted - use only in trusted networks
- For production use, consider adding proper authentication 