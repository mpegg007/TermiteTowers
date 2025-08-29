# % ccm_modify_date: 2025-08-29 13:23:17 %
# % ccm_author: Repo Hygiene %
# % ccm_author_email: hygiene@test %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: main %
# % ccm_object_id: LibreLink.get.ps1:59 %
# % ccm_commit_id: 9b54dd5331936bfca0a1bc265ddb7adeeed8c26f %
# % ccm_commit_count: 59 %
# % ccm_commit_message: hooks: normalize CCM headers in pre-commit; move Libre scripts to health/libre with wrappers; remove legacy ccm_last_commit_* fields %
# % ccm_commit_author: Repo Hygiene %
# % ccm_commit_email: hygiene@test %
# % ccm_commit_date: 2025-08-29 13:23:17 -0400 %
# % ccm_file_last_modified: 2025-08-29 13:23:17 %
# % ccm_file_name: LibreLink.get.ps1 %
# % ccm_file_type: text/plain %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %
# % ccm_path: LibreLink.get.ps1 %
# % ccm_blob_sha: 988822c9f4e86634c2729d977745ad9b076d345d %
# % ccm_exec: no %
# % ccm_size: 1074 %
# % ccm_tag:  %

Param()
# Wrapper shim: forwards to moved script under health/libre
$target = Join-Path $PSScriptRoot 'health/libre/LibreLink.get.ps1'
if (Test-Path $target) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File $target @args
} else {
    Write-Error "Moved script not found: $target"
    exit 1
}
