import gradio as gr
import argparse
import requests
import socket
import time
import os
import json
from pathlib import Path

# Parse command-line arguments
parser = argparse.ArgumentParser(description='OmniParser with VNC Integration')
parser.add_argument('--vm-ip', type=str, required=True, help='Windows VM IP address')
parser.add_argument('--api-port', type=int, default=5000, help='Flask API port')
parser.add_argument('--vnc-port', type=int, default=8006, help='NoVNC port')
args = parser.parse_args()

# Configuration
VM_IP = args.vm_ip
API_PORT = args.api_port
VNC_PORT = args.vnc_port
API_URL = f"http://{VM_IP}:{API_PORT}"
VNC_URL = f"http://{VM_IP}:{VNC_PORT}/vnc.html?autoconnect=true&resize=scale&reconnect=true&password=1234&view_only=1"

# App state
APP_STATE = {
    "vm_status": "Unknown",
    "api_status": "Unknown",
    "vnc_status": "Unknown",
    "parsing_status": "Ready",
    "parsed_document": None
}

# Validation: Check if services are available
def check_vm_services():
    results = []
    
    # Check API 
    try:
        response = requests.get(f"{API_URL}/probe", timeout=3)
        APP_STATE["api_status"] = "Online"
        results.append(f"✅ API is accessible at {API_URL}/probe")
    except Exception as e:
        APP_STATE["api_status"] = "Offline"
        results.append(f"❌ API is not accessible: {str(e)}")
    
    # Check VNC/Websockify
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((VM_IP, VNC_PORT))
        if result == 0:
            APP_STATE["vnc_status"] = "Online"
            results.append(f"✅ VNC service is accessible on port {VNC_PORT}")
        else:
            APP_STATE["vnc_status"] = "Offline"
            results.append(f"❌ VNC service is not accessible on port {VNC_PORT}")
        s.close()
    except Exception as e:
        APP_STATE["vnc_status"] = "Error"
        results.append(f"❌ Error checking VNC service: {str(e)}")
    
    # Check if base VM is reachable
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((VM_IP, 5900))  # VNC Server port
        if result == 0:
            APP_STATE["vm_status"] = "Online"
            results.append(f"✅ VM is running and VNC Server is accessible")
        else:
            APP_STATE["vm_status"] = "Partial"
            results.append(f"⚠️ VM is reachable but VNC Server is not responding on port 5900")
        s.close()
    except Exception as e:
        APP_STATE["vm_status"] = "Offline"
        results.append(f"❌ Cannot connect to VM: {str(e)}")
    
    return "\n".join(results)

# OmniParser functions (placeholder - integrate with your actual parser logic)
def parse_document(file_path):
    """Parse document using Windows VM API"""
    try:
        # Example API call to parse document - adapt to your actual API
        with open(file_path.name, "rb") as f:
            files = {"file": f}
            response = requests.post(f"{API_URL}/parse", files=files, timeout=30)
        
        if response.status_code == 200:
            APP_STATE["parsing_status"] = "Success"
            APP_STATE["parsed_document"] = response.json()
            return "Document parsed successfully", response.json()
        else:
            APP_STATE["parsing_status"] = "Failed"
            return f"Error parsing document: Status {response.status_code}", None
            
    except Exception as e:
        APP_STATE["parsing_status"] = "Error"
        return f"Error connecting to parser API: {str(e)}", None

# Create status display string
def get_status_display():
    vm_status = "🟢" if APP_STATE["vm_status"] == "Online" else "🔴"
    api_status = "🟢" if APP_STATE["api_status"] == "Online" else "🔴"
    vnc_status = "🟢" if APP_STATE["vnc_status"] == "Online" else "🔴"
    
    return f"""
    Windows VM: {vm_status} {APP_STATE["vm_status"]}  
    API Service: {api_status} {APP_STATE["api_status"]}
    VNC Viewer: {vnc_status} {APP_STATE["vnc_status"]}
    """

# NoVNC viewer HTML component
vnc_html = f"""
<div style="width:100%; height:100%;">
    <h2>Windows VM Remote Control</h2>
    <div style="width:100%; height:600px; border:1px solid #ddd; margin-bottom: 10px;">
        <iframe 
            src="{VNC_URL}" 
            style="width:100%; height:100%; border:none;"
            allow="clipboard-read; clipboard-write"
        ></iframe>
    </div>
    <p>
        <strong>Direct URL:</strong> 
        <a href="{VNC_URL}" target="_blank">Open in new window</a>
    </p>
</div>
"""

# Initial service check
initial_status = check_vm_services()
print("Initial service check:")
print(initial_status)

# Build Gradio interface
def build_interface():
    with gr.Blocks(title="OmniParser", theme=gr.themes.Base()) as demo:
        gr.Markdown("# OmniParser - Document Processing System")
        
        with gr.Row():
            with gr.Column(scale=2):
                gr.Markdown(f"Connected to Windows VM: **{VM_IP}**")
            with gr.Column(scale=1):
                status_display = gr.Markdown(get_status_display())
                refresh_btn = gr.Button("Refresh Status")

        # Create tabs for different functionality
        with gr.Tabs():
            # Document Processing Tab
            with gr.TabItem("Document Processing"):
                with gr.Row():
                    with gr.Column():
                        file_input = gr.File(label="Upload Document")
                        parse_btn = gr.Button("Parse Document", variant="primary")
                        status_output = gr.Textbox(label="Status", value="Ready")
                    
                    with gr.Column():
                        json_output = gr.JSON(label="Parsing Results")
            
            # VM Control Tab with NoVNC
            with gr.TabItem("Windows VM Control"):
                with gr.Row():
                    with gr.Column():
                        gr.HTML(vnc_html)
                
                with gr.Row():
                    check_services_btn = gr.Button("Check Services")
                    service_status = gr.Textbox(
                        label="Service Status", 
                        value=initial_status,
                        lines=6
                    )
            
            # Diagnostics Tab
            with gr.TabItem("Diagnostics"):
                with gr.Row():
                    diag_output = gr.Textbox(
                        label="System Diagnostics",
                        value="Click 'Run Diagnostics' to check system status",
                        lines=15
                    )
                    
                with gr.Row():
                    diag_btn = gr.Button("Run Diagnostics")

        # Connect component functions
        refresh_btn.click(
            fn=lambda: gr.Markdown.update(get_status_display()),
            outputs=[status_display]
        )
        
        check_services_btn.click(
            fn=check_vm_services,
            outputs=[service_status]
        )
        
        parse_btn.click(
            fn=parse_document,
            inputs=[file_input],
            outputs=[status_output, json_output]
        )
        
        # Diagnostics function
        def run_diagnostics():
            results = []
            results.append(f"OmniParser Diagnostics Report")
            results.append(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
            results.append(f"")
            results.append(f"Windows VM: {VM_IP}")
            results.append(f"API Port: {API_PORT}")
            results.append(f"VNC Port: {VNC_PORT}")
            results.append(f"")
            
            # Service status
            results.append(f"Service Status:")
            results.append(f"- VM Status: {APP_STATE['vm_status']}")
            results.append(f"- API Status: {APP_STATE['api_status']}")
            results.append(f"- VNC Status: {APP_STATE['vnc_status']}")
            results.append(f"- Parser Status: {APP_STATE['parsing_status']}")
            results.append(f"")
            
            # Connection test
            try:
                response = requests.get(f"{API_URL}/probe", timeout=3)
                results.append(f"API Connection: Success (Status {response.status_code})")
            except Exception as e:
                results.append(f"API Connection: Failed - {str(e)}")
            
            # Environment info
            results.append(f"")
            results.append(f"System Information:")
            results.append(f"- Python: {os.sys.version.split()[0]}")
            results.append(f"- OS: {os.name}")
            results.append(f"- Gradio: {gr.__version__}")
            
            return "\n".join(results)
        
        diag_btn.click(
            fn=run_diagnostics,
            outputs=[diag_output]
        )
                
    return demo

# Start the application
if __name__ == "__main__":
    app = build_interface()
    app.launch(server_name="0.0.0.0", server_port=7860, share=False)
    print(f"Application started. Access at http://0.0.0.0:7860") 