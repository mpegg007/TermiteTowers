:: % ccm_modify_date: 2025-08-27 17:13:11 %
:: % ccm_author: mpegg %
:: % version: 20 %
:: % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
:: % ccm_branch: main %
:: % ccm_object_id: flaresolverr_starter.cmd:45 %
:: % ccm_commit_id: a08a96751aca77f78f07c1360de62956f882c5a3 %
:: % ccm_commit_count: 45 %
:: % ccm_last_commit_message: adding chat %
:: % ccm_last_commit_author: mpegg %
:: % ccm_last_commit_date: 2025-08-26 21:08:00 -0400 %
:: % ccm_file_last_modified: 2025-07-24 13:41:27 %
:: % ccm_file_name: flaresolverr_starter.cmd %
:: % ccm_file_type: text/plain %
:: % ccm_file_encoding: us-ascii %
:: % ccm_file_eol: CRLF %
:: filepath: c:\Users\mpegg\Repos\TermiteTowers\start_vm.bat

@echo off
:: Enable logging to a file
set LOGFILE=c:\jobLogs\flaresolverr_starter.log
if not exist c:\jobLogs mkdir c:\jobLogs
echo Script started at %date% %time% >> "%LOGFILE%"

echo Listing existing flaresolverr.exe processes... >> "%LOGFILE%"
tasklist /FI "IMAGENAME eq flaresolverr.exe" >> "%LOGFILE%"

REM Kill any existing flaresolverr.exe processes
echo Checking for existing flaresolverr.exe processes... >> "%LOGFILE%"
taskkill /IM flaresolverr.exe /F >nul 2>&1

REM Start a new flaresolverr.exe process in a resized, minimized window
start /MIN "Flaresolverr" cmd.exe /c "mode con: cols=120 lines=40 & C:\ProgramData\flaresolverr\flaresolverr.exe"

echo Started new flaresolverr.exe process. >> "%LOGFILE%"

echo Script finished at %date% %time% >> "%LOGFILE%"
exit /b
:: End of script
