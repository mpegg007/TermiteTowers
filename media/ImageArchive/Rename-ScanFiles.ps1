<##  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/Rename-ScanFiles.ps1:145 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 71a9239ed59cef6d26922d2fc709918ba565c96c %
#  %ccm_git_commit_id: 613995c2aca19d377baa26d4daae9de8d2232e97 %
#  %ccm_git_commit_count: 145 %
#  %ccm_git_commit_date: 2026-05-24 15:14:51 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: adding readme %
#  %ccm_git_modify_date: 2026-05-24 15:14:59 %
#  %ccm_git_file_last_modified: 2026-05-24 15:14:58 %
#  %ccm_git_file_name: Rename-ScanFiles.ps1 %
#  %ccm_git_path: media/ImageArchive/Rename-ScanFiles.ps1 %
#  %ccm_git_language_mode: powershell %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1557 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  #>
<## %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  % #>
<## %git_commit_history: 2026-05-23 Matthew Pegg  image tagging phase 1  % #>
# Rename-ScanFiles.ps1
# SilverFast already prefixes files with the scan date (e.g. 20260521_0001.tif).
# This script prepends the owner token and a 14-digit datetime (from the file's
# last-write time) to any file in RAW_HDRi that doesn't already start with the owner token.
# Result: Matthew_20260521143022_20260521_0001.tif

$archiveRoot = "C:\media.tt.omp\StorageDisks\OMP-UD14TD2\pmedia.tt.omp\VG\PhotoArchive"

Get-ChildItem -Path $archiveRoot -Directory | ForEach-Object {
    $ownerFolder = $_.FullName
    $ownerToken  = $_.Name -replace '^\d+_', ''
    $rawFolder   = Join-Path $ownerFolder "RAW_HDRi"

    if (-not (Test-Path $rawFolder)) { return }

    $unowned = Get-ChildItem -Path $rawFolder -Filter '*.tif' |
               Where-Object { $_.Name -notmatch ('^' + [regex]::Escape($ownerToken)) }

    if ($unowned.Count -eq 0) { return }

    Write-Host "[$ownerToken] $($unowned.Count) file(s) to rename"

    foreach ($file in $unowned) {
        $dt      = $file.LastWriteTime.ToString("yyyyMMddHHmmss")
        $newName = $ownerToken + "_" + $dt + "_" + $file.Name
        Rename-Item -LiteralPath $file.FullName -NewName $newName
        Write-Host "  $($file.Name)  ->  $newName"

        $mdPath = $file.FullName + ".md"
        if (Test-Path $mdPath) {
            Rename-Item -LiteralPath $mdPath -NewName ($newName + ".md")
            Write-Host "  $($file.Name).md  ->  $($newName).md"
        }
    }
}

Write-Host ""
Write-Host "Rename complete."
