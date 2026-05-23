<##  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: media/New-PhotoArchiveFolders.ps1:139 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 5790fabd76b4b74fc60a8fb8124878073db869f2 %
#  %ccm_git_commit_id: 082ff38c260cbc5b6c247b8ea6097056d609d69a %
#  %ccm_git_commit_count: 139 %
#  %ccm_git_commit_date: 2026-05-23 16:09:44 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: image tagging phase 1 %
#  %ccm_git_modify_date: 2026-05-23 16:09:46 %
#  %ccm_git_file_last_modified: 2026-05-23 16:09:46 %
#  %ccm_git_file_name: New-PhotoArchiveFolders.ps1 %
#  %ccm_git_path: media/New-PhotoArchiveFolders.ps1 %
#  %ccm_git_language_mode: powershell %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: utf-8 %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 2786 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  #>
﻿# New-PhotoArchiveFolders.ps1
# Creates numbered person folders under PhotoArchive on external storage.
# Numbers are zero-padded to 3 digits (001-999).
# Re-run safely to add more people - existing folders are skipped.

$BasePath   = "C:\media.tt.omp\StorageDisks\OMP-UD14TD2\pmedia.tt.omp\VG\PhotoArchive"
$SubFolders = @("RAW_HDRi", "TIFF_Archive", "JPG_Share", "JPG_Print", "Workfiles")

# --- Ensure base folder exists -----------------------------------------------
if (-not (Test-Path -LiteralPath $BasePath)) {
    New-Item -ItemType Directory -Path $BasePath | Out-Null
    Write-Host "Created base folder: $BasePath"
}

# --- Find next available number ----------------------------------------------
$existing = Get-ChildItem -LiteralPath $BasePath -Directory |
    Where-Object   { $_.Name -match '^\d{3}_' } |
    ForEach-Object { [int]($_.Name.Substring(0, 3)) } |
    Sort-Object

if ($existing.Count -gt 0) {
    $nextNumber = ($existing | Measure-Object -Maximum).Maximum + 1
} else {
    $nextNumber = 1
}

$nextStr   = $nextNumber.ToString("D3")
$entryWord = if ($existing.Count -eq 1) { "entry" } else { "entries" }

Write-Host ""
Write-Host "PhotoArchive : $BasePath"
Write-Host "Existing     : $($existing.Count) $entryWord"
Write-Host "Next number  : $nextStr"
Write-Host ""

# --- Prompt for names --------------------------------------------------------
Write-Host "Enter one name per line. Press Enter on a blank line when done."
Write-Host ""

$names = New-Object System.Collections.Generic.List[string]
while ($true) {
    $entry = Read-Host "Name"
    if ([string]::IsNullOrWhiteSpace($entry)) { break }
    $names.Add($entry.Trim())
}

if ($names.Count -eq 0) {
    Write-Host "No names entered. Nothing to do."
    exit 0
}

# --- Create folders ----------------------------------------------------------
Write-Host ""
$created = 0

foreach ($name in $names) {
    if ($nextNumber -gt 999) {
        Write-Warning "Maximum index (999) reached - remaining names skipped."
        break
    }

    $paddedNum  = $nextNumber.ToString("D3")
    $safeName   = $name -replace '[\\/:*?"<>|]', '_'
    $personPath = Join-Path $BasePath ($paddedNum + "_" + $safeName)

    if (Test-Path -LiteralPath $personPath) {
        Write-Warning "Already exists, skipping: $personPath"
    } else {
        New-Item -ItemType Directory -Path $personPath | Out-Null
        Write-Host ($paddedNum + "_" + $safeName)

        foreach ($sub in $SubFolders) {
            New-Item -ItemType Directory -Path (Join-Path $personPath $sub) | Out-Null
            Write-Host "  + $sub"
        }
        $created++
    }

    $nextNumber++
}

$plural = if ($created -ne 1) { "s" } else { "" }
Write-Host ""
Write-Host ("Done. " + $created + " folder set" + $plural + " created.")
