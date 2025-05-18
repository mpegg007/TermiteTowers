# % ccm_modify_date: 2025-05-18 16:57:22 %
# % ccm_author: mpegg %
# % version: 20 %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: main %
# % ccm_object_id: LibreLink.log.ps1:43 %
# % ccm_commit_id: 85077287515bd36c372cecb566bd8b590687d30d %
# % ccm_commit_count: 43 %
# % ccm_last_commit_message: move config read %
# % ccm_last_commit_author: Matthew Pegg %
# % ccm_last_commit_date: 2025-03-22 17:57:56 -0400 %
# % ccm_file_last_modified: 2025-05-18 16:47:58 %
# % ccm_file_name: LibreLink.log.ps1 %
# % ccm_file_type: text/plain %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %

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
        $Authheaders.Add("Version", "4.7.0")
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
        $tresponse = Invoke-RestMethod $AuthURI -Method 'POST' -Headers $Authheaders -Body $AuthBody
        $AuthToken = $tresponse.data.authTicket.token
        #$AuthToken

        # Get Libre Link Data
        $headers = New-Object "System.Collections.Generic.Dictionary[[String],[String]]"
        $headers.Add("Pragma", "no-cache")
        $headers.Add("Version", "4.7.0")
        $headers.Add("product", "llu.ios")
        $headers.Add("Cache-Control", "no-cache")
        $headers.Add("Accept-Language", "en-CA,en;q=0.9")
        $headers.Add("Content-Type", "application/json")
        $headers.Add("Authorization", "Bearer $AuthToken")
        $response = $null
        $response = Invoke-RestMethod 'https://api-ca.libreview.io/llu/connections' -Method 'GET' -Headers $headers
        $headers = $null
        #$response | ConvertTo-Json
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

        # Wait for 1 minute
        Start-Sleep -Seconds 60
    }
    catch {
        # Log any errors to the console
        Write-Error "An error occurred: $_"
    }
}
