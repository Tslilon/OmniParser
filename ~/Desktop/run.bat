@echo off
echo ======== OmniParser Environment Setup ========
echo.

:: Check if Python is installed
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Python is not installed or not in PATH
    goto :error
)

:: Check if TightVNC is running
echo Checking if VNC Server is running...
powershell -Command "& {Test-NetConnection -ComputerName localhost -Port 5900 -WarningAction SilentlyContinue | Out-Null; if ($?) {echo 'VNC Server is running on port 5900'} else {echo 'ERROR: VNC Server is not running on port 5900'; exit 1}}"
if %ERRORLEVEL% NEQ 0 (
    echo Please start TightVNC Server before continuing.
    goto :error
)

:: Create directories
if not exist C:\omniserver mkdir C:\omniserver
if not exist C:\omniserver\novnc mkdir C:\omniserver\novnc

:: Install dependencies
echo Installing required Python packages...
pip install flask flask-cors pyautogui pillow websockify --quiet

:: Create Python script
echo Creating Flask API script...
echo from flask import Flask, request, jsonify, send_file > C:\omniserver\main.py
echo from flask_cors import CORS >> C:\omniserver\main.py
echo import pyautogui >> C:\omniserver\main.py
echo import io >> C:\omniserver\main.py
echo from PIL import Image >> C:\omniserver\main.py
echo import os >> C:\omniserver\main.py
echo. >> C:\omniserver\main.py
echo app = Flask(__name__) >> C:\omniserver\main.py
echo CORS(app) >> C:\omniserver\main.py
echo. >> C:\omniserver\main.py
echo @app.route('/probe', methods=['GET']) >> C:\omniserver\main.py
echo def probe(): >> C:\omniserver\main.py
echo     return jsonify({'status': 'ok'}) >> C:\omniserver\main.py
echo. >> C:\omniserver\main.py
echo if __name__ == '__main__': >> C:\omniserver\main.py
echo     print('Starting Flask server on port 5000...') >> C:\omniserver\main.py
echo     app.run(host='0.0.0.0', port=5000) >> C:\omniserver\main.py

:: Download NoVNC
echo Downloading NoVNC (this may take a moment)...
powershell -Command "& {$ProgressPreference = 'SilentlyContinue'; try { Invoke-WebRequest -Uri 'https://github.com/novnc/noVNC/archive/refs/tags/v1.4.0.zip' -OutFile 'C:\omniserver\novnc.zip'; Expand-Archive -Path 'C:\omniserver\novnc.zip' -DestinationPath 'C:\omniserver' -Force; Copy-Item -Path 'C:\omniserver\noVNC-1.4.0\*' -Destination 'C:\omniserver\novnc' -Recurse -Force; echo 'NoVNC files installed successfully' } catch { Write-Host 'Error downloading NoVNC: ' + $_.Exception.Message; exit 1 }}"
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Failed to download or extract NoVNC
    goto :error
)

echo Installing websockify...
echo.

:: Check if ports 5000 and 8006 are available
powershell -Command "& {$port5000=Get-NetTCPConnection -LocalPort 5000 -ErrorAction SilentlyContinue; if($port5000) { echo 'WARNING: Port 5000 is already in use'; exit 1 }}"
if %ERRORLEVEL% NEQ 0 (
    echo Please close any applications using port 5000 before continuing.
    goto :error
)

powershell -Command "& {$port8006=Get-NetTCPConnection -LocalPort 8006 -ErrorAction SilentlyContinue; if($port8006) { echo 'WARNING: Port 8006 is already in use'; exit 1 }}"
if %ERRORLEVEL% NEQ 0 (
    echo Please close any applications using port 8006 before continuing.
    goto :error
)

:: Start Flask API server
echo Starting Flask API on port 5000...
start "Flask API" cmd /k "python C:\omniserver\main.py"

:: Start websockify with CORRECT syntax
echo Starting websockify bridge on port 8006...
start "Websockify" cmd /k "python -m websockify 8006 localhost:5900 --web=C:\omniserver\novnc"

:: Give services time to start
timeout /t 5 > nul

:: Verify services are running
powershell -Command "& {$flask=Test-NetConnection -ComputerName localhost -Port 5000 -WarningAction SilentlyContinue; if(-not $flask) { echo 'ERROR: Flask API not running on port 5000'; exit 1 }}"
if %ERRORLEVEL% NEQ 0 goto :service_error

powershell -Command "& {$websock=Test-NetConnection -ComputerName localhost -Port 8006 -WarningAction SilentlyContinue; if(-not $websock) { echo 'ERROR: Websockify not running on port 8006'; exit 1 }}"
if %ERRORLEVEL% NEQ 0 goto :service_error

echo ======== Setup Complete! ========
echo.
echo Access URLs:
echo  - Flask API: http://localhost:5000/probe
echo  - VNC Viewer: http://localhost:8006/vnc.html?autoconnect=true^&resize=scale^&reconnect=true
echo.
echo Press any key to exit...
pause > nul
exit /b 0

:service_error
echo.
echo One or more services failed to start properly.
echo If websockify failed, try running this command manually:
echo python -m websockify 8006 localhost:5900 --web=C:\omniserver\novnc
goto :error

:error
echo.
echo Setup failed! See error messages above.
echo.
echo Troubleshooting tips:
echo  1. Make sure TightVNC Server is running
echo  2. Check if ports 5000 and 8006 are available
echo  3. Verify Python and pip are installed correctly
echo  4. Check your internet connection for downloading NoVNC
echo.
pause
exit /b 1