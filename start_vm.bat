:: % ccm_modify_date: 2025-05-18 16:57:22 %
:: % ccm_author: mpegg %
:: % version: 20 %
:: % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
:: % ccm_branch: main %
:: % ccm_object_id: start_vm.bat:43 %
:: % ccm_commit_id: 85077287515bd36c372cecb566bd8b590687d30d %
:: % ccm_commit_count: 43 %
:: % ccm_last_commit_message: move config read %
:: % ccm_last_commit_author: Matthew Pegg %
:: % ccm_last_commit_date: 2025-03-22 17:57:56 -0400 %
:: % ccm_file_last_modified: 2025-04-17 10:30:22 %
:: % ccm_file_name: start_vm.bat %
:: % ccm_file_type: text/plain %
:: % ccm_file_encoding: us-ascii %
:: % ccm_file_eol: CRLF %
:: filepath: c:\Users\mpegg\Repos\TermiteTowers\start_vm.bat

@echo off
:: Enable logging to a file
set LOGFILE=c:\jobLogs\start_vm.log
if not exist c:\jobLogs mkdir c:\jobLogs
echo Script started at %date% %time% >> "%LOGFILE%"

:: Check if Home_Assistant is reachable by pinging for 2 minutes
set HOST=homeassistant
set TIMEOUT=120
set /a END=%TIMEOUT% / 1
set REACHABLE=0

for /l %%i in (1,1,%END%) do (
    ping -n 1 %HOST% >nul 2>&1
    if %errorlevel% equ 0 (
        set REACHABLE=1
        goto :HOST_REACHABLE
    )
    timeout /t 1 /nobreak >nul
)

:HOST_REACHABLE
if %REACHABLE% equ 1 (
    echo Home_Assistant is reachable. >> "%LOGFILE%"
    echo Home_Assistant is reachable.
    :: Check if web response on port 8123 is available
    powershell -Command "try { (Invoke-WebRequest -Uri http://homeassistant:8123 -UseBasicParsing).StatusCode } catch { $_.Exception.Response.StatusCode }" >nul 2>&1
    if %errorlevel% neq 0 (
        echo Home_Assistant web response on port 8123 is not available. Restarting VM... >> "%LOGFILE%"
        echo Home_Assistant web response on port 8123 is not available. Restarting VM...
        "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" controlvm "Home_Assistant" poweroff
        timeout /t 5 /nobreak >nul
        "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" startvm "Home_Assistant" --type headless
    ) else (
        echo Home_Assistant web response on port 8123 is available. >> "%LOGFILE%"
        echo Home_Assistant web response on port 8123 is available.
    )
) else (
    echo Home_Assistant is not reachable after 2 minutes. Restarting VM... >> "%LOGFILE%"
    echo Home_Assistant is not reachable after 2 minutes. Restarting VM...
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" controlvm "Home_Assistant" poweroff
    timeout /t 5 /nobreak >nul
    "C:\Program Files\Oracle\VirtualBox\VBoxManage.exe" startvm "Home_Assistant" --type headless
)


echo Post Validation Check... >> "%LOGFILE%"
echo Post Validation Check...
powershell -Command "try { (Invoke-WebRequest -Uri http://homeassistant:8123 -UseBasicParsing).StatusCode } catch { $_.Exception.Response.StatusCode }" >nul 2>&1
if %errorlevel% neq 0 (
    echo Home_Assistant web response on port 8123 is not available. >> "%LOGFILE%"
    echo Home_Assistant web response on port 8123 is not available. 
) else (
    echo Home_Assistant web response on port 8123 is available. >> "%LOGFILE%"
    echo Home_Assistant web response on port 8123 is available.
)
echo Script finished at %date% %time% >> "%LOGFILE%"
exit /b
:: End of script
