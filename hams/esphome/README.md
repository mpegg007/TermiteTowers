# ESPHome Configuration for Elegoo ESP32

This directory contains modular ESPHome configurations for ESP32 devices, specifically configured for an Elegoo ESP32 board with DHT22 sensor and relay control.

## File Structure

```
esphome/
├── secrets.yaml              # Sensitive configuration (Wi-Fi, API keys, passwords)
├── base.yaml                 # Shared configuration for all ESP devices
├── elegoo-esp32-01.yaml     # Device-specific configuration
└── README.md                 # This documentation file
```

## Hardware Setup

### Elegoo ESP32 Board Connections

**DHT22 Temperature/Humidity Sensor (GPIO4):**
- VCC → 3.3V or 5V
- GND → GND
- DATA → GPIO4
- Add 4.7kΩ pull-up resistor between DATA and VCC

**Relay Module (GPIO5):**
- VCC → 5V or 3.3V (depending on relay module)
- GND → GND  
- IN/Signal → GPIO5

**Optional Push Button (GPIO0):**
- One side → GPIO0
- Other side → GND
- Built-in pull-up resistor is used

## Setup Instructions

### 1. Initial Configuration

1. **Configure secrets.yaml:**
   ```yaml
   wifi_ssid: "Your_WiFi_Network"
   wifi_password: "your_wifi_password"
   api_encryption_key: "your_32_character_encryption_key"
   ota_password: "your_ota_password"
   fallback_ap_password: "fallback12345678"
   ```

2. **Generate encryption key:**
   ```bash
   esphome wizard elegoo-esp32-01.yaml
   ```
   Or generate manually:
   ```python
   import secrets
   print(secrets.token_hex(16))  # Generates 32-character hex string
   ```

### 2. Compilation and Upload

**First-time flash (via USB):**
```bash
esphome run elegoo-esp32-01.yaml
```

**OTA updates (after initial flash):**
```bash
esphome run elegoo-esp32-01.yaml --device elegoo-esp32-01.local
```

### 3. Home Assistant Integration

1. The device should auto-discover in Home Assistant
2. Go to Settings → Devices & Services → ESPHome
3. Configure the device using the API encryption key from secrets.yaml

## Configuration Features

### Base Configuration (base.yaml)
- **Wi-Fi with fallback AP:** Automatic connection with backup hotspot
- **OTA updates:** Over-the-air firmware updates
- **API integration:** Secure Home Assistant connection
- **Web server:** Local device interface
- **Basic sensors:** WiFi signal, internal temperature, uptime
- **Device information:** IP address, version, MAC address

### Device-Specific Features (elegoo-esp32-01.yaml)
- **DHT22 sensor:** Temperature and humidity monitoring
- **Relay control:** GPIO5 switch with restore state
- **Input validation:** Sensor reading validation and filtering
- **Logging:** Detailed operation logs
- **Automation examples:** Ready-to-use scripts and intervals

## Customization

### Adding New Devices

1. Copy `elegoo-esp32-01.yaml` to a new file (e.g., `elegoo-esp32-02.yaml`)
2. Update substitutions:
   ```yaml
   substitutions:
     device_name: "elegoo-esp32-02"
     friendly_name: "Elegoo ESP32 #2"
     dht_pin: "4"      # Change if different
     relay_pin: "5"    # Change if different
   ```

### Modifying GPIO Pins

Update the substitutions in your device-specific YAML:
```yaml
substitutions:
  dht_pin: "4"        # DHT22 data pin
  relay_pin: "5"      # Relay control pin
```

### Adding More Sensors

Add to the device-specific YAML file:
```yaml
sensor:
  - platform: adc
    pin: A0
    name: "${friendly_name} Analog Input"
    update_interval: 60s
```

## Version Control

### Git Setup

1. **Initialize repository (if not already done):**
   ```bash
   git init
   git add .
   git commit -m "Initial ESPHome configuration"
   ```

2. **Create .gitignore:**
   ```
   secrets.yaml
   .esphome/
   ```

3. **Create secrets template:**
   ```bash
   cp secrets.yaml secrets.yaml.template
   # Edit template to remove actual passwords
   git add secrets.yaml.template
   ```

### Best Practices

- **Never commit secrets.yaml** - contains sensitive information
- **Use meaningful commit messages:** "Add DHT22 sensor to living room ESP32"
- **Tag stable versions:** `git tag -a v1.0 -m "Stable DHT22 + Relay config"`
- **Branching:** Use feature branches for testing new sensors
- **Documentation:** Update README when adding new features

## Troubleshooting

### Common Issues

1. **Device won't connect to Wi-Fi:**
   - Check credentials in secrets.yaml
   - Connect to fallback AP: "Elegoo ESP32 #1 Fallback"
   - Use captive portal to reconfigure

2. **DHT22 reading errors:**
   - Check wiring and pull-up resistor
   - Verify GPIO pin in substitutions
   - Check logs for validation errors

3. **OTA updates fail:**
   - Ensure device is on same network
   - Check OTA password in secrets.yaml
   - Try USB upload if OTA fails

4. **Home Assistant discovery issues:**
   - Verify API encryption key matches
   - Check firewall settings
   - Restart Home Assistant integration

### Debug Mode

Enable detailed logging:
```yaml
logger:
  level: DEBUG
  logs:
    dht: DEBUG
    wifi: DEBUG
```

## Hardware Specifications

### Elegoo ESP32 DevKit V1
- **Microcontroller:** ESP32-WROOM-32
- **CPU:** Dual-core Tensilica Xtensa 32-bit LX6
- **Flash:** 4MB
- **SRAM:** 520KB
- **Wi-Fi:** 802.11 b/g/n
- **Bluetooth:** Classic + BLE
- **GPIO Pins:** 30 (some with restrictions)
- **ADC:** 12-bit, 18 channels
- **PWM:** 16 channels
- **Power:** 5V USB or 7-12V VIN

### Recommended GPIO Usage
- **GPIO 0:** Boot mode pin (avoid or use with caution)
- **GPIO 1, 3:** UART TX/RX (avoid unless necessary)
- **GPIO 4-5, 12-15, 16-19, 21-23, 25-27, 32-39:** General purpose
- **GPIO 6-11:** Connected to flash (avoid)
- **GPIO 34-39:** Input only, no pull-up resistors

## Future Enhancements

- [ ] Add temperature-based relay automation
- [ ] Implement MQTT support for non-Home Assistant setups
- [ ] Add support for multiple relay channels
- [ ] Create templates for common sensor combinations
- [ ] Add deep sleep configuration for battery-powered devices
