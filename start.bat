@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "APP_NAME=ai-portfolio"
set "PID_FILE=%~dp0.%APP_NAME%.pid"
set "LOG_DIR=%~dp0logs"
set "OUT_LOG=%LOG_DIR%\%APP_NAME%.out.log"
set "ERR_LOG=%LOG_DIR%\%APP_NAME%.err.log"
set "PWSH=%LOCALAPPDATA%\Microsoft\WindowsApps\pwsh.exe"
set "PYTHON_EXE=%~dp0.venv\Scripts\python.exe"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

for /f "usebackq delims=" %%H in (`uv run python scripts\config_value.py server.host`) do set "HOST=%%H"
for /f "usebackq delims=" %%P in (`uv run python scripts\config_value.py server.port`) do set "PORT=%%P"

set "COMMAND=%~1"
if "%COMMAND%"=="" set "COMMAND=start"

if /i "%COMMAND%"=="help" goto help
if /i "%COMMAND%"=="--help" goto help
if /i "%COMMAND%"=="-h" goto help

if not exist "%PWSH%" (
    echo PowerShell 7 was not found at %PWSH%.
    echo Open this project in PowerShell and run: uv run python app.py
    exit /b 1
)

if not exist "%PYTHON_EXE%" (
    echo Virtual environment was not found at %PYTHON_EXE%.
    echo Open this project in PowerShell and run: uv sync
    exit /b 1
)

if /i "%COMMAND%"=="start" (
    call :_kill_existing
    "%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "$logDir='%LOG_DIR%'; $out='%OUT_LOG%'; $err='%ERR_LOG%'; $port=[int]'%PORT%'; New-Item -ItemType Directory -Force -Path $logDir | Out-Null; $p = Start-Process -FilePath '%PYTHON_EXE%' -ArgumentList @('app.py') -WorkingDirectory '%~dp0' -WindowStyle Hidden -RedirectStandardOutput $out -RedirectStandardError $err -PassThru; Set-Content -Path '%PID_FILE%' -Value $p.Id; $deadline=(Get-Date).AddSeconds(120); $listener=$null; while ((Get-Date) -lt $deadline) { $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($listener) { break }; if (-not (Get-Process -Id $p.Id -ErrorAction SilentlyContinue)) { break }; Start-Sleep -Seconds 1 }; if ($listener) { Write-Host 'Started %APP_NAME% on PID' $p.Id; Write-Host 'URL: http://%HOST%:%PORT%'; Write-Host ('Logs: ' + $out); Write-Host ('      ' + $err); exit 0 }; Write-Error 'Timed out waiting for %APP_NAME% to listen on http://%HOST%:%PORT%'; exit 1"
    if errorlevel 1 exit /b %ERRORLEVEL%
    for /f "usebackq delims=" %%P in ("%PID_FILE%") do set "STARTED_PID=%%P"
    echo Started %APP_NAME% on PID %STARTED_PID%.
    echo URL: http://%HOST%:%PORT%
    echo Logs:
    echo   %OUT_LOG%
    echo   %ERR_LOG%
    exit /b 0
)

if /i "%COMMAND%"=="stop" (
    call :_kill_existing
    exit /b 0
)

if /i "%COMMAND%"=="restart" (
    call :_kill_existing
    call "%~f0" start
    exit /b %ERRORLEVEL%
)

if /i "%COMMAND%"=="status" (
    "%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "$pidFile='%PID_FILE%'; $port=[int]'%PORT%'; $pidValue = if (Test-Path $pidFile) { Get-Content $pidFile -ErrorAction SilentlyContinue | Select-Object -First 1 } else { $null }; $process = if ($pidValue) { Get-Process -Id $pidValue -ErrorAction SilentlyContinue } else { $null }; $listener = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1; if ($listener) { if (-not $process) { Set-Content -Path $pidFile -Value $listener.OwningProcess; $pidValue = $listener.OwningProcess }; Write-Host '%APP_NAME% is running on PID' $pidValue; Write-Host 'URL: http://%HOST%:%PORT%'; exit 0 }; if ($process) { Write-Host '%APP_NAME% is starting on PID' $pidValue 'but is not listening on port %PORT% yet.'; exit 1 }; Remove-Item $pidFile -Force -ErrorAction SilentlyContinue; Write-Host '%APP_NAME% is not running.'; exit 1"
    exit /b %ERRORLEVEL%
)

echo Unknown command: %COMMAND%
exit /b 1

:_kill_existing
    echo Checking for existing %APP_NAME% processes...

    REM Kill by PID file if it exists and the process is alive
    if exist "%PID_FILE%" (
        for /f "usebackq delims=" %%P in ("%PID_FILE%") do (
            tasklist /FI "PID eq %%P" 2>NUL | findstr /I "%%P" >NUL
            if not errorlevel 1 (
                echo   Stopping existing %APP_NAME% on PID %%P
                taskkill /F /T /PID %%P >NUL 2>&1
                "%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "Start-Sleep -Seconds 2"
            )
        )
        del /F "%PID_FILE%" 2>NUL
    )

    REM Kill any process listening on the target port. Use PowerShell's TCP
    REM table instead of findstr regex so only the exact local port is touched.
    "%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "$port=[int]'%PORT%'; $listeners = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique; foreach ($processId in $listeners) { if (Get-Process -Id $processId -ErrorAction SilentlyContinue) { Write-Host ('  Freeing port %PORT% from PID ' + $processId); Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue; Start-Sleep -Seconds 2 } }"

    REM Verify port is actually free before returning
    "%PWSH%" -NoProfile -ExecutionPolicy Bypass -Command "$port=[int]'%PORT%'; if (Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue) { exit 1 } else { exit 0 }"
    if errorlevel 1 (
        echo   WARNING: Port %PORT% is still in use after kill attempts.
    ) else (
        echo   Port %PORT% is free.
    )
exit /b 0

:help
echo Usage:
echo   start.bat start     Start the portfolio service; restart it if already running
echo   start.bat stop      Stop the portfolio service
echo   start.bat restart   Restart the portfolio service
echo   start.bat status    Show service status
echo.
echo Default command:
echo   start.bat
echo.
echo Local URL:
echo   http://%HOST%:%PORT%
exit /b 0
