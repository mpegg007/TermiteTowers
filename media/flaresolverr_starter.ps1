<##||  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#||  %ccm_git_repo: TermiteTowers %
#||  %ccm_git_branch: dev1 %
#||  %ccm_git_object_id: media/flaresolverr_starter.ps1:137 %
#||  %ccm_git_author: Matthew Pegg %
#||  %ccm_git_author_email: mpegg@hotmail.com %
#||  %ccm_git_blob_sha: 147eb27583083b29a3160680c3d2c9d1e6314d08 %
#||  %ccm_git_commit_id: 01ebf6d73b649abbf1444f8211ffc1cfb8c3afe1 %
#||  %ccm_git_commit_count: 137 %
#||  %ccm_git_commit_date: 2026-03-01 12:46:09 -0500 %
#||  %ccm_git_commit_author: Matthew Pegg %
#||  %ccm_git_commit_email: mpegg@hotmail.com %
#||  %ccm_git_commit_message: shebang fix %
#||  %ccm_git_modify_date: 2026-03-01 12:46:11 %
#||  %ccm_git_file_last_modified: 2026-03-01 12:46:11 %
#||  %ccm_git_file_name: flaresolverr_starter.ps1 %
#||  %ccm_git_path: media/flaresolverr_starter.ps1 %
#||  %ccm_git_language_mode: powershell %
#||  %ccm_git_file_type: text/plain %
#||  %ccm_git_file_encoding: utf-8 %
#||  %ccm_git_file_eol: CRLF %
#||  %ccm_git_exec: no %
#||  %ccm_git_size: 6056 %
#||  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 
#|| ##COMMIT_HISTORY: %git_commit_history: $DATE $AUTHOR $MESSAGE % #>
<##|| %git_commit_history: #||  %ccm_git_commit_message: shebang fix % #>
#Requires -Version 5.1
#|| ##COMMIT_HISTORY: %git_commit_history: $DATE $AUTHOR $MESSAGE % #>
<##|| %git_commit_history: #  %ccm_git_commit_message: shebang fix % #>
<#

  .SYNOPSIS
    Restarts FlareSolverr - designed to run hidden via Task Scheduler.

  .DESCRIPTION
    - Kills any existing flaresolverr.exe process
    - Starts a fresh instance in a visible minimized console window
      (so you can restore it and read the FlareSolverr console log)
    - The starter script itself runs completely hidden - no CMD window
      pops up or steals keyboard focus on each scheduled run
    - Wakes the external USB drive (F: via c:\jobLogs symlink) with retries
      before writing log entries, avoiding "device not ready" errors

  .NOTES
    Task Scheduler setup:
      Program:   powershell.exe
      Arguments: -NoProfile -NonInteractive -WindowStyle Hidden -ExecutionPolicy Bypass -File "C:\Users\mpegg\Repos\TermiteTowers\media\flaresolverr_starter.ps1"
      General tab: check "Run whether user is logged on or not" for a
      fully invisible launcher (no window flash at all).
      Alternatively, run from a normal console for testing.
#>

# -- Configuration ----------------------------------------------------------------
$LogDir            = 'c:\jobLogs'
$LogFile           = Join-Path $LogDir 'flaresolverr_starter.log'
$FlaresolverrLog   = Join-Path $LogDir 'flaresolverr_console.log'
$ExePath           = 'C:\ProgramData\flaresolverr\flaresolverr.exe'
$WakeMaxTries      = 5     # number of wake attempts for the USB drive
$WakeSleepSec      = 3     # seconds between retries

# -- Helper: Wake the USB drive behind the symlink ----------------------------
function Wait-ForLogDrive {
    <#
      c:\jobLogs is a symlink to F: (external USB).  When the drive is in
      USB selective-suspend / sleep, the first access fails with
      "device not ready".  A small read is enough to spin it up; we just
      need to retry a few times while it wakes.
    #>
    for ($i = 1; $i -le $WakeMaxTries; $i++) {
        try {
            # Attempt a lightweight probe — resolve the symlink target and test it
            $target = (Get-Item $LogDir -ErrorAction Stop).Target
            if ($target) {
                # If it's a symlink/junction, also probe the real path
                $null = Get-ChildItem -Path $LogDir -ErrorAction Stop | Select-Object -First 1
            }
            if (-not (Test-Path $LogDir)) { throw 'Path not found' }
            return $true        # drive is awake
        }
        catch {
            if ($i -lt $WakeMaxTries) {
                Start-Sleep -Seconds $WakeSleepSec
            }
        }
    }
    return $false               # still not ready after all retries
}

# -- Helper: Append a timestamped line to the log ----------------------------
function Write-Log {
    param([string]$Message)
    $ts = Get-Date -Format 'yyyy-MM-dd HH:mm:ss'
    $line = "$ts  $Message"
    try {
        Add-Content -LiteralPath $LogFile -Value $line -ErrorAction Stop
    }
    catch {
        # Last resort — write to the Windows Application event log so we
        # don't lose the message even if the USB drive is truly unreachable.
        Write-EventLog -LogName Application -Source 'Application' `
                       -EventId 1001 -EntryType Warning `
                       -Message "flaresolverr_starter: $Message (log write failed: $_)"
    }
}

# -- Main ---------------------------------------------------------------------

# 1.  Wake the USB drive / log directory
$driveReady = Wait-ForLogDrive

if (-not $driveReady) {
    # Still try to create/write, but don't abort the restart
    # The actual flaresolverr restart is more important than logging
    try { New-Item -Path $LogDir -ItemType Directory -Force -ErrorAction SilentlyContinue | Out-Null } catch {}
}

if (-not (Test-Path $LogDir)) {
    try { New-Item -Path $LogDir -ItemType Directory -Force | Out-Null } catch {}
}

Write-Log 'Script started.'

if (-not $driveReady) {
    Write-Log "WARNING: Log drive required $WakeMaxTries wake attempts or was not fully ready."
}

# 2.  List & kill existing flaresolverr processes
$existing = Get-Process -Name 'flaresolverr' -ErrorAction SilentlyContinue
if ($existing) {
    Write-Log "Found $($existing.Count) existing flaresolverr process(es) - killing."
    $existing | Stop-Process -Force -ErrorAction SilentlyContinue
    Start-Sleep -Seconds 2  # brief pause so the port is released
} else {
    Write-Log 'No existing flaresolverr process found.'
}

# 3.  Start FlareSolverr with stdout/stderr redirected to a log file.
#     The OS handles the redirection natively so the log keeps writing
#     after this script exits.
#     View live output any time with:
#       Get-Content c:\jobLogs\flaresolverr_console.log -Tail 50 -Wait
if (Test-Path $ExePath) {
    # Roll the console log - keep previous run as .prev for reference
    if (Test-Path $FlaresolverrLog) {
        $prevLog = $FlaresolverrLog -replace '\.log$', '.prev.log'
        Copy-Item -LiteralPath $FlaresolverrLog -Destination $prevLog -Force -ErrorAction SilentlyContinue
    }

    # Combine stdout + stderr into one file via cmd /c redirection.
    # Start-Process -NoNewWindow + redirect keeps it headless and the
    # child process owns the file handle directly (survives script exit).
    $stderrLog = $FlaresolverrLog -replace '\.log$', '.stderr.log'
    try {
        $proc = Start-Process -FilePath $ExePath `
                              -NoNewWindow `
                              -RedirectStandardOutput $FlaresolverrLog `
                              -RedirectStandardError  $stderrLog `
                              -PassThru
        Write-Log "Started flaresolverr.exe (PID $($proc.Id))."
        Write-Log "  stdout -> $FlaresolverrLog"
        Write-Log "  stderr -> $stderrLog"
    }
    catch {
        Write-Log "ERROR: Failed to start flaresolverr.exe - $_"
    }
} else {
    Write-Log "ERROR: Executable not found at $ExePath"
}

Write-Log 'Script finished.'
