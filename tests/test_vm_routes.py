import os
import sys
import time
import json
import base64
import requests
import logging
from pathlib import Path
import matplotlib.pyplot as plt

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('/tmp/vm_route_test.log')
    ]
)
logger = logging.getLogger("vm_route_test")

class RouteTest:
    def __init__(self):
        self.windows_vm_url = os.environ.get('WINDOWS_HOST_URL', '10.211.55.3:5000')
        self.omniparser_url = "http://localhost:8000"
        self.gradio_url = "http://localhost:7888"
        
        # Results storage
        self.results = {
            "direct": [],
            "via_vm": [],
            "via_gradio": []
        }
    
    def get_test_image(self):
        """Get the test image path"""
        test_image = "imgs/demo_image.jpg"  # Using a specific test image
        if not os.path.exists(test_image):
            raise FileNotFoundError(f"Test image not found at {test_image}")
        return test_image
    
    def test_direct_route(self, image_base64):
        """Test direct OmniParser API call"""
        try:
            logger.info(f"Testing direct route to {self.omniparser_url}")
            start_time = time.time()
            response = requests.post(
                f"{self.omniparser_url}/parse",
                json={"base64_image": image_base64, "request_id": "direct_test"},
                timeout=120
            )
            total_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"OmniParser error (status {response.status_code}): {response.text}")
                return None
            
            result = response.json()
            logger.info(f"Direct route time: {total_time:.2f}s")
            
            self.results["direct"].append({
                "total_time": total_time,
                "server_time": result.get("latency", 0),
                "timestamp": time.time()
            })
            
            return result
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to OmniParser: {str(e)}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error to OmniParser: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in direct route test: {str(e)}")
            return None
    
    def test_vm_route(self, image_base64):
        """Test routing through Windows VM"""
        try:
            logger.info(f"Testing VM route to {self.windows_vm_url}")
            start_time = time.time()
            
            # First, get a screenshot from the VM
            response = requests.get(
                f"http://{self.windows_vm_url}/screenshot",
                timeout=120
            )
            
            if response.status_code != 200:
                logger.error(f"Windows VM error (status {response.status_code}): {response.text}")
                return None
            
            total_time = time.time() - start_time
            logger.info(f"VM route time: {total_time:.2f}s")
            
            self.results["via_vm"].append({
                "total_time": total_time,
                "server_time": 0,  # We don't have server processing time for now
                "vm_overhead": total_time,
                "timestamp": time.time()
            })
            
            return {"status": "success", "time": total_time}
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to Windows VM: {str(e)}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error to Windows VM: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in VM route test: {str(e)}")
            return None
    
    def test_gradio_route(self, image_base64):
        """Test routing through Gradio UI"""
        try:
            logger.info(f"Testing Gradio route to {self.gradio_url}")
            start_time = time.time()
            response = requests.post(
                f"{self.gradio_url}/api/predict",
                json={"data": [image_base64]},
                timeout=120
            )
            total_time = time.time() - start_time
            
            if response.status_code != 200:
                logger.error(f"Gradio error (status {response.status_code}): {response.text}")
                return None
            
            result = response.json()
            logger.info(f"Gradio route time: {total_time:.2f}s")
            
            self.results["via_gradio"].append({
                "total_time": total_time,
                "timestamp": time.time()
            })
            
            return result
            
        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error to Gradio: {str(e)}")
            return None
        except requests.exceptions.Timeout as e:
            logger.error(f"Timeout error to Gradio: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error in Gradio route test: {str(e)}")
            return None
    
    def check_service_availability(self):
        """Check which services are available"""
        services = {
            "OmniParser": {"url": f"{self.omniparser_url}/probe", "available": False},
            "Windows VM": {"url": f"http://{self.windows_vm_url}/probe", "available": False},
            "Gradio": {"url": f"{self.gradio_url}/", "available": False}
        }
        
        for service, info in services.items():
            try:
                response = requests.get(info["url"], timeout=5)
                info["available"] = response.status_code == 200
                logger.info(f"{service} {'is' if info['available'] else 'is not'} available at {info['url']}")
            except Exception as e:
                logger.warning(f"{service} is not available: {str(e)}")
        
        return services

    def run_comparative_test(self, num_runs=3):
        """Run comparative tests of different routes"""
        try:
            # Check service availability first
            services = self.check_service_availability()
            
            # Get test image
            try:
                image_path = self.get_test_image()
                logger.info(f"Using test image: {image_path}")
                
                with open(image_path, 'rb') as f:
                    image_base64 = base64.b64encode(f.read()).decode('utf-8')
            except FileNotFoundError:
                logger.error(f"Test image not found at imgs/demo_image.jpg")
                return
            except Exception as e:
                logger.error(f"Error reading test image: {str(e)}")
                return
            
            # Run tests
            for i in range(num_runs):
                logger.info(f"\nTest run {i+1}/{num_runs}")
                
                # Only test routes where services are available
                if services["OmniParser"]["available"]:
                    logger.info("Testing direct route...")
                    result = self.test_direct_route(image_base64)
                    if result is None:
                        logger.warning("Direct route test failed")
                else:
                    logger.warning("Skipping direct route - OmniParser not available")
                
                if services["Windows VM"]["available"]:
                    logger.info("Testing VM route...")
                    result = self.test_vm_route(image_base64)
                    if result is None:
                        logger.warning("VM route test failed")
                else:
                    logger.warning("Skipping VM route - Windows VM not available")
                
                if services["Gradio"]["available"]:
                    logger.info("Testing Gradio route...")
                    result = self.test_gradio_route(image_base64)
                    if result is None:
                        logger.warning("Gradio route test failed")
                else:
                    logger.warning("Skipping Gradio route - Gradio not available")
                
                # Brief pause between runs
                if i < num_runs - 1:  # Don't sleep after the last run
                    time.sleep(5)
            
            # Save and plot results if we have any
            if any(self.results.values()):
                self.save_results()
                self.plot_results()
            else:
                logger.error("No successful test results to save or plot")
            
        except Exception as e:
            logger.error(f"Error in comparative test: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
    
    def save_results(self):
        """Save test results to file"""
        output_file = Path('/tmp/route_test_results.json')
        with output_file.open('w') as f:
            json.dump(self.results, f, indent=2)
        logger.info(f"Results saved to {output_file}")
    
    def plot_results(self):
        """Create visualization of test results"""
        # Check if we have any results
        if not any(self.results.values()):
            logger.error("No results to plot - all tests failed")
            return
            
        plt.figure(figsize=(12, 6))
        
        # Prepare data
        routes = []
        times = []
        
        # Only include routes that have data
        if self.results["direct"]:
            routes.append('Direct')
            times.append([r["total_time"] for r in self.results["direct"]])
        if self.results["via_vm"]:
            routes.append('Via VM')
            times.append([r["total_time"] for r in self.results["via_vm"]])
        if self.results["via_gradio"]:
            routes.append('Via Gradio')
            times.append([r["total_time"] for r in self.results["via_gradio"]])
            
        if not routes:
            logger.error("No valid routes to plot")
            return
        
        # Create box plot
        plt.subplot(121)
        plt.boxplot(times, labels=routes)
        plt.title('Processing Time by Route')
        plt.ylabel('Time (seconds)')
        plt.grid(True, linestyle='--', alpha=0.7)
        
        # Create bar plot of averages
        plt.subplot(122)
        averages = [sum(t)/len(t) for t in times]
        plt.bar(routes, averages)
        plt.title('Average Processing Time by Route')
        plt.ylabel('Time (seconds)')
        
        # Add value labels
        for i, v in enumerate(averages):
            plt.text(i, v + 0.5, f'{v:.2f}s', ha='center')
        
        plt.tight_layout()
        plt.savefig('/tmp/route_comparison.png')
        logger.info("Results plot saved to /tmp/route_comparison.png")

def main():
    # Parse arguments
    import argparse
    parser = argparse.ArgumentParser(description='Test different OmniParser routing paths')
    parser.add_argument('--runs', type=int, default=3,
                      help='Number of test runs (default: 3)')
    args = parser.parse_args()
    
    # Run tests
    tester = RouteTest()
    tester.run_comparative_test(args.runs)

if __name__ == "__main__":
    main() 