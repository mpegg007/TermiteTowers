<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: hams/README.md:102 %
  %ccm_git_author: Matthew Pegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: dc2c578ac6151c4ad495fa211963fd31b61c7a24 %
  %ccm_git_commit_id: 0fe5f85b2d82fa548d0ef593b302bf3f28915940 %
  %ccm_git_commit_count: 102 %
  %ccm_git_commit_date: 2025-10-18 16:33:31 -0400 %
  %ccm_git_commit_author: Matthew Pegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: esphome %
  %ccm_git_modify_date: 2025-10-18 16:33:33 %
  %ccm_git_file_last_modified: 2025-10-18 16:33:33 %
  %ccm_git_file_name: README.md %
  %ccm_git_path: hams/README.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 1783 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Home Assistant Miscellaneous (HAMS)

This directory contains various Home Assistant related configurations, scripts, and documentation.

## Documentation

Start here:

- **[hal-context.md](docs/hal-context.md)** — the HAL (Home Assistant) instance snapshot: topology, sensor families & naming, add-on/integration stack, automation inventory, gotchas. **Read first for any HAL question.**
- **[SKILL.md](docs/SKILL.md)** — the HA development skill (triggers on "HAL").
- **[sensors.md](docs/sensors.md)** · **[dashboards.md](docs/dashboards.md)** · **[integrations.md](docs/integrations.md)** — generic HA references.
- **[zigbee-door-sensor-rollout.md](docs/zigbee-door-sensor-rollout.md)** — Zigbee door/contact + PIR + button rollout: naming contract, automation slate, live status.
- **[esphome/README.md](esphome/README.md)** · **[ESP32-Naming-Standard.md](esphome/ESP32-Naming-Standard.md)** — ESPHome configs & naming.
- Wiki: [ha-hal-bridge runbook](../wiki/runbook-ha-hal-bridge.md) · [ha-handler runbook](../wiki/runbook-ha-handler.md) · [Device-Naming-Standard](../wiki/Device-Naming-Standard.md).

## Directory Structure

```
hams/
├── docs/                 # Documentation (see "Documentation" above)
│   ├── SKILL.md          # HA development skill (triggers on "HAL")
│   ├── hal-context.md    # HAL instance snapshot — read first for HAL questions
│   ├── zigbee-door-sensor-rollout.md  # Zigbee contact/PIR/button rollout plan
│   ├── sensors.md        # Sensor reference
│   ├── dashboards.md     # Lovelace dashboard reference
│   └── integrations.md   # Custom integration reference
├── esphome/              # ESPHome device configs (esp32-node01..09, orion, hydra)
│   ├── tt-esp-base.yaml  # Shared ESPHome base configuration
│   ├── esp32-node*.yaml  # Per-node device configs
│   ├── secrets.yaml      # Sensitive data (not in git)
│   ├── secrets.yaml.template  # Template for secrets
│   └── README.md         # ESPHome documentation
├── inventory/            # Network/device inventories (CSV, YAML, JSON)
├── .gitignore            # Git ignore rules
└── README.md             # This file
```

## Components

### ESPHome Configurations
Modular ESPHome configurations for ESP32 devices with:
- Shared base configuration for common settings
- Device-specific configurations
- Proper secrets management
- Version control ready

See [esphome/README.md](esphome/README.md) for detailed documentation.

## Getting Started

1. **Configure your secrets:**
   ```bash
   cd esphome
   cp secrets.yaml.template secrets.yaml
   # Edit secrets.yaml with your actual credentials
   ```

2. **Flash your first device:**
   ```bash
   esphome run elegoo-esp32-01.yaml
   ```

3. **Add to Home Assistant:**
   - Device should auto-discover
   - Use the API key from your secrets.yaml

## Future Components

This directory is set up to accommodate additional Home Assistant related items:
- Node-RED flows
- Automation backups  
- Custom integrations
- Dashboard configurations
- Scripts and utilities

## Version Control

The configuration is designed to work well with Git:
- Sensitive data is excluded via .gitignore
- Template files provided for setup
- Modular structure for easy maintenance
- Clear documentation for team collaboration
