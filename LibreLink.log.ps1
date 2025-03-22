# Define the output TXT file in OneDrive Health folder
$outputTxt = "$env:USERPROFILE\OneDrive\Health\LibreLinkData.txt"

# Ensure the TXT file has a header if it doesn't exist
if (-not (Test-Path $outputTxt)) {
    "Timestamp,Measurement" | Out-File -FilePath $outputTxt -Encoding UTF8
}

# Infinite loop to fetch data every minute
while ($true) {
    try {
        # Fetch the measurement data (integrated from LibreLink.get.ps1)
        # Example logic from LibreLink.get.ps1:
        #Libre Link Region and Credentials
        $Region = "ca"
        $Username = "mpegg@hotmail.com"
        $Password = "rLncT6VtGn@4"

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
