@echo off
setlocal
title PolicyPilot
cd /d "%~dp0"

echo ================================================
echo   PolicyPilot - starting
echo ================================================

REM ---- make sure Python exists before anything else ----
where python >nul 2>nul || goto :nopython

REM ---- first run: create the Python environment (a few minutes, once) ----
if not exist "backend\.venv\Scripts\uvicorn.exe" (
    echo First run detected - installing Python dependencies, please wait...
    python -m venv backend\.venv || goto :fail
    backend\.venv\Scripts\python.exe -m pip install --quiet -r backend\requirements.txt || goto :fail
)

REM ---- first run: build the web interface (needs Node.js) ----
if not exist "frontend\dist\index.html" (
    echo Building the web interface...
    where npm >nul 2>nul || goto :nonode
    pushd frontend
    call npm install --no-fund --no-audit
    if errorlevel 1 (popd & goto :fail)
    call npm run build
    if errorlevel 1 (popd & goto :fail)
    popd
)

REM ---- start the server in its own minimized window ----
echo Starting the server (first start takes ~30 seconds to load AI models)...
start "PolicyPilot server" /min cmd /c "backend\.venv\Scripts\uvicorn.exe app.main:app --app-dir backend --port 8000"

REM ---- wait until the API answers, then open the browser ----
echo Waiting for PolicyPilot to come online...
set /a tries=0
:wait
timeout /t 2 /nobreak >nul
curl -s -o NUL http://localhost:8000/api/health && goto :ready
set /a tries+=1
if %tries% lss 60 goto :wait
echo The server did not respond in time - check the "PolicyPilot server" window for errors.
pause
goto :eof

:ready
start "" http://localhost:8000
echo.
echo   PolicyPilot is running:  http://localhost:8000
echo.
echo   - Your browser opened automatically.
echo   - To stop the app, close the minimized "PolicyPilot server"
echo     window, or double-click stop.bat.
echo.
echo   (This window can be closed; the app keeps running.)
pause
goto :eof

:fail
echo.
echo Setup failed - read the messages above.
pause
goto :eof

:nonode
echo.
echo Node.js is needed to build the web interface. Install the LTS version from
echo https://nodejs.org and run start.bat again.
pause
goto :eof

:nopython
echo.
echo Python is needed to run the AI backend. Install version 3.11 or newer from
echo https://www.python.org/downloads/ - IMPORTANT: tick "Add Python to PATH"
echo during installation - then run start.bat again.
pause
goto :eof
