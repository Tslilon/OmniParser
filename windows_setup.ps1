# Windows Setup Script for OmniParser
# This script sets up and starts the OmniParser services on Windows

# Define variables
$PORT = 5000
$WORKSPACE_DIR = Get-Location

# Print banner
Write-Host "============================================================"
Write-Host "OmniParser Windows VM Setup"
Write-Host "============================================================"
Write-Host "Using the following configuration:"
Write-Host "- Server Port: $PORT"
Write-Host "- Workspace: $WORKSPACE_DIR"
Write-Host "============================================================"

# Ensure the required directories exist
New-Item -ItemType Directory -Force -Path "C:\omniserver" | Out-Null

# Function to check if a process is running on a specific port
function Test-PortInUse {
    param(
        [Parameter(Mandatory=$true)]
        [int]$Port
    )
    
    $connections = netstat -ano | findstr ":$Port"
    return $connections.Count -gt 0
}

# Start Windows Flask server
if (Test-PortInUse -Port $PORT) {
    Write-Host "Server is already running on port $PORT"
} else {
    Write-Host "Starting Windows Flask server on port $PORT..."
    
    # Navigate to the server directory
    Set-Location -Path "C:\omniserver"
    
    # Start the server
    Start-Process -FilePath "python" -ArgumentList "main.py", "--port", "$PORT" -NoNewWindow
    
    # Wait for server to start
    Write-Host "Waiting for server to initialize..."
    Start-Sleep -Seconds 3
    
    Write-Host "Server started successfully on port $PORT"
}

# Display IP address information
Write-Host "`nIP Address Information:"
ipconfig | findstr "IPv4"
Write-Host "`nMake sure to use the correct IP address with port $PORT in your Mac setup"

# Return to original directory
Set-Location -Path $WORKSPACE_DIR

Write-Host "`nWindows setup complete. The server is running at http://localhost:$PORT"
Write-Host "Press Ctrl+C to stop the server."

# Keep the script running
try {
    while ($true) {
        Start-Sleep -Seconds 10
    }
} finally {
    Write-Host "Shutting down..."
} 