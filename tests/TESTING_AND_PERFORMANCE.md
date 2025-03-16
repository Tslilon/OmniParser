# Testing and Performance Tools

This document describes the various testing, checking, and performance measurement tools available in the OmniParser project.

## Server Scripts

### 1. `run_omniparser_ml.sh`
Main script to run the OmniParser ML server with optimized settings.
```bash
./run_omniparser_ml.sh [windows_vm_ip:port]
```
- Sets up environment variables for MPS optimization
- Manages server processes and cleanup
- Starts both ML server and Gradio UI
- Default Windows VM URL: 10.211.55.3:5000

### 2. `debug_server.py`
FastAPI server with detailed logging and performance monitoring.
```bash
python debug_server.py
```
- Runs on port 8000
- Includes memory tracking
- Request timing middleware
- Detailed error logging
- MPS device optimization

### 3. `minimal_server.py`
Lightweight version of the server for testing.
```bash
python minimal_server.py
```
- Minimal dependencies
- Basic functionality only
- Useful for isolating issues

## Performance Testing

### 1. `optimize_batch_size.py`
Tests different batch sizes to find optimal performance.
```bash
python optimize_batch_size.py
```
- Tests batch sizes: [1, 16, 32, 64, 128, 256]
- Measures processing time
- Generates performance plots
- Output: `batch_size_optimization.png`

### 2. `compare_performance.py`
Compares direct vs. API call performance.
```bash
python compare_performance.py
```
- Tests direct model calls vs. API requests
- Measures latency and throughput
- Generates comparison charts
- Output: `performance_comparison.png`

### 3. `profile_omniparser_directly.py`
Profiles OmniParser's internal performance.
```bash
python profile_omniparser_directly.py
```
- Detailed function-level profiling
- Memory usage tracking
- Outputs: 
  - `omniparser_profile.prof`
  - `omniparser_direct_perf.png`

### 4. `test_omniparser_perf.py`
Tests overall OmniParser performance.
```bash
python test_omniparser_perf.py
```
- End-to-end performance testing
- Generates performance logs
- Outputs:
  - `omniparser_perf.png`
  - `omniparser_perf_log.txt`

## Device and Model Checks

### 1. `check_device_consistency.py`
Verifies model device placement and dtype consistency.
```bash
python check_device_consistency.py
```
- Checks model device assignments
- Verifies tensor dtypes
- Tests device consistency across runs

### 2. `model_device_monitor.py`
Monitors model device usage and memory.
```bash
python model_device_monitor.py
```
- Tracks device assignments
- Monitors memory usage
- Logs device changes

## Network Testing

### 1. `test_vm_routes.py`
Tests connectivity with Windows VM server.
```bash
python test_vm_routes.py
```
- Tests all VM endpoints
- Verifies screenshot functionality
- Checks command execution
- Validates response formats

### 2. `network_monitor.py`
Monitors network performance and connectivity.
```bash
python network_monitor.py
```
- Tracks request latency
- Monitors connection stability
- Logs network errors

## Usage Examples

### Performance Testing Workflow
1. Check device consistency:
```bash
python check_device_consistency.py
```

2. Optimize batch size:
```bash
python optimize_batch_size.py
```

3. Compare performance:
```bash
python compare_performance.py
```

### Debugging Workflow
1. Start with minimal server:
```bash
python minimal_server.py
```

2. Monitor device placement:
```bash
python model_device_monitor.py
```

3. Test VM connectivity:
```bash
python test_vm_routes.py
```

## Performance Tips

1. **MPS Optimization**
   - Use float32 dtype consistently
   - Set proper memory fraction
   - Enable MPS fallback

2. **Batch Processing**
   - Default optimal batch size: 32
   - Adjust based on memory availability
   - Monitor memory usage

3. **Memory Management**
   - Clear cache between runs
   - Use inference mode
   - Monitor memory leaks

4. **Network Performance**
   - Check VM connectivity
   - Monitor request latency
   - Use proper timeouts

## Troubleshooting

1. **Device Issues**
   - Run `check_device_consistency.py`
   - Verify MPS availability
   - Check dtype consistency

2. **Performance Issues**
   - Use `profile_omniparser_directly.py`
   - Monitor memory with `model_device_monitor.py`
   - Check batch size optimization

3. **Network Issues**
   - Run `test_vm_routes.py`
   - Use `network_monitor.py`
   - Check VM connectivity

## Contributing

When adding new test scripts:
1. Follow existing naming conventions
2. Add proper logging
3. Include performance metrics
4. Document in this file
5. Add example usage 