@echo off
REM  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
REM  %ccm_git_repo: TermiteTowers %
REM  %ccm_git_branch: dev1 %
REM  %ccm_git_object_id: media/flaresolverr_starter.cmd:0 %
REM  %ccm_git_author: mpegg %
REM  %ccm_git_author_email: mpegg@hotmail.com %
REM  %ccm_git_blob_sha: abc69c2cbfa3f3bfff7f26460539bfdaa0b997cf %
REM  %ccm_git_commit_id: unknown %
REM  %ccm_git_commit_count: 0 %
REM  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
REM  %ccm_git_commit_author: unknown %
REM  %ccm_git_commit_email: unknown %
REM  %ccm_git_commit_message: unknown %
REM  %ccm_git_modify_date: 2025-09-06 11:51:26 %
REM  %ccm_git_file_last_modified: 2025-09-06 11:51:26 %
REM  %ccm_git_file_name: flaresolverr_starter.cmd %
REM  %ccm_git_path: media/flaresolverr_starter.cmd %
REM  %ccm_git_language_mode: bat %
REM  %ccm_git_file_type: text/x-msdos-batch %
REM  %ccm_git_file_encoding: us-ascii %
REM  %ccm_git_file_eol: CRLF %
REM  %ccm_git_exec: no %
REM  %ccm_git_size: 833 %
REM  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
REM %git_commit_history: test % 



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
