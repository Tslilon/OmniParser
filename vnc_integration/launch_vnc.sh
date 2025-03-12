#!/bin/bash

# Get the VM address from command line argument
if [ -z "$1" ]; then
  echo "Usage: $0 <VM_IP>:<API_PORT>"
  echo "Example: $0 10.211.55.3:5000"
  exit 1
fi

# Parse the VM IP and API port
VM_ADDRESS=$1
VM_IP=$(echo $VM_ADDRESS | cut -d':' -f1)
API_PORT=$(echo $VM_ADDRESS | cut -d':' -f2)
VNC_PORT=8006

echo "======================================================"
echo "Standalone VNC Integration Launcher"
echo "======================================================"
echo "Windows VM IP: $VM_IP"
echo "API Port: $API_PORT"
echo "VNC Port: $VNC_PORT"
echo "======================================================"

# Check if VM is reachable
ping -c 1 $VM_IP > /dev/null
if [ $? -ne 0 ]; then
  echo "ERROR: Cannot reach Windows VM at $VM_IP"
  echo "Please ensure the VM is running and reachable from this machine."
  exit 1
fi

# Check if API is accessible
curl -s "http://$VM_IP:$API_PORT/probe" > /dev/null
if [ $? -ne 0 ]; then
  echo "WARNING: API is not responding at http://$VM_IP:$API_PORT/probe"
  echo "Make sure fix_omniparser.bat is running on the Windows VM."
fi

# Check if VNC port is accessible
nc -z -w 2 $VM_IP $VNC_PORT > /dev/null
if [ $? -ne 0 ]; then
  echo "WARNING: VNC service is not responding at $VM_IP:$VNC_PORT"
  echo "Make sure fix_omniparser.bat is running on the Windows VM."
fi

echo "Starting Standalone VNC Viewer..."
echo "You can access the VNC interface at http://localhost:7860"
echo ""

# Start the standalone application with the VM parameters (on port 7860 to avoid conflict with OmniTool)
cd "$(dirname "$0")"
python omniparser_app.py --vm-ip=$VM_IP --api-port=$API_PORT --vnc-port=$VNC_PORT 