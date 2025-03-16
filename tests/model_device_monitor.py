import torch
import psutil
import time
import os
import gc

class ModelDeviceMonitor:
    """
    A utility to monitor model device placement and memory usage
    during OmniParser operations.
    """
    
    def __init__(self):
        self.device_logs = []
        self.memory_logs = []
        self.initialized = False
        
    def log_model_devices(self, omniparser):
        """Log the device information for all models in OmniParser"""
        if not self.initialized:
            self.initialized = True
            
        entry = {"timestamp": time.time()}
        
        # Log SOM (YOLO) model device info
        if hasattr(omniparser, 'som_model'):
            try:
                som_model_type = type(omniparser.som_model).__name__
                entry["som_model_type"] = som_model_type
                # YOLO models have different parameter access
                if hasattr(omniparser.som_model, 'model'):
                    # Try to get device from internal PyTorch model
                    if hasattr(omniparser.som_model.model, 'device'):
                        entry["som_model_device"] = str(omniparser.som_model.model.device)
                    else:
                        # Try to get from a parameter
                        for p in omniparser.som_model.model.parameters():
                            entry["som_model_device"] = str(p.device)
                            break
            except Exception as e:
                entry["som_model_error"] = str(e)
                
        # Log caption model device info
        if hasattr(omniparser, 'caption_model_processor'):
            try:
                if 'model' in omniparser.caption_model_processor:
                    model = omniparser.caption_model_processor['model']
                    entry["caption_model_type"] = type(model).__name__
                    
                    # Get device from a parameter
                    for p in model.parameters():
                        entry["caption_model_device"] = str(p.device)
                        break
                        
                    # Get model dtype
                    for p in model.parameters():
                        entry["caption_model_dtype"] = str(p.dtype)
                        break
            except Exception as e:
                entry["caption_model_error"] = str(e)
                
        # Memory usage
        self.log_memory_usage()
        
        # Store the entry
        self.device_logs.append(entry)
        return entry
        
    def log_memory_usage(self):
        """Log current memory usage"""
        entry = {
            "timestamp": time.time(),
            "system_memory_mb": None,
            "mps_memory_mb": None,
            "cuda_memory_mb": None
        }
        
        # System memory
        try:
            process = psutil.Process(os.getpid())
            memory_info = process.memory_info()
            entry["system_memory_mb"] = memory_info.rss / (1024 * 1024)
        except Exception as e:
            entry["system_memory_error"] = str(e)
            
        # MPS memory 
        if hasattr(torch.mps, 'current_allocated_memory'):
            try:
                entry["mps_memory_mb"] = torch.mps.current_allocated_memory() / (1024 * 1024)
            except Exception as e:
                entry["mps_memory_error"] = str(e)
                
        # CUDA memory
        if torch.cuda.is_available():
            try:
                entry["cuda_memory_mb"] = torch.cuda.memory_allocated() / (1024 * 1024)
            except Exception as e:
                entry["cuda_memory_error"] = str(e)
                
        self.memory_logs.append(entry)
        return entry
        
    def force_gc(self):
        """Force garbage collection and try to clear caches"""
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        if hasattr(torch.mps, 'empty_cache'):
            torch.mps.empty_cache()
        return self.log_memory_usage()
            
    def print_summary(self):
        """Print a summary of device and memory logs"""
        if not self.device_logs:
            print("No device logs recorded")
            return
            
        print("\n=== Device Placement Summary ===")
        latest = self.device_logs[-1]
        for key, value in latest.items():
            if key != "timestamp":
                print(f"{key}: {value}")
                
        print("\n=== Memory Usage Summary ===")
        if self.memory_logs:
            first = self.memory_logs[0]
            latest = self.memory_logs[-1]
            
            print(f"Initial system memory: {first.get('system_memory_mb', 'N/A'):.2f} MB")
            print(f"Current system memory: {latest.get('system_memory_mb', 'N/A'):.2f} MB")
            
            if 'mps_memory_mb' in latest and latest['mps_memory_mb'] is not None:
                print(f"Current MPS memory: {latest['mps_memory_mb']:.2f} MB")
                
            if 'cuda_memory_mb' in latest and latest['cuda_memory_mb'] is not None:
                print(f"Current CUDA memory: {latest['cuda_memory_mb']:.2f} MB")
                
            print(f"Change in system memory: {latest.get('system_memory_mb', 0) - first.get('system_memory_mb', 0):.2f} MB")

# Example usage:
# monitor = ModelDeviceMonitor()
# monitor.log_model_devices(omniparser)  # Before processing
# # Process image
# monitor.log_model_devices(omniparser)  # After processing
# monitor.force_gc()  # Force cleanup
# monitor.print_summary()  # Print summary 