@echo off
REM setup-all-opencode.bat - Windows convenience wrapper for setup-all-opencode.py.
REM
REM Runs the .py installer (single source of truth) via Python so there's no separate logic to
REM keep in sync. Requires Python 3. Prefers the official "py" launcher, then a PATH lookup,
REM then the standard per-user install location.
REM
REM Usage:        setup-scripts\setup-all-opencode.bat
REM Env override: BRYES_TARGET_DIR (passed through to the .py)

setlocal
set "SCRIPT=%~dp0setup-all-opencode.py"

REM Detect a double-click launch (Explorer runs us via cmd /c "...bat") so we can keep the window
REM open at the end - otherwise a fast success or failure just flashes a black window shut.
set "DOUBLECLICK="
echo %cmdcmdline% | find /i "%~nx0" >nul && set "DOUBLECLICK=1"

if not exist "%SCRIPT%" (
    echo Error: installer not found: %SCRIPT%
    if defined DOUBLECLICK pause
    exit /b 1
)

REM Prefer the official py launcher (always resolves a real interpreter). Fall back to a PATH
REM lookup, skipping the WindowsApps stub: that "python.exe" is an App Execution Alias which opens
REM the Microsoft Store instead of running anything, so it must never win here - the same trap as
REM the System32 WSL "bash" that used to break this installer.
set "PY="
set "PYARGS="

for /f "delims=" %%i in ('where py 2^>nul ^| findstr /v /i "WindowsApps"') do (
    if not defined PY set "PY=%%i"
)
if defined PY set "PYARGS=-3"

if not defined PY (
    for /f "delims=" %%i in ('where python 2^>nul ^| findstr /v /i "WindowsApps"') do (
        if not defined PY set "PY=%%i"
    )
)

if not defined PY (
    if exist "%LocalAppData%\Programs\Python\Launcher\py.exe" (
        set "PY=%LocalAppData%\Programs\Python\Launcher\py.exe"
        set "PYARGS=-3"
    )
)

if not defined PY (
    echo Error: Python 3 not found. Install it from https://www.python.org/downloads/
    echo        ^(tick "Add python.exe to PATH"^), then re-run. Alternatively run directly:
    echo            python setup-scripts\setup-all-opencode.py
    if defined DOUBLECLICK pause
    exit /b 1
)

"%PY%" %PYARGS% "%SCRIPT%" %*
set "RC=%ERRORLEVEL%"
if defined DOUBLECLICK pause
exit /b %RC%
