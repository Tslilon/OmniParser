import gradio as gr
import requests
import os
import time
import subprocess
import webbrowser
from threading import Thread

# Configuration - UPDATED with correct IP address
VM_IP = "10.211.55.3"  # Windows VM IP address
VNC_URL = f"http://{VM_IP}:8006/vnc.html?autoconnect=true&resize=scale&reconnect=true&password=1234&view_only=1"
API_URL = f"http://{VM_IP}:5000"
VNC_PASSWORD = "1234"  # This should match the VNC server password

# HTML content with embedded NoVNC iframe
html_content = f"""
<div style="width:100%; height:100%;">
    <h1>OmniParser Control Panel</h1>
    <div style="width:100%; height:600px; border:1px solid #ddd; margin-bottom: 20px;">
        <iframe 
            src="{VNC_URL}" 
            style="width:100%; height:100%; border:none;"
            allow="clipboard-read; clipboard-write"
        ></iframe>
    </div>
    <p>Use the controls below to interact with the Windows VM or check the API status.</p>
</div>
"""

# Check if API is running
def check_api_status():
    try:
        response = requests.get(f"{API_URL}/probe", timeout=5)
        if response.status_code == 200:
            return f"✅ API is running and accessible at {API_URL}/probe"
        else:
            return f"❌ API returned status code: {response.status_code}"
    except requests.exceptions.RequestException as e:
        return f"❌ Failed to connect to API: {str(e)}"

# Check if NoVNC is running
def check_vnc_status():
    try:
        # Just check if the websockify port is open
        response = requests.get(f"http://{VM_IP}:8006", timeout=5)
        return f"✅ VNC Websockify is running at {VM_IP}:8006"
    except requests.exceptions.RequestException as e:
        return f"❌ VNC Websockify is not accessible: {str(e)}"

# Additional diagnostic function
def run_diagnostics():
    results = []
    
    # Check API 
    try:
        response = requests.get(f"{API_URL}/probe", timeout=3)
        results.append(f"API (port 5000): ✅ Responded with status {response.status_code}")
    except Exception as e:
        results.append(f"API (port 5000): ❌ Connection error - {str(e)}")
    
    # Check NoVNC port
    try:
        response = requests.get(f"http://{VM_IP}:8006", timeout=3)
        results.append(f"NoVNC port 8006: ✅ Responded with status {response.status_code}")
    except Exception as e:
        results.append(f"NoVNC port 8006: ❌ Connection error - {str(e)}")
    
    # Check if VNC server is accessible directly
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((VM_IP, 5900))
        if result == 0:
            results.append(f"VNC Server (port 5900): ✅ Port is open")
        else:
            results.append(f"VNC Server (port 5900): ❌ Port is closed (error {result})")
        s.close()
    except Exception as e:
        results.append(f"VNC Server (port 5900): ❌ Check failed - {str(e)}")
    
    return "\n".join(results)

# Create Gradio interface
def create_ui():
    with gr.Blocks(theme=gr.themes.Base(), css="footer {visibility: hidden}") as demo:
        gr.HTML(html_content)
        
        with gr.Row():
            with gr.Column(scale=1):
                api_status_btn = gr.Button("Check API Status", variant="primary")
                vnc_status_btn = gr.Button("Check VNC Status", variant="primary")
                refresh_btn = gr.Button("Refresh View", variant="secondary")
                diag_btn = gr.Button("Run Full Diagnostics", variant="secondary")
            
            with gr.Column(scale=2):
                status_msg = gr.Textbox(
                    label="Status", 
                    value=f"Ready - Using VM IP: {VM_IP}", 
                    lines=5
                )
        
        # Connect buttons to functions
        api_status_btn.click(
            fn=check_api_status,
            outputs=[status_msg]
        )
        
        vnc_status_btn.click(
            fn=check_vnc_status,
            outputs=[status_msg]
        )
        
        diag_btn.click(
            fn=run_diagnostics,
            outputs=[status_msg]
        )
        
        refresh_btn.click(
            fn=lambda: f"View refreshed. VNC URL: {VNC_URL}",
            outputs=[status_msg]
        )
        
        # Add instructions
        with gr.Accordion("Instructions", open=False):
            gr.Markdown(f"""
            ### How to use this interface
            
            1. The VNC viewer above shows the Windows VM (IP: {VM_IP}) running OmniParser.
            2. You can interact with the VM directly through this interface.
            3. The VNC connection uses password: `1234`
            4. The Flask API running in the VM is accessible at {API_URL}/probe
            
            ### Troubleshooting
            
            - If the VNC viewer is not loading, check if the Windows VM is running.
            - Ensure the batch script `fix_omniparser.bat` is running on the Windows VM.
            - Click "Run Full Diagnostics" to check all connection points.
            - If the iframe doesn't load, try accessing the NoVNC directly at: {VNC_URL}
            """)
    
    return demo

# Open the VNC viewer in a browser if needed
def open_vnc_in_browser():
    time.sleep(2)  # Wait a bit for Gradio to start
    webbrowser.open(VNC_URL)

if __name__ == "__main__":
    app = create_ui()
    # Uncomment the next line to automatically open the VNC viewer in a browser
    # Thread(target=open_vnc_in_browser).start()
    app.launch(share=True)  # share=True creates a public URL for sharing 