# % ccm_tag:  %
# % ccm_size: 3299 %
# % ccm_exec: no %
# % ccm_blob_sha: 5b8f5231bb9aa859b583813e934390963dd4faf8 %
# % ccm_path: health/libre/LibreLink.get.ps1 %
# % ccm_commit_date: 2025-08-29 13:23:17 -0400 %
# % ccm_commit_email: hygiene@test %
# % ccm_commit_author: Repo Hygiene %
# % ccm_commit_message: hooks: normalize CCM headers in pre-commit; move Libre scripts to health/libre with wrappers; remove legacy ccm_last_commit_* fields %
# % ccm_author_email: hygiene@test %
# % ccm_modify_date: 2025-08-29 13:23:17 %
# % ccm_author: Repo Hygiene %
# % ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
# % ccm_branch: main %
# % ccm_object_id: health/libre/LibreLink.get.ps1:59 %
# % ccm_commit_id: 9b54dd5331936bfca0a1bc265ddb7adeeed8c26f %
# % ccm_commit_count: 59 %
# % ccm_file_last_modified: 2025-08-29 13:23:17 %
# % ccm_file_name: LibreLink.get.ps1 %
# % ccm_file_type: text/plain %
# % ccm_file_encoding: us-ascii %
# % ccm_file_eol: CRLF %


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

Write-Output "$TimestampFormatted | Glucose Level: $level mmol/L | Trend Arrow: $TrendArrow | Measurement Colour: $MeasurementColor | Sensor Serial Number: $SensorSerialNumber $SensorStartDateTimeFormatted"