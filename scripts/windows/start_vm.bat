REM % ccm_tag:  %
REM % ccm_size: 988 %
REM % ccm_exec: no %
REM % ccm_blob_sha: 9f3f6230312c3466238cd9e2ba281a540f055eca %
REM % ccm_path: scripts/windows/start_vm.bat %
REM % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
REM % ccm_commit_email: unknown %
REM % ccm_commit_author: unknown %
REM % ccm_commit_message: unknown %
REM % ccm_author_email: mpegg@hotmail.com %
@echo off
REM moved to scripts\windows\start_vm.bat
REM Original content preserved below

:: % ccm_modify_date: 2025-08-29 15:31:33 %
:: % ccm_author: mpegg %
:: % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
:: % ccm_branch: dev1 %
:: % ccm_object_id: start_vm.bat:43 %
:: % ccm_commit_id: 85077287515bd36c372cecb566bd8b590687d30d %
:: % ccm_commit_count: 43 %
:: % ccm_file_last_modified: 2025-08-29 13:51:08 %
:: % ccm_file_name: start_vm.bat %
:: % ccm_file_type: text/x-msdos-batch %
:: % ccm_file_encoding: us-ascii %
:: % ccm_file_eol: CRLF %
:: filepath: c:\Users\mpegg\Repos\TermiteTowers\start_vm.bat

@echo off
:: Enable logging to a file
set LOGFILE=c:\jobLogs\start_vm.log
if not exist c:\jobLogs mkdir c:\jobLogs
echo Script started at %date% %time% >> "%LOGFILE%"
REM ...existing content unchanged...
