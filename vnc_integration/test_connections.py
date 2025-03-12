import requests
import socket
import time
import webbrowser

# VM Configuration
VM_IP = "10.211.55.3"  # Windows VM IP address
API_PORT = 5000
NOVNC_PORT = 8006
VNC_PORT = 5900

def print_section(title):
    """Print a section header"""
    print("\n" + "="*50)
    print(f" {title}")
    print("="*50)

def test_socket_connection(ip, port, service_name):
    """Test if a TCP socket connection can be established"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(3)
        start_time = time.time()
        result = s.connect_ex((ip, port))
        elapsed = time.time() - start_time
        if result == 0:
            print(f"✅ {service_name} is ACCESSIBLE on {ip}:{port} ({elapsed:.2f}s)")
            s.close()
            return True
        else:
            print(f"❌ {service_name} is NOT ACCESSIBLE on {ip}:{port} - Error: {result} ({elapsed:.2f}s)")
            return False
    except Exception as e:
        print(f"❌ Error testing {service_name} on {ip}:{port} - {str(e)}")
        return False

def test_http_connection(url, service_name):
    """Test if an HTTP connection can be established"""
    try:
        start_time = time.time()
        response = requests.get(url, timeout=5)
        elapsed = time.time() - start_time
        print(f"✅ {service_name} is ACCESSIBLE at {url}")
        print(f"   Status: {response.status_code}, Time: {elapsed:.2f}s, Content Length: {len(response.content)} bytes")
        return True
    except requests.exceptions.RequestException as e:
        print(f"❌ {service_name} is NOT ACCESSIBLE at {url}")
        print(f"   Error: {str(e)}")
        return False

def main():
    print_section("CONNECTION TESTS")
    print(f"Testing connections to VM at {VM_IP}...")
    
    # Test direct socket connections first
    print_section("SOCKET CONNECTIONS")
    vnc_ok = test_socket_connection(VM_IP, VNC_PORT, "VNC Server")
    flask_ok = test_socket_connection(VM_IP, API_PORT, "Flask API")
    novnc_ok = test_socket_connection(VM_IP, NOVNC_PORT, "NoVNC/Websockify")
    
    # Test HTTP services
    print_section("HTTP CONNECTIONS")
    flask_api_ok = test_http_connection(f"http://{VM_IP}:{API_PORT}/probe", "Flask API endpoint")
    
    # Only test NoVNC if the socket connection worked
    if novnc_ok:
        novnc_ui_ok = test_http_connection(f"http://{VM_IP}:{NOVNC_PORT}/vnc.html", "NoVNC UI")
    else:
        novnc_ui_ok = False
        print(f"⚠️ Skipping NoVNC UI test since socket connection failed")
    
    # Summary
    print_section("SUMMARY")
    if vnc_ok:
        print("✅ VNC Server (port 5900) is accessible")
    else:
        print("❌ VNC Server is NOT accessible - Check if TightVNC is running")
    
    if flask_ok and flask_api_ok:
        print("✅ Flask API is fully functional")
        print(f"   API URL: http://{VM_IP}:{API_PORT}/probe")
    elif flask_ok:
        print("⚠️ Flask API port is open but the API endpoint is not responding")
    else:
        print("❌ Flask API is NOT accessible - Check if the Flask server is running")
    
    if novnc_ok and novnc_ui_ok:
        print("✅ NoVNC is fully functional")
        print(f"   NoVNC URL: http://{VM_IP}:{NOVNC_PORT}/vnc.html?autoconnect=true&resize=scale&reconnect=true&password=1234")
    elif novnc_ok:
        print("⚠️ NoVNC port is open but the UI is not available")
    else:
        print("❌ NoVNC is NOT accessible - Check if websockify is running with the correct parameters")
    
    # Provide next steps
    print_section("RECOMMENDED ACTIONS")
    if not vnc_ok:
        print("1. Start TightVNC Server on the Windows VM")
    
    if not flask_ok:
        if vnc_ok:
            print("1. Start the Flask API by running:")
            print("   python C:\\omniserver\\main.py")
    
    if not novnc_ok:
        print("1. Start websockify with the correct parameters:")
        print("   python -m websockify 8006 localhost:5900 --web=C:\\omniserver\\novnc")
    
    if vnc_ok and flask_ok and novnc_ok:
        print("All services appear to be running correctly!")
        
        # Ask to open in browser
        try:
            answer = input("\nWould you like to open NoVNC in your browser? (y/n): ")
            if answer.lower() == 'y':
                webbrowser.open(f"http://{VM_IP}:{NOVNC_PORT}/vnc.html?autoconnect=true&resize=scale&reconnect=true&password=1234")
                print("Browser opened!")
        except:
            pass

if __name__ == "__main__":
    main() 