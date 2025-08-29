REM % ccm_tag:  %
REM % ccm_size: 931 %
REM % ccm_exec: no %
REM % ccm_blob_sha: bd29f816da1779987c5923cb36a0686d33b21c07 %
REM % ccm_path: flaresolverr_starter.cmd %
REM % ccm_commit_date: 1970-01-01 00:00:00 +0000 %
REM % ccm_commit_email: unknown %
REM % ccm_commit_author: unknown %
REM % ccm_commit_message: unknown %
REM % ccm_author_email: mpegg@hotmail.com %
:: % ccm_modify_date: 2025-08-29 15:31:33 %
:: % ccm_author: mpegg %
:: % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
:: % ccm_branch: dev1 %
:: % ccm_object_id: flaresolverr_starter.cmd:45 %
:: % ccm_commit_id: a08a96751aca77f78f07c1360de62956f882c5a3 %
:: % ccm_commit_count: 45 %
:: % ccm_file_last_modified: 2025-08-29 13:51:08 %
:: % ccm_file_name: flaresolverr_starter.cmd %
:: % ccm_file_type: text/plain %
:: % ccm_file_encoding: us-ascii %
:: % ccm_file_eol: CRLF %
:: filepath: c:\Users\mpegg\Repos\TermiteTowers\start_vm.bat

@echo off
REM Wrapper: forward to moved script
setlocal
set TARGET=%~dp0scripts\windows\flaresolverr_starter.cmd
if exist "%TARGET%" (
	call "%TARGET%" %*
) else (
	echo Moved script not found: %TARGET%
	exit /b 1
)
endlocal
