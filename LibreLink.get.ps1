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
