@echo off
setlocal EnableExtensions

cd /d "%~dp0"

set "PYTHONUTF8=1"

if exist ".sync.local.bat" (
  call ".sync.local.bat"
) else (
  (
    echo @echo off
    echo rem Local-only secrets for sync.bat. This file is gitignored.
    echo set "VPS_PASSWORD=xl6DJn;^:w3kCf?@"
  ) > ".sync.local.bat"
  call ".sync.local.bat"
)

if not defined VPS_PASSWORD (
  echo ERROR: VPS_PASSWORD is not set.
  echo Edit .sync.local.bat and set:
  echo   set "VPS_PASSWORD=your-password"
  exit /b 1
)

if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" sync.py %*
) else (
  python sync.py %*
)

set "EXIT_CODE=%ERRORLEVEL%"
endlocal & exit /b %EXIT_CODE%
