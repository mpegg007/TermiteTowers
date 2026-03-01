<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/Device-Naming-Standard.md:121 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 3af1f7599a1fbc4318951bc1330295728ad508e5 %
  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
  %ccm_git_commit_count: 121 %
  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: cleanup %
  %ccm_git_modify_date: 2025-11-30 12:27:19 %
  %ccm_git_file_last_modified: 2025-11-30 12:27:19 %
  %ccm_git_file_name: Device-Naming-Standard.md %
  %ccm_git_path: wiki/Device-Naming-Standard.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 27770 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: november changes % -->
# TermiteTowers Network Device Naming Standard

## Overview
This document defines the naming convention for all networked devices in the TermiteTowers infrastructure. The system uses device type prefixes combined with constellation names for memorable, consistent identification.

## Naming Format

### General Pattern
```
[tt]<device-prefix>[-<model>]-<constellation|os-code|purpose>[-<purpose>][-<location>]
```

**Complete Pattern Breakdown:**
- **[tt]**: Optional company prefix (attaches to next component)
- **<device-prefix>**: Hardware identifier (mandatory)
- **[-<model>]**: Optional hardware model/variant
- **<constellation|os-code|purpose>**: Core identifier (one of three types)
- **[-<purpose>]**: Optional purpose (when not used as core identifier)
- **[-<location>]**: Optional location (always last when present)

**Maximum Complexity Example**: `ttamd59-u24-monolith-main1-office`
- `tt` = company prefix
- `amd59` = hardware (AMD Ryzen 5 9600X)
- `u24` = OS (Ubuntu 24.04)
- `monolith` = constellation name
- `main1` = purpose code
- `office` = location

### Advanced Rules

#### Prefix Rules
- **TT Prefix**: Optional `tt` prefix attached to hardware prefix (e.g., `ttdi3`, `ttesp32`)
- **Device Prefix**: Mandatory (e.g., `esp32`, `di3`, `amd59`, `sams23`)
- **Model**: Optional additional hardware specification

#### Pattern Differentiation System
**Smart parsing based on format patterns:**
- **OS Codes**: Letters + numbers (e.g., `u24`, `w11`, `d12`, `haos`)
- **Purpose Codes**: 3-4 letters + numbers (e.g., `app01`, `web02`, `main1`, `test01`) 
- **Constellation Names**: Letters only (e.g., `monolith`, `orion`, `terminus`)

**Valid Position 2 Options** (after hardware prefix):
- Constellation: `esp32-orion`, `amd59-monolith`
- OS Code: `esp32-u24`, `amd59-w11` (requires position 3)
- Purpose: `esp32-test01`, `amd59-main1` (direct to purpose)

**Pattern Recognition**: The system can distinguish between `esp32-u24-test01` (hardware+OS+purpose) and `esp32-test01` (hardware+purpose) because `u24` vs `test01` have different patterns.

**Purpose Numbering Limit**: 01-99 only (hex like `appff` would break pattern since it lacks numbers and would be mistaken for constellation name)

#### Multiple Valid Formats for Same Device
**The same physical device can be referenced in numerous ways:**
- **Pure Friendly**: `monolith` (constellation name only)
- **Hardware + Friendly**: `amd59-monolith` (hardware context)
- **Hardware + Purpose**: `esp32-test01` (hardware + direct purpose)
- **OS + Friendly**: `u24-monolith` (OS context)
- **OS + Purpose**: `u24-test01` (OS + direct purpose)
- **Company + OS + Friendly**: `ttu24-monolith` (organizational context)
- **Full Technical**: `amd59-u24-monolith` (complete specification)
- **Full with Purpose**: `esp32-u24-test01` (hardware + OS + purpose)
- **With Location**: `esp32-test01-garage` (purpose + location)
- **Maximum Detail**: `ttamd59-u24-monolith-main1-office` (everything)

**Location Rules**: 
- Location always comes **last** (after purpose if present)
- Must be from **predefined location table**
- Only use when **location context adds value**

**Core Principle**: *Choose the appropriate level of detail for your context. The pattern differentiation system (letters-only vs letters+numbers) eliminates ambiguity.*

#### Constellation vs OS Code
- **Constellation Names**: Friendly names from reserved constellation list
- **OS Codes**: Technical OS identifiers (when used, **purpose is mandatory**)

#### Friendly Name Shortcuts
- **Selected devices** can use constellation name alone (skip prefix)
- **Reserved for primary/important devices** (e.g., `monolith` = `amd59-monolith`)
- **Not all constellation names** qualify for prefix-less usage

### Examples by Pattern

#### Standard Format (Most Common)
```yaml
esp32-orion              # ESP32 with constellation name
amd59-apollo-main1       # AMD Ryzen 5 9600X main workstation
sams6-hermes-living      # Samsung Tab S6 in living room
ttdi3-atlas-server       # Dell i3 server with TT prefix
```

#### OS Code Format (Technical Detail)
```yaml
amd59-w11-dev01          # AMD system, Windows 11, development environment #01
di3-u24-web01            # Dell i3, Ubuntu 24.04, web server #01
vm-u24x-fw01             # VM, Ubuntu 24.04 variant, firewall server #01
sams23-a14-daily         # Samsung S23, Android 14, daily use device
```

#### Mixed Format (OS + Constellation)
```yaml
amd59-u24-monolith       # AMD system, Ubuntu 24.04, monolith constellation
di3-u24-stargate         # Dell i3, Ubuntu 24.04, stargate constellation
amd15-u24-terminus       # AMD Bulldozer, Ubuntu 24.04, terminus constellation
vm-haos-hal              # VM, Home Assistant OS, hal constellation
```

#### Friendly Shortcuts (Prefix-Skip Allowed)
**Constellation names with prefix-skip permission can be used in multiple formats:**

| Constellation | Full Formats | Valid Shortcuts |
|---------------|--------------|-----------------|
| `monolith` | `amd59-monolith`, `amd59-u24-monolith` | `monolith`, `amd59-monolith`, `u24-monolith`, `ttu24-monolith` |
| `stargate` | `di3-u24-stargate` | `stargate`, `di3-stargate`, `u24-stargate`, `ttu24-stargate` |
| `terminus` | `amd15-u24-terminus` | `terminus`, `amd15-terminus`, `u24-terminus`, `ttu24-terminus` |
| `hal` | `vm-haos-hal` | `hal`, `vm-hal`, `haos-hal` |

### Scalability: Bulk Device Naming

**Problem**: With many similar devices (e.g., dozen ESP32s), individual constellation names become impractical.

**Solution**: **Tiered Naming System**
- **Tier 1 (VIP)**: Important devices get constellation names + prefix-skip privilege
- **Tier 2 (Standard)**: Regular devices use constellation names (no prefix-skip)  
- **Tier 3 (Bulk)**: Commodity devices use numbered purposes

#### ESP32 Example Fleet
```yaml
# Tier 1 - VIP Production Devices (constellation + prefix-skip)
# (Currently none - ESP32s moved to Tier 3)

# Tier 2 - Named Devices (constellation, no prefix-skip)
esp32-apollo             # Solar monitoring ESP32
esp32-atlas              # Structural monitoring ESP32
esp32-hermes             # Communication relay ESP32

# Tier 3 - Bulk Devices (numbered purposes)
esp32-node01             # Primary test bed (all sensors)
esp32-node02             # Secondary test bed (bedroom testing)
esp32-node03             # New device #03 (inventory)
esp32-node04             # New device #04 (inventory)
esp32-node05             # New device #05 (inventory)
esp32-sensor01           # Generic sensor node #01
esp32-sensor02           # Generic sensor node #02  
esp32-test01             # Test device #01 (can also be u24-test01, esp32-u24-test01)
esp32-test02             # Test device #02
esp32-dev01              # Development device #01
esp32-dev02              # Development device #02
esp32-temp01             # Temperature sensor #01
esp32-temp02             # Temperature sensor #02

# Alternative valid formats for same devices:
u24-test01               # OS context for test device #01
esp32-u24-test01         # Full hardware + OS + purpose
esp32-test01-garage      # With location context
```

**Naming Strategy**:
1. **Reserve constellation names** for devices with **distinct roles/importance**
2. **Use numbered purposes** for **similar/commodity devices**
3. **Location suffixes** help distinguish: `esp32-temp01-garage`, `esp32-temp02-attic`

**Decision Framework:**
- **Unique important role** → Tier 1 (constellation + shortcut)
- **Distinct specialized function** → Tier 2 (constellation only)
- **Similar/commodity function** → Tier 3 (numbered purpose)

#### Bulk Device Flexibility Example
**ESP32 test device #01 can be referenced as:**
- `esp32-test01` (most common - hardware + purpose)
- `u24-test01` (when OS context matters)
- `esp32-u24-test01` (full technical specification)  
- `ttu24-test01` (with company prefix)
- `esp32-test01-lab` (with location)
- `test01` (if granted shortcut privilege - rare for bulk devices)

#### 99-Device Limit & Scaling Strategy
**Purpose Numbering**: Strict 01-99 limit (hex would break pattern differentiation)

**If You Ever Need 100+ of Same Purpose**:
- **Sub-categorize**: `fw01-99`, `fwcore01-99`, `fwedge01-99` (unlikely scenario)
- **Location differentiate**: `fw01-office`, `fw02-lab`, `fw03-rack1` 
- **Promote important ones**: Give constellation names to key devices

**Reality Check**: 99 firewalls would be an enterprise-scale deployment - at that point you'd likely need different organizational approaches anyway!

### Location Codes (Final Position, Optional)
| Location | Description | Examples |
|----------|-------------|----------|
| `office` | Home office/study | `esp32-temp01-office`, `monolith-main1-office` |
| `living` | Living room | `ps5-phoenix-living`, `chromecast-apollo-living` |
| `bedroom` | Master bedroom | `tv-samsung-bedroom`, `alexa-dot-bedroom` |
| `kitchen` | Kitchen area | `alexa-nova-kitchen`, `bulb-hue-kitchen` |
| `garage` | Garage/workshop | `esp32-temp01-garage`, `camera-wyze-garage` |
| `attic` | Attic space | `esp32-temp02-attic`, `sensor-climate-attic` |
| `basement` | Basement area | `ups-apc-basement`, `server-backup-basement` |
| `lab` | Home lab/server room | `esp32-test01-lab`, `switch-main-lab` |
| `guest` | Guest room | `roku-vega-guest`, `rt02-cosmos-guest` |
| `main` | Main/central location | `rt01-nexus-main`, `sw01-stellar-main` |
| `front` | Front of house | `camera-ring-front`, `sensor-motion-front` |
| `back` | Back of house | `camera-wyze-back`, `light-flood-back` |
| `rack1`, `rack2` | Server rack positions | `ups-apc-rack1`, `switch-main-rack2` |

**Location Rules:**
- **Position**: Always last (after purpose if present)
- **Optional**: Only use when location context adds value
- **Predefined**: Must be from approved location table above
- **Consistent**: Use same location codes across all device types

## OS Codes & Reserved Names

### OS Identifier Codes (1 Letter + Numbers)
| OS Code | Description | Purpose or Constellation Required |
|---------|-------------|----------------------------------|
| `w11` | Windows 11 | ✅ Mandatory |
| `w10` | Windows 10 | ✅ Mandatory |
| `u24` | Ubuntu 24.04 LTS | ✅ Mandatory |
| `u22` | Ubuntu 22.04 LTS | ✅ Mandatory |
| `u20` | Ubuntu 20.04 LTS | ✅ Mandatory |
| `d12` | Debian 12 (Bookworm) | ✅ Mandatory |
| `d11` | Debian 11 (Bullseye) | ✅ Mandatory |
| `c9` | CentOS 9 Stream | ✅ Mandatory |
| `c8` | CentOS 8 Stream | ✅ Mandatory |
| `haos` | Home Assistant OS | ❌ Optional (constellation preferred) |
| `a14` | Android 14 | ✅ Mandatory |
| `a13` | Android 13 | ✅ Mandatory |
| `i17` | Apple iOS 17 | ✅ Mandatory |
| `i16` | Apple iOS 16 | ✅ Mandatory |

### Purpose Codes (Letters + Numbers)
| Purpose | Description | Examples |
|---------|-------------|----------|
| `app01`, `app02` | Application servers | `amd59-u24-app01`, `di3-orion-app02` |
| `web01`, `web02` | Web servers | `amd59-u22-web01`, `vm-apollo-web02` |
| `db01`, `db02` | Database servers | `amd59-u24-db01`, `vm-atlas-db02` |
| `fw01`, `fw02` | Firewall servers | `amd59-u24x-fw01`, `vm-nexus-fw02` |
| `dns01`, `dns02` | DNS servers | `pi4-u24-dns01`, `vm-hermes-dns02` |
| `mail01`, `mail02` | Mail servers | `amd59-u24-mail01`, `vm-vega-mail02` |
| `proxy01`, `proxy02` | Proxy servers | `amd59-u24-proxy01`, `vm-stellar-proxy02` |
| `backup01`, `backup02` | Backup servers | `amd59-u24-backup01`, `nas01-phoenix-backup02` |
| `test01`, `test02` | Testing environments | `vm-u24-test01`, `amd15-hydra-test02` |
| `dev01`, `dev02` | Development environments | `vm-u24-dev01`, `amd59-orion-dev02` |
| `stage01`, `stage02` | Staging environments | `vm-u24-stage01`, `amd59-atlas-stage02` |
| `prod01`, `prod02` | Production environments | `amd59-u24-prod01`, `vm-titan-prod02` |
| `main1`, `main2` | Primary/main systems | `amd59-monolith-main1`, `di3-stargate-main2` |
| `home1`, `home2` | Home automation systems | `vm-haos-home1`, `pi4-nexus-home2` |
| `node01`, `node02` | Generic network nodes | `esp32-node01`, `esp32-node02-bedroom` |
| `sensor01`, `sensor02` | Generic sensor devices | `esp32-sensor01`, `esp32-sensor02` |
| `temp01`, `temp02` | Temperature sensors | `esp32-temp01-garage`, `esp32-temp02-attic` |
| `light01`, `light02` | Lighting controllers | `esp32-light01`, `esp32-light02` |
| `relay01`, `relay02` | Relay controllers | `esp32-relay01`, `esp32-relay02` |
| `cam01`, `cam02` | Camera devices | `esp32-cam01-front`, `esp32-cam02-back` |

### OS Variants ( 1 Letter + Numbers + variant )
OS codes can include variant suffixes for specialized distributions:
- `u24x` - Ubuntu 24.04 variant (custom/minimal/server)
- `u22s` - Ubuntu 22.04 Server edition
- `d12m` - Debian 12 minimal installation
- `w11p` - Windows 11 Pro
- `w11e` - Windows 11 Enterprise

### Network Equipment Integration
Network equipment prefixes align with purpose codes for servers:
- `fw01-u24x-fw01` becomes just `fw01` for network firewall device
- `rt01-nexus-main` for router (uses constellation)
- But `amd59-u24x-fw01` for firewall server running on general hardware
| `macos` | Apple macOS | ✅ Mandatory |

### Constellation Names (Friendly Names)
| Constellation | Prefix Skip Allowed | Current Assignment |
|---------------|---------------------|-------------------|
| `monolith` | ✅ Yes | `amd59-monolith` (can use just `monolith`) |
| `orion` | ✅ Yes | `esp32-orion` (can use just `orion`) |
| `hydra` | ✅ Yes | `esp32-hydra` (can use just `hydra`) |
| `atlas` | ✅ Yes | `di3-atlas` (can use just `atlas`) |
| `apollo` | ❌ No | Must use full `amd15-apollo` |
| `hermes` | ❌ No | Must use full `sams6-hermes` |
| `vega` | ❌ No | Must use full `pixel8-vega` |
| `phoenix` | ❌ No | Must use full prefix |
| `titan` | ❌ No | Must use full prefix |
| `nova` | ❌ No | Must use full prefix |
| `cosmos` | ❌ No | Must use full prefix |
| `stellar` | ❌ No | Must use full prefix |
| `nebula` | ❌ No | Must use full prefix |

## Device Type Prefixes

### Microcontrollers & IoT
| Prefix | Description | Example |
|--------|-------------|---------|
| `esp32` | ESP32 microcontroller boards | `esp32-orion`, `esp32-hydra` |
| `esp8266` | ESP8266 microcontroller boards | `esp8266-vega` |
| `rpi` | Raspberry Pi single-board computers | `rpi4-apollo`, `rpi-zero-nova` |
| `arduino` | Arduino microcontroller boards | `arduino-uno-atlas` |

### Servers & Workstations
| Prefix | Description | Example |
|--------|-------------|---------|
| `di3` | Dell i3 systems | `di3-u24-stargate` |
| `amd15` | AMD Bulldozer Family 15h | `amd15-atlas-server`, `amd15-u24-terminus` |
| `amd59` | AMD Ryzen 5 9600X systems | `amd59-monolith-main` |
| `bosgame` | Bosgame mini PC systems | `bosgame-w10-sdow` |
| `vm` | Virtual machines | `vm-orion-test`, `vm-haos-hal` |

### Mobile Devices
| Prefix | Description | Example |
|--------|-------------|---------|
| `sams23` | Samsung Galaxy S23 | `sams23-nova-mike` |
| `pixel8` | Google Pixel 8 | `pixel8-vega-sarah` |
| `samsa21` | Samsung Galaxy A21 | `samsa21-atlas-backup` |
| `lgg2` | LG G2 | `lgg2-hermes-old` |
| `lgg4` | LG G4 | `lgg4-apollo-spare` |
| `lgg7` | LG G7 | `lgg7-cosmos-previous` |
| `iphone15` | Apple iPhone 15 series | `iphone15-stellar-john` |
| `iphone14` | Apple iPhone 14 series | `iphone14-titan-jane` |

### Tablets
| Prefix | Description | Example |
|--------|-------------|---------|
| `sams2` | Samsung Galaxy Tab S2 10" | `sams2-nexus-kitchen` |
| `sams6` | Samsung Galaxy Tab S6 10" | `sams6-phoenix-living` |
| `sams6lite` | Samsung Galaxy Tab S6 Lite | `sams6lite-hermes-office` |
| `acer7` | Acer 7" tablet | `acer7-atlas-old` |
| `acer10` | Acer 10" tablet | `acer10-apollo-backup` |
| `surface10` | Microsoft Surface tablet 10" | `surface10-cosmos-legacy` |
| `ipadpro` | iPad Pro models | `ipadpro-nexus-shared` |
| `ipadair` | iPad Air models | `ipadair-phoenix-office` |

### Game Consoles
| Prefix | Description | Example |
|--------|-------------|---------|
| `ps4` | PlayStation 4 | `ps4-titan-living` |
| `ps5` | PlayStation 5 | `ps5-phoenix-bedroom` |
| `xbox` | Xbox One/Series | `xbox-atlas-den` |
| `switch` | Nintendo Switch | `switch-nova-portable` |
| `steam` | Steam Deck | `steam-vega-handheld` |

### Network Equipment
| Prefix | Description | Example |
|--------|-------------|---------|
| `rt01` | Primary router | `rt01-nexus-main` |
| `rt02` | Secondary router | `rt02-cosmos-guest` |
| `sw01` | Network switch 1 | `sw01-stellar-main` |
| `sw02` | Network switch 2 | `sw02-apollo-lab` |
| `ap01` | Access Point 1 | `ap01-hermes-office` |
| `ap02` | Access Point 2 | `ap02-vega-workshop` |
| `fw01` | Firewall | `fw01-atlas-perimeter` |
| `nas01` | Network Attached Storage | `nas01-titan-backup` |

### Smart Home & IoT
| Prefix | Description | Example |
|--------|-------------|---------|
| `alexa` | Amazon Echo devices | `alexa-nova-kitchen`, `alexa-dot-bedroom` |
| `google` | Google Home devices | `google-stellar-living` |
| `chromecast` | Chromecast devices | `chromecast-apollo-tv` |
| `roku` | Roku streaming devices | `roku-vega-guest` |
| `tv` | Smart TVs | `tv-samsung-living`, `tv-lg-bedroom` |
| `bulb` | Smart light bulbs | `bulb-hue-office`, `bulb-lifx-kitchen` |

### Specialty Devices
| Prefix | Description | Example |
|--------|-------------|---------|
| `camera` | IP/Security cameras | `camera-ring-front`, `camera-wyze-garage` |
| `print` | Network printers | `print-hp-office`, `print-brother-workshop` |
| `ups` | Uninterruptible Power Supply | `ups-apc-server`, `ups-cyberpower-office` |
| `monitor` | Network monitoring devices | `monitor-pi-temp`, `monitor-sensor-power` |

## Constellation Names Available

### Currently Assigned
- `monolith` - Primary server (friendly: mono)
- `stargate` - Dell i3 Ubuntu 24.04 server (di3-u24-stargate)
- `terminus` - AMD Bulldozer Ubuntu 24.04 system (amd15-u24-terminus)
- `hal` - Oracle VM Home Assistant OS (vm-haos-hal)

### Available for Assignment
- `apollo` - Solar/light-based applications
- `atlas` - Heavy-duty/structural applications  
- `hermes` - Communication/messaging systems
- `vega` - Bright/display-focused devices
- `phoenix` - Backup/recovery systems
- `titan` - High-power/performance devices
- `nova` - New/experimental devices
- `cosmos` - Multi-function hubs
- `stellar` - Precision/accuracy-focused
- `nebula` - Distributed/cloud systems
- `polaris` - Navigation/reference systems
- `andromeda` - Advanced/complex systems
- `centauri` - Remote/distant systems
- `sirius` - High-priority/critical systems
- `nexus` - Central/connection points
- `quantum` - Advanced processing systems
- `orion` - Hunter/tracker applications (freed from ESP32)
- `hydra` - Multi-headed/distributed systems (freed from ESP32)

## Usage Examples

### Server Migration Example
**Old Format**: `ttdi3-w8-app01`  
**New Format**: `di3-atlas-app01`  
**Friendly Reference**: "atlas" (short for atlas server)

### Complete Device Inventory Example
```yaml
# Core Infrastructure (with friendly shortcuts)
monolith              # Short for: amd59-monolith (Dell i3 server)
atlas                 # Short for: di3-atlas (AMD Bulldozer system)
stargate              # Short for: di3-u24-stargate (Dell i3 Ubuntu 24.04 server)
terminus              # Short for: amd15-u24-terminus (AMD Bulldozer Ubuntu 24.04 system)
hal                   # Short for: vm-haos-hal (Oracle VM Home Assistant OS)
rt01-nexus-main       # Primary router (no shortcut available)
sw01-stellar-main     # Main network switch (no shortcut available)
nas01-titan-backup    # Backup storage (no shortcut available)

# Development Environment (mixed formats)
esp32-node01          # ESP32 test bed (all sensors, formerly orion)
esp32-node02          # ESP32 bedroom testing (sensor dev, formerly hydra)
amd59-apollo-main     # AMD Ryzen 5 9600X main workstation (no shortcut)
vm-u24-dev01          # Ubuntu 24.04 development VM #01
amd15-w10-test01      # AMD Bulldozer, Windows 10, testing environment #01
vm-u24x-fw01          # Ubuntu 24.04 variant firewall server #01
bosgame-w10-sdow      # Bosgame mini PC Windows 10 system

# Personal Devices (standard format)
sams23-nova-mike     # Samsung S23 
pixel8-vega-sarah    # Google Pixel 8
sams6-hermes-living  # Samsung Tab S6 10"
ps5-phoenix-living   # Living room PlayStation 5

# With Optional TT Prefix
ttesp32-orion        # Same as esp32-orion, with company prefix
ttdi3-atlas          # Same as di3-atlas, with company prefix
```

## Implementation Guidelines

### Device Registration
1. Choose appropriate prefix from the table above
2. Select unused constellation name from available list
3. Add purpose/location suffix if needed for clarity
4. Update this documentation with assignment
5. Configure device hostname to match naming convention

### Network Configuration
- **Hostname**: Use full device name (`di3-monolith`)
- **DNS**: Should resolve both full name and constellation (`monolith`)
- **DHCP Reservations**: Use full device name for consistency
- **Documentation**: Reference by constellation name in casual communication

### Expansion Process
When adding new device categories:
1. Define appropriate prefix following existing patterns
2. Add to prefix table with examples
3. Update MCP prompts section
4. Document any special naming rules for that category

# IoT Device Naming Clarification

All IoT devices (including ESP32s, sensors, relays, bulbs, switches, etc.) must follow the existing TermiteTowers device naming standard described in this document.

**Do not introduce alternative naming formats.**

Consistency across all device types is critical for scalability, automation, and ease of management. The established pattern (e.g., `esp32-node01`, `esp32-sensor01-garage`) is designed to support large environments and varied device roles.

If you have questions about applying the standard to new device types, refer to the guidelines above or consult the infrastructure team.

## MCP Prompts for Future Expansion

### Adding New Device Category
```
I need to add a new device category for [device type] to the TermiteTowers naming standard. Please review Device-Naming-Standard.md and suggest appropriate prefixes, update the documentation, and provide naming examples that follow the established pattern.
```

### Assigning Names to New Devices
```
I'm adding a new [device type] with [brief description of function/purpose]. Using the Device-Naming-Standard.md, suggest an appropriate constellation name from the available list and provide the complete device name following the naming convention.
```

### Renaming Existing Devices
```
I want to rename [current device name] to follow the TermiteTowers naming standard. The device is a [type/function description]. Please suggest the new name format and help update any necessary configuration files.
```

### Expanding Constellation Names
```
Please expand the constellation name list in Device-Naming-Standard.md with 10 more names. Include mythological, astronomical, and space-themed options. For each new name, suggest what type of device or function would be appropriate based on the name's characteristics.
```

## Migration Notes

### From Legacy Format
Legacy format: `tt<hardware>-<os>-<purpose><number>`  
New format: `<hardware>-<constellation>[-<purpose>]`

**Benefits of New System:**
- ✅ Memorable constellation names for daily use
- ✅ Hardware identification preserved in prefix
- ✅ OS-agnostic (OS changes don't require rename)
- ✅ Scalable across all device categories
- ✅ Consistent format across entire network

### Best Practices
1. **Use constellation names in conversation**: "Is monolith responding?" vs "Is di3-monolith responding?"
2. **Keep technical prefix for documentation**: Inventory, configs, and technical docs use full names
3. **Group related devices**: Use related constellation names for device clusters
4. **Reserve special names**: Keep mythologically significant names (zeus, odin) for critical infrastructure

## Naming Validation Reference

### Quick Validation Checklist

✅ **Valid Names (Same Device, Multiple Formats):**
**Monolith server references:**
- `monolith` (pure constellation)
- `amd59-monolith` (hardware + constellation)
- `u24-monolith` (OS + constellation)
- `ttu24-monolith` (company + OS + constellation)
- `amd59-u24-monolith` (hardware + OS + constellation)
- `amd59-monolith-main1` (hardware + constellation + purpose)

**Other valid examples:**
- `stargate`, `di3-stargate`, `u24-stargate`, `di3-u24-stargate`
- `terminus`, `amd15-terminus`, `u24-terminus`, `amd15-u24-terminus` 
- `hal`, `vm-hal`, `haos-hal`, `vm-haos-hal`
- `esp32-node01`, `esp32-node02` (Tier 3: bulk devices, no shortcuts)
- `esp32-apollo` (Tier 2: constellation name, no prefix-skip)
- `esp32-sensor01-garage`, `esp32-temp02-attic` (Tier 3: bulk devices with location)
- `ttamd59-u24-monolith-main1-office` (maximum detail example)
- `pixel8-vega-mike` (standard format)
- `vm-u24-dev01-lab` (OS code with numbered purpose and location)

❌ **Invalid Names:**
- `vega` (constellation name, but no shortcut permission)
- `apollo` (constellation name, but no shortcut permission)  
- `vm-u24-test` (missing purpose number - should be `test01`)
- `u24-apollo` (apollo doesn't have prefix-skip permission)
- `esp32-test01-workshop` (location `workshop` not in predefined table - use `garage` or add to table)
- `tt-monolith` (tt must attach to hardware/OS prefix, not constellation)
- `esp32-garage-test01` (location must come after purpose, not before)
- `invalid-name` (not following any pattern)

❌ **Invalid Names:**
- `vega` (constellation name, but no shortcut permission)
- `apollo` (constellation name, but no shortcut permission)  
- `vm-u24-test` (missing purpose number - should be `test01`)
- `u24-apollo` (apollo doesn't have prefix-skip permission)
- `tt-monolith` (tt must attach to hardware/OS prefix, not constellation)
- `invalid-name` (not following any pattern)

### Pattern Reference
- **Full Pattern**: `[tt]<device-prefix>[-<model>]-<constellation|os-code>[-<purpose>][-<location>]`
- **Constellation Shortcuts**: Only `monolith`, `stargate`, `terminus`, `hal` permitted
- **OS Codes**: Must include purpose field (e.g., `-dev`, `-test`, `-prod`)
- **Optional tt Prefix**: Can be used with any valid hardware prefix (e.g., `ttesp32`, `ttdi3`)

### Hardware-OS Compatibility
Ensure hardware capabilities match naming choices:
- **ESP32 devices**: Use constellation names (can't run full OS)
- **x86 systems**: Can use OS codes or constellation names
- **Mobile devices**: Match OS to actual device OS (android, ios)
- **Gaming consoles**: Use constellation names (don't run general-purpose OS)
- **Network equipment**: Use constellation names with purpose


---

**Document Version**: 1.1  
**Last Updated**: November 7, 2025  
**Maintainer**: TermiteTowers Infrastructure Team

## Common IoT Device Type Prefixes

Below are recommended prefixes for common IoT device types. Use these in accordance with the TermiteTowers naming standard:

- `esp32` — ESP32 microcontroller boards
- `esp8266` — ESP8266 microcontroller boards
- `rpi` — Raspberry Pi single-board computers (e.g., `rpi4`, `rpi-zero`)
- `arduino` — Arduino microcontroller boards (e.g., `arduino-uno`)
- `zigbee` — Zigbee coordinator/bridge devices
- `zwave` — Z-Wave controller devices
- `sonoff` — Sonoff smart switches/relays
- `shelly` — Shelly smart relays/sensors
- `tuya` — Tuya-based smart devices
- `bulb` — Smart bulbs (e.g., Hue, Lifx)
- `switch` — Smart switches
- `sensor` — Generic sensor modules (if not board-specific)
- `relay` — Relay modules
- `camera` — IP/security cameras
- `plug` — Smart plugs/outlets

Choose prefixes that match the hardware or platform for clarity and consistency.