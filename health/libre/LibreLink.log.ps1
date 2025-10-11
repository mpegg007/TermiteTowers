<##  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
#  %ccm_git_branch: main %
#  %ccm_git_object_id: health/libre/LibreLink.log.ps1:99 %
#  %ccm_git_author: CCM Maintainer %
#  %ccm_git_author_email: ccm@test %
#  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
#  %ccm_git_commit_id: fdd5a462e92cd6c0edee95d543ff210ba1975833 %
#  %ccm_git_commit_count: 99 %
#  %ccm_git_commit_date: 2025-10-11 10:34:48 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: fix: update LibreLink.log.ps1 for LibreView API v4.16.0 - add account-id header and remove debug out %
#  %ccm_git_modify_date: 2025-08-29 07:37:53 %
#  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
#  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
#  %ccm_git_language_mode:  %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 659 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  #>

# Relaunch the script in a new PowerShell window with specific size and position
if (-not $Host.UI.RawUI.WindowTitle -like "*LibreLink Script*") {
    $scriptPath = $MyInvocation.MyCommand.Path
    Start-Process powershell.exe -ArgumentList "-NoExit", "-Command `"$scriptPath`"" -WindowStyle Normal -WorkingDirectory (Split-Path $scriptPath) -PassThru | ForEach-Object {
        $_.WaitForInputIdle()
        # Set window size and position (e.g., width: 800, height: 600, x: 100, y: 100)
        Add-Type @"
using System;
using System.Runtime.InteropServices;
public class Window {
    [DllImport("user32.dll", SetLastError = true)]
    public static extern bool MoveWindow(IntPtr hWnd, int X, int Y, int nWidth, int nHeight, bool bRepaint);
}
"@
        [Window]::MoveWindow($_.MainWindowHandle, 1000, 100, 1000, 200, $true)
    }
    exit
}

# Set the window title to identify the script
$Host.UI.RawUI.WindowTitle = "LibreLink Script"

# Define the output TXT file in OneDrive Health folder
$outputTxt = "$env:USERPROFILE\OneDrive\Health\LibreLinkData.txt"

# Check if the output file has been modified within the last 3 minutes
if (Test-Path $outputTxt) {
    $lastWriteTime = (Get-Item $outputTxt).LastWriteTime
    $timeDifference = (Get-Date) - $lastWriteTime
    if ($timeDifference.TotalMinutes -lt 3) {
        Write-Output "The output file was modified within the last 3 minutes. Exiting script."
        Start-Sleep -Seconds 10
        exit 0
    }
}

# Ensure the OneDrive Health folder exists
$healthFolder = "$env:USERPROFILE\OneDrive\Health"
if (-not (Test-Path $healthFolder)) {
    New-Item -ItemType Directory -Path $healthFolder -Force
}

# Ensure the TXT file has a header if it doesn't exist
if (-not (Test-Path $outputTxt)) {
    "Timestamp,Measurement" | Out-File -FilePath $outputTxt -Encoding UTF8
}

# Load credentials from an external configuration file
$ConfigPath = "c:\Users\mpegg\Repos\TermiteTowers\config.json"
if (-Not (Test-Path $ConfigPath)) {
    Write-Error "Configuration file not found at $ConfigPath"
    exit 1
}
$Config = Get-Content $ConfigPath | ConvertFrom-Json

        # Infinite loop to fetch data every minute
while ($true) {
    try {
        $Region = $Config.Region
        $Username = $Config.Username
        $Password = $Config.Password

        # Fetch the measurement data (integrated from LibreLink.get.ps1)
        # Example logic from LibreLink.get.ps1:
        #Libre Link Region and Credentials

        # Get Auth Token
        $AuthToken = $null
        $Authheaders = $null
        $Authheaders = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
        $Authheaders.Add("Pragma", "no-cache")
        $Authheaders.Add("Version", "4.16.0")
        $Authheaders.Add("product", "llu.ios")
        $Authheaders.Add("Cache-Control", "no-cache")
        $Authheaders.Add("Accept-Language", "en-CA,en;q=0.9")
        $Authheaders.Add("Content-Type", "application/json")
        $AuthBody = @"
{
    `"email`": `"$Username`",
    `"password`": `"$Password`"
}
"@
        $AuthURI = "https://api-$Region.libreview.io/llu/auth/login"
        try {
            $tresponse = Invoke-RestMethod $AuthURI -Method 'POST' -Headers $Authheaders -Body $AuthBody
            $AuthToken = $tresponse.data.authTicket.token
            $UserId = $tresponse.data.user.id
            
            # Create SHA256 hash of User ID for account-id header
            $sha256 = [System.Security.Cryptography.SHA256]::Create()
            $userIdBytes = [System.Text.Encoding]::UTF8.GetBytes($UserId)
            $hashBytes = $sha256.ComputeHash($userIdBytes)
            $AccountIdHash = [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()
        } catch {
            Write-Error "[ERROR] Auth API call failed: $($_.Exception.Message)"
            throw
        }

        # Get Libre Link Data
        $headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
        $headers.Add("Pragma", "no-cache")
        $headers.Add("Version", "4.16.0")
        $headers.Add("product", "llu.ios")
        $headers.Add("Cache-Control", "no-cache")
        $headers.Add("Accept-Language", "en-CA,en;q=0.9")
        $headers.Add("Content-Type", "application/json")
        $headers.Add("Authorization", "Bearer $AuthToken")
        $headers.Add("account-id", $AccountIdHash)
        $response = $null
        $LibreLinkURI = "https://api-ca.libreview.io/llu/connections"
        try {
            $response = Invoke-RestMethod $LibreLinkURI -Method 'GET' -Headers $headers
            $timestamp = $response.data.glucoseMeasurement.Timestamp
            $level = $response.data.glucoseMeasurement.Value
            $TrendArrow = $response.data.glucoseMeasurement.TrendArrow
            $MeasurementColor = $response.data.glucoseMeasurement.MeasurementColor
            $SensorSerialNumber = $response.data.sensor.sn
            $SensorStartUnixTimeStamp = $response.data.sensor.a

            # Convert the Unix timestamp to a DateTime object
            $SensorStartDateTime = [System.DateTimeOffset]::FromUnixTimeSeconds($SensorStartUnixTimeStamp).DateTime
            $SensorStartDateTimeFormatted = $SensorStartDateTime.ToString("yyyyMMdd.HHmmss")
            $TimestampFormatted = (Get-Date $timestamp).ToString("yyyyMMdd.HHmmss")

            $outLine = "$TimestampFormatted | Glucose Level: $level mmol/L | Trend Arrow: $TrendArrow | Measurement Colour: $MeasurementColor | Sensor Serial Number: $SensorSerialNumber $SensorStartDateTimeFormatted"

            Write-Output $outLine

            # Append the data to the TXT file
            "$outLine" | Out-File -FilePath $outputTxt -Append -Encoding UTF8
        } catch {
            Write-Error "[ERROR] LibreLink API call failed: $($_.Exception.Message)"
            throw
        }

        # Wait for 1 minute
        Start-Sleep -Seconds 150
    }
    catch {
        Write-Error "Exception type: $($_.GetType().FullName)"
        Write-Error "Message: $($_.Exception.Message)"
        Write-Error "StackTrace: $($_.Exception.StackTrace)"
        # Wait for 1 minute
        Start-Sleep -Seconds 150
    }
}
