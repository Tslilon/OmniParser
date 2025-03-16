import os
import sys
import time
import json
import requests
import asyncio
import websockets
import logging
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/network_monitor.log')
    ]
)
logger = logging.getLogger("network_monitor")

class NetworkMonitor:
    def __init__(self):
        self.windows_vm_url = os.environ.get('WINDOWS_HOST_URL', '10.211.55.3:5000')
        self.omniparser_url = "http://localhost:8000"
        self.gradio_url = "http://localhost:7888"
        
        # Track timing stats
        self.timing_stats = {
            "windows_vm": [],
            "omniparser": [],
            "gradio": []
        }
    
    async def check_component(self, name, url, endpoint="/probe"):
        """Check if a component is responsive"""
        try:
            start_time = time.time()
            if url.startswith('ws'):
                async with websockets.connect(url) as websocket:
                    await websocket.ping()
                    latency = (time.time() - start_time) * 1000
                    logger.info(f"{name} WebSocket latency: {latency:.2f}ms")
            else:
                full_url = f"{url}{endpoint}"
                response = requests.get(full_url, timeout=5)
                latency = (time.time() - start_time) * 1000
                logger.info(f"{name} HTTP latency: {latency:.2f}ms")
                
            self.timing_stats[name].append({
                "timestamp": datetime.now().isoformat(),
                "latency_ms": latency,
                "status": "success"
            })
            return True
        except Exception as e:
            logger.error(f"Error checking {name}: {str(e)}")
            self.timing_stats[name].append({
                "timestamp": datetime.now().isoformat(),
                "error": str(e),
                "status": "error"
            })
            return False
    
    def test_image_processing(self, image_path):
        """Test full image processing pipeline"""
        try:
            # Load test image
            with open(image_path, 'rb') as f:
                import base64
                image_base64 = base64.b64encode(f.read()).decode('utf-8')
            
            # Track timing for each step
            timings = {}
            
            # 1. Send to OmniParser
            logger.info("Testing OmniParser processing...")
            start_time = time.time()
            response = requests.post(
                f"{self.omniparser_url}/parse",
                json={"base64_image": image_base64, "request_id": "network_monitor_test"},
                timeout=120
            )
            omniparser_time = time.time() - start_time
            
            if response.status_code != 200:
                raise Exception(f"OmniParser error: {response.text}")
            
            result = response.json()
            logger.info(f"OmniParser processing time: {omniparser_time:.2f}s")
            logger.info(f"OmniParser reported latency: {result.get('latency', 'unknown')}s")
            
            # 2. Test Windows VM connection
            logger.info("Testing Windows VM connection...")
            start_time = time.time()
            response = requests.get(f"http://{self.windows_vm_url}/probe")
            windows_time = time.time() - start_time
            
            logger.info(f"Windows VM response time: {windows_time:.2f}s")
            
            return {
                "omniparser_time": omniparser_time,
                "windows_time": windows_time,
                "omniparser_result": result
            }
            
        except Exception as e:
            logger.error(f"Error in image processing test: {str(e)}")
            return {"error": str(e)}
    
    def monitor_network_stats(self):
        """Get network statistics between components"""
        try:
            import psutil
            
            # Get network stats
            net_io = psutil.net_io_counters()
            
            # Get connection info
            connections = []
            for conn in psutil.net_connections():
                if conn.laddr and conn.raddr:  # Only track active connections
                    connections.append({
                        "local": f"{conn.laddr.ip}:{conn.laddr.port}",
                        "remote": f"{conn.raddr.ip}:{conn.raddr.port}",
                        "status": conn.status
                    })
            
            return {
                "bytes_sent": net_io.bytes_sent,
                "bytes_recv": net_io.bytes_recv,
                "packets_sent": net_io.packets_sent,
                "packets_recv": net_io.packets_recv,
                "active_connections": connections
            }
        except Exception as e:
            logger.error(f"Error getting network stats: {str(e)}")
            return {"error": str(e)}
    
    async def continuous_monitoring(self, duration_seconds=300):
        """Monitor network performance for a specified duration"""
        start_time = time.time()
        iteration = 0
        
        logger.info(f"Starting continuous monitoring for {duration_seconds} seconds...")
        
        while time.time() - start_time < duration_seconds:
            iteration += 1
            logger.info(f"\nIteration {iteration}")
            
            # Check component health
            await self.check_component("windows_vm", f"http://{self.windows_vm_url}")
            await self.check_component("omniparser", self.omniparser_url)
            await self.check_component("gradio", self.gradio_url)
            
            # Get network stats
            stats = self.monitor_network_stats()
            logger.info(f"Network stats: {json.dumps(stats, indent=2)}")
            
            # Save timing stats periodically
            if iteration % 10 == 0:
                self.save_stats()
            
            # Wait before next check
            await asyncio.sleep(5)
        
        # Final stats save
        self.save_stats()
        logger.info("Monitoring complete")
    
    def save_stats(self):
        """Save timing statistics to file"""
        output_file = Path('/tmp/network_monitor_stats.json')
        with output_file.open('w') as f:
            json.dump(self.timing_stats, f, indent=2)
        logger.info(f"Stats saved to {output_file}")

def main():
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Monitor OmniParser network performance')
    parser.add_argument('--duration', type=int, default=300,
                      help='Duration to monitor in seconds (default: 300)')
    parser.add_argument('--test-image', type=str,
                      help='Path to test image for processing test')
    args = parser.parse_args()
    
    monitor = NetworkMonitor()
    
    # Run image processing test if image provided
    if args.test_image:
        logger.info(f"Running image processing test with {args.test_image}")
        results = monitor.test_image_processing(args.test_image)
        logger.info(f"Test results: {json.dumps(results, indent=2)}")
    
    # Run continuous monitoring
    asyncio.run(monitor.continuous_monitoring(args.duration))

if __name__ == "__main__":
    main() 