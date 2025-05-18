# % ccm_modify_date: 2025-05-18 16:57:22 %
# % ccm_author: mpegg %
# % version: 20 %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: main %
# % ccm_object_id: MonitorLibreLink.ps1:43 %
# % ccm_commit_id: 85077287515bd36c372cecb566bd8b590687d30d %
# % ccm_commit_count: 43 %
# % ccm_last_commit_message: move config read %
# % ccm_last_commit_author: Matthew Pegg %
# % ccm_last_commit_date: 2025-03-22 17:57:56 -0400 %
# % ccm_file_last_modified: 2025-05-18 16:54:21 %
# % ccm_file_name: MonitorLibreLink.ps1 %
# % ccm_file_type: text/plain %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %

# Define the path to the target script
$scriptPath = "c:\Users\mpegg\Repos\TermiteTowers\LibreLink.log.ps1"

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
