:: filepath: c:\Users\mpegg\Repos\TermiteTowers\start_vm.bat
@echo off

:: Check if Home_Assistant is reachable
ping -n 1 homeassistant >nul 2>&1
if %errorlevel% neq 0 (
    echo Home_Assistant is not reachable. Restarting VM...
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" controlvm "Home_Assistant" poweroff
    timeout /t 5 /nobreak >nul
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" startvm "Home_Assistant" --type headless
) else (
    echo Home_Assistant is reachable.
    :: Check if web response on port 8123 is available
    powershell -Command "try { (Invoke-WebRequest -Uri http://homeassistant:8123 -UseBasicParsing).StatusCode } catch { $_.Exception.Response.StatusCode }" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Home_Assistant web response on port 8123 is not available. Restarting VM...
        "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" controlvm "Home_Assistant" poweroff
        timeout /t 5 /nobreak >nul
        "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" startvm "Home_Assistant" --type headless
    ) else (
        echo Home_Assistant web response on port 8123 is available.
    )
)
