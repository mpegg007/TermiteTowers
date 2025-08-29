# % ccm_tag:  %
# % ccm_size: 3340 %
# % ccm_exec: no %
# % ccm_blob_sha: 450361f2953976c02a1cd0a4d5d2961c2d97bfff %
# % ccm_path: health/libre/MonitorLibreLink.ps1 %
# % ccm_commit_date: 2025-08-29 13:23:17 -0400 %
# % ccm_commit_email: hygiene@test %
# % ccm_commit_author: Repo Hygiene %
# % ccm_commit_message: hooks: normalize CCM headers in pre-commit; move Libre scripts to health/libre with wrappers; remove legacy ccm_last_commit_* fields %
# % ccm_author_email: hygiene@test %
# % ccm_modify_date: 2025-08-29 13:23:17 %
# % ccm_author: Repo Hygiene %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: main %
# % ccm_object_id: health/libre/MonitorLibreLink.ps1:59 %
# % ccm_commit_id: 9b54dd5331936bfca0a1bc265ddb7adeeed8c26f %
# % ccm_commit_count: 59 %
# % ccm_file_last_modified: 2025-08-29 13:23:17 %
# % ccm_file_name: MonitorLibreLink.ps1 %
# % ccm_file_type: text/plain %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %

# Define the path to the target script (relative to this file's folder)
$scriptPath = Join-Path $PSScriptRoot 'LibreLink.log.ps1'

# Ensure the script is running with administrative rights
if (-not ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "Script is not running as administrator. Relaunching with elevated privileges..."
    Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`"" -Verb RunAs
    exit
}

# Function to log messages (now outputs to screen as well)
function Write-Log {
    param (
        [string]$message
    )
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "$timestamp - $message"
    Write-Host $logMessage
}

# Start logging
Write-Log "Monitor Script started with administrative privileges."

# Check if the script is already running
Write-Log "Checking if the script is already running..."
try {
    Write-Log "Listing all processes with 'powershell' in their name, including executable paths and command lines:"
    $powershellProcesses = Get-Process -Name "powershell" -ErrorAction SilentlyContinue
    foreach ($process in $powershellProcesses) {
        try {
            $executablePath = (Get-Process -Id $process.Id | Select-Object -ExpandProperty Path)
            $commandLine = (Get-WmiObject Win32_Process -Filter "ProcessId=$($process.Id)" | Select-Object -ExpandProperty CommandLine)
            if ($commandLine -match [regex]::Escape($scriptPath)) {
                Write-Log "Process ID: $($process.Id), Matched, Command Line: $executablePath"
            } else {
                Write-Log "Process ID: $($process.Id), Not Matched, Command Line: $executablePath"
            }
        } catch {
            Write-Log "Failed to retrieve details for Process ID: $($process.Id). Error: $_"
        }
    }

    $processRunning = $powershellProcesses | Where-Object {
        $commandLine -match [regex]::Escape($scriptPath)
    }

    if ($processRunning) {
        Write-Log "The script is already running."
    } else {
        Write-Log "The script is not running. Attempting to start it..."
        ##Start-Process -FilePath "powershell.exe" -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`"" 
        Write-Log "Script started successfully."
    }
} catch {
    Write-Log "An error occurred: $_"
}

Write-Log "Script finished."
