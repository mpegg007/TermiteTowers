REM % ccm_tag:  %
REM % ccm_size: 1267 %
REM % ccm_exec: no %
REM % ccm_blob_sha: 295ea395950ab82e9dd893d47490f3307159d830 %
REM % ccm_path: flaresolverr_starter.cmd %
REM % ccm_commit_date: 2025-08-29 15:33:16 -0400 %
REM % ccm_commit_email: mpegg@hotmail.com %
REM % ccm_commit_author: mpegg %
REM % ccm_commit_message: chore(repo): finalize infra flattening and wrapper shims %
REM % ccm_author_email: mpegg@hotmail.com %
:: % ccm_modify_date: 2025-08-29 15:33:16 %
:: % ccm_author: mpegg %
:: % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
:: % ccm_branch: dev1 %
:: % ccm_object_id: flaresolverr_starter.cmd:62 %
:: % ccm_commit_id: d450999f33707bf562bcbdbb00f28d20c1dd488f %
:: % ccm_commit_count: 62 %
:: % ccm_file_last_modified: 2025-08-29 15:33:16 %
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
