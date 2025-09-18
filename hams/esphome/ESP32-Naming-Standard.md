# ESP32 Device Naming Standard

## Overview
This document outlines the naming convention for ESP32 devices in the TermiteTowers project, using constellation and mythology-based names for persistent, location-agnostic identification.

## Naming Convention

### Format
- **Device Name**: `esp32_<constellation>` (lowercase, underscore separator)
- **Friendly Name**: `"ESP32 <Constellation>"` (title case, human readable)
- **File Name**: `esp32-<constellation>.yaml` (lowercase, hyphen separator)

### Examples
```yaml
esphome:
  name: esp32-orion
  friendly_name: "ESP32 Orion"
```

## Current Device Mapping

| Legacy Name | New Name | Friendly Name | Primary Function | Status |
|-------------|----------|---------------|------------------|---------|
| `esp32-green-room` | `esp32-orion` | `"ESP32 Orion"` | Multi-sensor environmental monitoring | ✅ Active |
| `esp32-breakout-board` | `esp32-hydra` | `"ESP32 Hydra"` | Development/testing platform | ✅ Active |
| `elegoo-esp32-01` | `esp32-nimbus` | `"ESP32 Nimbus"` | Basic test device | 🔄 Pending |

## Available Names for Future Expansion

### Constellation Names
- `esp32-apollo` - Solar/light-based sensors
- `esp32-atlas` - Heavy sensor load/structural monitoring
- `esp32-hermes` - Communication/relay devices
- `esp32-vega` - Bright/LED focused applications
- `esp32-phoenix` - Backup/failover devices
- `esp32-titan` - High-power applications
- `esp32-nova` - New experimental features
- `esp32-cosmos` - Multi-sensor hubs
- `esp32-stellar` - Precision measurements
- `esp32-nebula` - Environmental monitoring
- `esp32-polaris` - Navigation/reference devices
- `esp32-andromeda` - Advanced sensor arrays
- `esp32-centauri` - Remote/distributed sensors
- `esp32-sirius` - High-priority/critical systems
- `esp32-rigel` - Blue-spectrum/UV applications
- `esp32-capella` - Variable/adaptive systems
- `esp32-altair` - Fast/responsive applications
- `esp32-deneb` - Long-range/extended operations
- `esp32-arcturus` - Bright/prominent displays
- `esp32-spica` - Binary/paired systems

## Benefits of This Naming System

✅ **Location-Agnostic**: Devices can move without name changes  
✅ **MAC-Independent**: No reliance on hardware addresses  
✅ **Memorable**: Easy to remember and distinguish  
✅ **Professional**: Suitable for documentation and presentations  
✅ **Scalable**: Unlimited expansion possibilities  
✅ **Thematic**: Consistent celestial theme

## MCP Prompts for Future Expansion

### Adding New Devices
```
I need to add a new ESP32 device for [describe function/purpose]. Using the constellation naming standard from ESP32-Naming-Standard.md, suggest an appropriate name from the available list and help me create the configuration file.
```

### Expanding the Name List
```
Please expand the ESP32 constellation naming list in ESP32-Naming-Standard.md with 10 more names. Include constellation names, star names, and mythology-based options. For each new name, suggest a potential use case or device function that would fit the name's characteristics.
```

### Renaming Existing Devices
```
I want to rename [current device name] to use the constellation naming standard. Please update the configuration file and suggest an appropriate constellation name based on the device's function and sensors.
```

### Device Documentation
```
Create or update the device documentation for ESP32 [constellation name], including its sensors, pin assignments, and configuration summary following the naming standard format.
```

## File Naming Convention

### Configuration Files
- Format: `esp32-<constellation>.yaml`
- Examples: `esp32-orion.yaml`, `esp32-hydra.yaml`

### Documentation Files
- Format: `ESP32-<Constellation>-Setup.md`
- Examples: `ESP32-Orion-Setup.md`, `ESP32-Hydra-Setup.md`

### Build Directories
- Format: `.esphome/build/esp32-<constellation>/`
- Examples: `.esphome/build/esp32-orion/`

## Migration Notes

When renaming existing devices:

1. **Update ESPHome Configuration**
   ```yaml
   esphome:
     name: esp32-<new-constellation>
     friendly_name: "ESP32 <New-Constellation>"
   ```

2. **Update Home Assistant**
   - Device will appear with new name after restart
   - Update any automations/scripts referencing the old name
   - Update dashboards and entity names if needed

3. **Update Documentation**
   - Rename setup documentation files
   - Update README references
   - Update any network documentation

4. **Network Configuration**
   - Device will get new hostname: `esp32-<constellation>.local` (or by IP address)
   - Update any static IP assignments if used
   - Update firewall rules if device-specific

## Maintenance

This document should be updated when:
- New devices are added to the fleet
- Devices are renamed or retired
- New constellation names are needed
- MCP prompts are refined or expanded

---

**Last Updated**: September 18, 2025  
**Document Version**: 1.0  
**Maintainer**: TermiteTowers Project