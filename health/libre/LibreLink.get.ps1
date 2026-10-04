<##  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: health/libre/LibreLink.get.ps1:100 %
#  %ccm_git_author: Matthew Pegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: a92c686e8ca2b0e9484773deac3109c97e640076 %
#  %ccm_git_commit_id: 043d1161f28704961fc3977112b42f1a9c83dd93 %
#  %ccm_git_commit_count: 100 %
#  %ccm_git_commit_date: 2025-10-11 10:56:22 -0400 %
#  %ccm_git_commit_author: Matthew Pegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: libre logon fix plus hook rework for win.os %
#  %ccm_git_modify_date: 2025-10-11 10:56:23 %
#  %ccm_git_file_last_modified: 2025-10-11 10:56:23 %
#  %ccm_git_file_name: LibreLink.get.ps1 %
#  %ccm_git_path: health/libre/LibreLink.get.ps1 %
#  %ccm_git_language_mode: powershell %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 3395 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  #>
<## %git_commit_history: hook final alpha v0.1 % #>
<## %git_commit_history: fix: update LibreLink.get.ps1 for LibreView API v4.16.0 - add account-id header and update version % #>


# Load credentials from an external configuration file
$ConfigPath = "c:\Users\mpegg\Repos\TermiteTowers\config.json"
if (-Not (Test-Path $ConfigPath)) {
	Write-Error "Configuration file not found at $ConfigPath"
	exit 1
}
$Config = Get-Content $ConfigPath | ConvertFrom-Json
$Region = $Config.Region
$Username = $Config.Username
$Password = $Config.Password

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
$Authheaders.Add("User-Agent", "llu.ios/4.16.0 CFNetwork/1408.0.4 Darwin/22.4.0")
$AuthBody = @"
{
	`"email`": `"$Username`",
	`"password`": `"$Password`"
}
"@
$AuthURI = "https://api-$Region.libreview.io/llu/auth/login"
$tresponse = Invoke-RestMethod $AuthURI -Method 'POST' -Headers $Authheaders -Body $AuthBody

# Log the full authentication response for debugging
Write-Output "[DEBUG] Auth Response: $($tresponse | ConvertTo-Json -Depth 10)"
$AuthToken = $tresponse.data.authTicket.token
$UserId = $tresponse.data.user.id
Write-Output "[DEBUG] Auth Token: $AuthToken"
Write-Output "[DEBUG] User ID: $UserId"

# Create SHA256 hash of User ID for account-id header
$sha256 = [System.Security.Cryptography.SHA256]::Create()
$userIdBytes = [System.Text.Encoding]::UTF8.GetBytes($UserId)
$hashBytes = $sha256.ComputeHash($userIdBytes)
$AccountIdHash = [System.BitConverter]::ToString($hashBytes).Replace("-", "").ToLower()
Write-Output "[DEBUG] Account ID Hash: $AccountIdHash"

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
$response = Invoke-RestMethod 'https://api-ca.libreview.io/llu/connections' -Method 'GET' -Headers $headers
$headers = $null
$response | ConvertTo-Json
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

Write-Output "$TimestampFormatted | Glucose Level: $level mmol/L | Trend Arrow: $TrendArrow | Measurement Colour: $MeasurementColor | Sensor Serial Number: $SensorSerialNumber $SensorStartDateTimeFormatted"