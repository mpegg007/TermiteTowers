REM TermiteTowers Continuous Code Management Header TEMPLATE
REM % ccm_modify_date: 2025-08-29 15:31:33 %
REM % ccm_author: mpegg %
REM % ccm_author_email: mpegg@hotmail.com %
REM % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
REM % ccm_branch: dev1 %
REM % ccm_object_id: scripts/windows/flaresolverr_starter.cmd:0 %
REM % ccm_commit_id: unknown %
REM % ccm_commit_count: 0 %
REM % ccm_commit_message: unknown %
REM % ccm_commit_author: unknown %
REM % ccm_commit_email: unknown %
REM % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
REM % ccm_file_last_modified: 2025-08-29 15:31:34 %
REM % ccm_file_name: flaresolverr_starter.cmd %
REM % ccm_file_type: text/plain %
REM % ccm_file_encoding: us-ascii %
REM % ccm_file_eol: CRLF %
REM % ccm_path: scripts/windows/flaresolverr_starter.cmd %
REM % ccm_blob_sha: cb3ae5e5045ff16cbe2b178177bf42b83fc85cdd %
REM % ccm_exec: no %
REM % ccm_size: 1746 %
REM % ccm_tag:  %
REM tt-ccm.header.end

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
