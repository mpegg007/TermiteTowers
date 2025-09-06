@echo off
REM  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
REM  %ccm_git_modify_date: 2025-09-06 10:01:24 %
REM  %ccm_git_author:  %
REM  %ccm_git_author_email:  %
REM  %ccm_git_repo:  %
REM  %ccm_git_branch:  %
REM  %ccm_git_object_id: :0 %
REM  %ccm_git_commit_id: unknown %
REM  %ccm_git_commit_count: 0 %
REM  %ccm_git_commit_message: unknown %
REM  %ccm_git_commit_author: unknown %
REM  %ccm_git_commit_email: unknown %
REM  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
REM  %ccm_git_file_last_modified:  %
REM  %ccm_git_file_name:  %
REM  %ccm_git_file_type:  %
REM  %ccm_git_file_encoding:  %
REM  %ccm_git_file_eol:  %
REM  %ccm_git_path:  %
REM  %ccm_git_blob_sha: e3d0ca4bcbc6e39a954092e922c1f203e2f11d8a %
REM  %ccm_git_exec: no %
REM  %ccm_git_size: 820 %
REM  %ccm_git_tag:  %
REM  %ccm_git_language_mode: bat %
REM  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 

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
