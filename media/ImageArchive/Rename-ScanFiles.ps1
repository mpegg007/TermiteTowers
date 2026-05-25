<##  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/ImageArchive/Rename-ScanFiles.ps1:146 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 5bb29cfcb9a1735bd201317299591b947f945602 %
#  %ccm_git_commit_id: ff10418d79d5d337bca240bb7739df3da4f6892a %
#  %ccm_git_commit_count: 146 %
#  %ccm_git_commit_date: 2026-05-24 20:26:55 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: track duplicate image locations, scrape from all files %
#  %ccm_git_modify_date: 2026-05-24 20:26:57 %
#  %ccm_git_file_last_modified: 2026-05-24 20:26:56 %
#  %ccm_git_file_name: Rename-ScanFiles.ps1 %
#  %ccm_git_path: media/ImageArchive/Rename-ScanFiles.ps1 %
#  %ccm_git_language_mode: powershell %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 1881 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  #>
<## %git_commit_history: 2026-05-24 Matthew Pegg  adding readme  % #>
<## %git_commit_history: 2026-05-24 Matthew Pegg  imageArchives  %
 #>
<## %git_commit_history: 2026-05-23 Matthew Pegg  image tagging phase 1  %
 #>
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
        $dt        = $file.LastWriteTime.ToString("yyyyMMddHHmmss")
        $stem      = [System.IO.Path]::GetFileNameWithoutExtension($file.Name)
        $ext       = [System.IO.Path]::GetExtension($file.Name)
        $cleanStem = $stem -replace '[^A-Za-z0-9_\-]', '_' -replace '_+', '_' -replace '^_|_$', ''
        $newName   = $ownerToken + "_" + $dt + "_" + $cleanStem + $ext
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
