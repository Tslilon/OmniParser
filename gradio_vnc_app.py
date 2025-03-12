import gradio as gr
import os
import socket
import requests

# Use the correct VM IP address
VM_IP = "10.211.55.3"  # Windows VM IP address

# HTML content with embedded NoVNC iframe
html_content = f"""
<div style="width:100%; height:100%;">
    <h2>OmniParser VNC Viewer</h2>
    <div style="width:100%; height:800px; border:1px solid #ddd;">
        <iframe 
            src="http://{VM_IP}:8006/vnc.html?autoconnect=true&resize=scale&reconnect=true&password=1234" 
            style="width:100%; height:100%; border:none;"
            allow="clipboard-read; clipboard-write"
        ></iframe>
    </div>
    <p>If the VNC viewer doesn't load, please ensure the VNC server and websockify are running.</p>
    <p>Direct link: <a href="http://{VM_IP}:8006/vnc.html?autoconnect=true&resize=scale&reconnect=true&password=1234" target="_blank">Open NoVNC in new window</a></p>
</div>
"""

# Function to check service status
def check_service_status():
    status = []
    
    # Check API
    try:
        response = requests.get(f"http://{VM_IP}:5000/probe", timeout=3)
        status.append(f"API (port 5000): ✅ Connected - Status {response.status_code}")
    except Exception as e:
        status.append(f"API (port 5000): ❌ Failed - {str(e)}")
    
    # Check NoVNC
    try:
        response = requests.get(f"http://{VM_IP}:8006", timeout=3)
        status.append(f"NoVNC (port 8006): ✅ Connected - Status {response.status_code}")
    except Exception as e:
        status.append(f"NoVNC (port 8006): ❌ Failed - {str(e)}")
    
    # Check VNC directly
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        result = s.connect_ex((VM_IP, 5900))
        if result == 0:
            status.append(f"VNC Server (port 5900): ✅ Port is open")
        else:
            status.append(f"VNC Server (port 5900): ❌ Port is closed (error {result})")
        s.close()
    except Exception as e:
        status.append(f"VNC Server check failed: {str(e)}")
    
    return "\n".join(status)

# Create Gradio interface
def create_ui():
    with gr.Blocks(css="footer {visibility: hidden}") as demo:
        gr.HTML(html_content)
        
        # Controls for VNC interaction
        with gr.Row():
            refresh_btn = gr.Button("Refresh VNC Viewer")
            check_btn = gr.Button("Check Services")
        
        status_msg = gr.Textbox(label="Status", value=f"VNC viewer loaded - Using VM IP: {VM_IP}", lines=4)
        
        # Button handlers
        refresh_btn.click(
            fn=lambda: f"VNC viewer refreshed - Using VM IP: {VM_IP}", 
            outputs=[status_msg]
        )
        
        check_btn.click(
            fn=check_service_status,
            outputs=[status_msg]
        )
    
    return demo

if __name__ == "__main__":
    app = create_ui()
    app.launch(share=True)  # share=True creates a public URL 