<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: hams/esphome/ESP32-Node06-Setup.md:102 %
  %ccm_git_author: Matthew Pegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: f16341eeef7d01a2e810fb778c7f8da81b2ba1eb %
  %ccm_git_commit_id: 0fe5f85b2d82fa548d0ef593b302bf3f28915940 %
  %ccm_git_commit_count: 102 %
  %ccm_git_commit_date: 2025-10-18 16:33:31 -0400 %
  %ccm_git_commit_author: Matthew Pegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: esphome %
  %ccm_git_modify_date: 2025-10-18 16:33:36 %
  %ccm_git_file_last_modified: 2025-10-18 16:33:36 %
  %ccm_git_file_name: ESP32-Node06-Setup.md %
  %ccm_git_path: hams/esphome/ESP32-Node06-Setup.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 4694 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# ESP32 Node06 Setup Documentation

## Device Information
- **Device Name**: esp32-node06
- **Friendly Name**: ESP32 Node06
- **Asset Tag**: TT-006
- **Purpose**: Environmental monitoring station
- **Location**: TBD

## Hardware Components

### ESP32 Development Board
- **Model**: ESP32 DevKit v1 (or compatible)
- **Pins Used**: GPIO21 (SDA), GPIO22 (SCL)

### Sensors
1. **SHT3x Temperature & Humidity Sensor**
   - **Model**: SHT30/SHT31/SHT35
   - **Interface**: I2C (Address: 0x44)
   - **Measurements**: Temperature (-40°C to +125°C), Humidity (0-100% RH)
   - **Wiring**:
     - VCC → 3.3V
     - GND → GND
     - SDA → GPIO21
     - SCL → GPIO22

2. **BH1750 Digital Light Intensity Sensor**
   - **Type**: Ambient light sensor
   - **Interface**: I2C (Address: 0x23)
   - **Range**: 0-65535 lux
   - **Wiring**:
     - VCC → 3.3V
     - GND → GND
     - SDA → GPIO21
     - SCL → GPIO22

## Network Configuration
- **IP Assignment**: DHCP (reserve in router)
- **Fallback AP**: "Esp32-Node06" 
- **OTA Updates**: Enabled
- **API Encryption**: Enabled

## Sensor Specifications

### SHT3x Sensor
- **Accuracy**: ±0.2°C (temperature), ±2% RH (humidity)
- **Resolution**: 0.01°C, 0.01% RH
- **Update Interval**: 30 seconds
- **Operating Range**: -40°C to +125°C, 0-100% RH

### BH1750 Sensor
- **Accuracy**: ±20%
- **Resolution**: 1 lux
- **Update Interval**: 30 seconds
- **Measurement Duration**: 69ms (high resolution mode)

## Installation Commands

### Initial Flash (CRITICAL TIMING!)

**Step 1: Start the flash command**
```bash
esphome run esp32-node06.yaml
```

**Step 2: Wait for connection prompt**
```
Found multiple options for uploading, please choose one:
  [1] COM3 (Silicon Labs CP210x USB to UART Bridge (COM3))
  [2] Over The Air (esp32-node06.local)
(number):
```

**Step 3: Type `1` and hit Enter**

**Step 4: AS SOON AS you see "Connecting..." put ESP32 in boot mode**
- **Hold BOOT button** (don't release yet)
- **Press and release EN button** (while holding BOOT)
- **Release BOOT button**
- Upload should start immediately with "Writing at 0x..." messages

**TIMING IS EVERYTHING**: Boot mode must happen RIGHT when ESPHome tries to connect, not before!

### OTA Updates (after initial flash)
```bash
esphome upload esp32-node06.yaml --device 192.168.1.XXX
```

### View Logs
```bash
esphome logs esp32-node06.yaml --device 192.168.1.XXX
```

### If Flash Gets Stuck
**Symptoms**: Command hangs at "Connecting..." or "Waiting for device"

**Solutions**:
1. **Reset to Boot Mode**: Repeat Step 1 above
2. **Check USB Cable**: Try a different cable (data, not just charging)
3. **Check COM Port**: Make sure no other programs are using the port
4. **Manual Port**: Add `--device COM3` (or your COM port) to command

## Home Assistant Integration

### Entities Created
- `sensor.node06_temperature`
- `sensor.node06_humidity`
- `sensor.node06_light_intensity`
- `sensor.node06_wifi_signal`
- `sensor.node06_uptime`
- `sensor.node06_ip_address`
- `sensor.node06_connected_ssid`
- `sensor.node06_mac_address`
- `sensor.node06_esphome_version`

### Typical Use Cases
- **Environmental Monitoring**: Track room conditions
- **Automation Triggers**: Light-based automation
- **Energy Efficiency**: Monitor for optimal HVAC control
- **Plant Care**: Monitor growing conditions
- **Health Monitoring**: Track indoor air quality metrics

## Troubleshooting

### Flash Issues
1. **Command Hangs**: ESP32 not in boot mode - hold BOOT, press EN, release BOOT
2. **"Device not found"**: Wrong COM port or USB cable issue
3. **"Permission denied"**: Close Arduino IDE, serial monitors, or other programs using the port
4. **Compile errors**: Check secrets.yaml has all required values

### Sensor Issues
1. **I2C Scanner Results**: Check that devices show at 0x23 (BH1750) and 0x44 (SHT3x)
2. **Sensor Not Found**: Verify wiring connections
3. **Unstable Readings**: Check power supply stability
4. **WiFi Connection**: Verify credentials in secrets.yaml

### Debug Commands
```bash
# Check I2C devices
esphome logs esp32-node06.yaml --device IP_ADDRESS

# Monitor sensor readings in real-time
esphome logs esp32-node06.yaml --device 192.168.1.XXX
```

## Wiring Diagram
```
ESP32 Pin    →    Sensor
GPIO21 (SDA) →    SDA (both sensors)
GPIO22 (SCL) →    SCL (both sensors)
3.3V         →    VCC (both sensors)
GND          →    GND (both sensors)
```

## Maintenance
- **Sensor Cleaning**: Clean BH1750 optical surface monthly
- **Calibration**: SHT3x sensors are factory calibrated
- **Updates**: Check for ESPHome updates quarterly

---
**Created**: September 20, 2025  
**Device**: ESP32 Node06  
**Asset Tag**: TT-006  
**Location**: TBD