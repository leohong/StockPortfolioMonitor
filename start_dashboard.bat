@echo off
setlocal

set "PORT=8502"
set "URL=http://127.0.0.1:%PORT%/"
set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "APP=%~dp0app.py"

call :is_running
if not errorlevel 1 (
    echo Dashboard is already running at %URL%. Skipping duplicate startup.
    start "" "%URL%"
    exit /b 0
)

if not exist "%PYTHON%" (
    echo Virtual environment not found: %PYTHON%
    echo Install the project environment first. See README.md.
    pause
    exit /b 1
)

if not exist "%APP%" (
    echo Application not found: %APP%
    pause
    exit /b 1
)

echo Starting StockPortfolioMonitor...
powershell.exe -NoProfile -Command "Start-Process -FilePath '%PYTHON%' -ArgumentList @('-m','streamlit','run','%APP%','--server.headless','true','--server.address','127.0.0.1','--server.port','%PORT%','--browser.gatherUsageStats','false') -WorkingDirectory '%~dp0'"

for /L %%I in (1,1,30) do (
    call :is_running
    if not errorlevel 1 goto ready
    powershell.exe -NoProfile -Command "Start-Sleep -Seconds 1"
)

echo Startup timed out. Check the StockPortfolioMonitor window for errors.
pause
exit /b 1

:ready
echo Dashboard started: %URL%
start "" "%URL%"
exit /b 0

:is_running
powershell.exe -NoProfile -Command "if (Get-NetTCPConnection -LocalAddress '127.0.0.1' -LocalPort %PORT% -State Listen -ErrorAction SilentlyContinue) { exit 0 } else { exit 1 }"
exit /b %errorlevel%
