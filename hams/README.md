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

## Directory Structure

```
hams/
├── esphome/              # ESPHome device configurations
│   ├── base.yaml         # Shared ESPHome configuration
│   ├── elegoo-esp32-01.yaml  # Elegoo ESP32 device config
│   ├── secrets.yaml      # Sensitive data (not in git)
│   ├── secrets.yaml.template  # Template for secrets
│   └── README.md         # ESPHome documentation
├── .gitignore            # Git ignore rules
└── README.md            # This file
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
