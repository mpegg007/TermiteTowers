<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/docs/TECHNITIUM_VISIBILITY.md:0 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: fcb3e3ed7c983463cd636dcc8d3dacea694faa3b %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: 0 %
  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2025-09-27 11:12:09 %
  %ccm_git_file_last_modified: 2025-09-25 18:23:56 %
  %ccm_git_file_name: TECHNITIUM_VISIBILITY.md %
  %ccm_git_path: infra/dhcp/docs/TECHNITIUM_VISIBILITY.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 4157 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Technitium DHCP Reservation Information Overview

## What Will Be Visible in Technitium DNS Server

When you add DHCP reservations to Technitium, each entry will display:

### 🏷️ **Core Information (Always Visible)**
- **IP Address**: The reserved IP (192.168.1.x)
- **MAC Address**: Hardware address for device identification
- **Hostname**: Descriptive name (enhanced from your CSV data)

### 📊 **Enhanced Hostname Format**

Your CSV contains rich data that creates **highly descriptive hostnames**:

```
Format: [DeviceName]-[Location]-(DeviceType)
Examples:
- GlobePlug-4-[Basement]-(50207)
- Weather-Bulb-[Master-Bath]  
- Living-room-track-lights-[living-room]-(SW2_NEW)
- Bathroom-Power-Strip-[Master-Bath]-(Power-Strip-44USA)
```

## 🏠 **Your Smart Home Network Layout**

Based on your CSV data, Technitium will show this organized view:

### **Basement Devices**
- `192.168.1.100` → GlobePlug-4-[Basement]-(50207)
- `192.168.1.101` → GlobePlug-3-[Basement]-(50207)  
- `192.168.1.102` → GlobePlug-1-[Basement]-(50207)
- `192.168.1.103` → GlobePlug-2-[Basement]-(50207)
- `192.168.1.121` → [basement]-(Bulb)

### **Kitchen/Living Areas**
- `192.168.1.109` → Front-room-lights-[Kitchen]-(socket)
- `192.168.1.111` → Living-room-track-lights-[living-room]-(SW2_NEW)

### **Bedrooms**
- `192.168.1.107` → [Master-Bedroom]-(Floor-Light-2-4G-WIFI)
- `192.168.1.118` → [bedroom-room]-(Bulb)
- `192.168.1.120` → [bedroom-room]-(Bulb)

### **Bathrooms**  
- `192.168.1.106` → Weather-Bulb-[Master-Bath]
- `192.168.1.222` → Bathroom-Power-Strip-[Master-Bath]-(Power-Strip-44USA)

### **Office**
- `192.168.1.119` → old-b-room-ceiling-Light-[Office]-(E1R)
- `192.168.1.124` → [office]-(Bulb)
- `192.168.1.125` → [office]-(socket)  
- `192.168.1.197` → Office-Pole-Upper-light-[Office]-(SMART-RGB-BULB)
- `192.168.1.207` → [Library]-(Socket)

### **Utility Areas**
- `192.168.1.104` → catio-lights-[Catio]-(socket)
- `192.168.1.105` → Laundry-room-[Laundy-Room]-(socket)
- `192.168.1.108` → Second-floor-light-switch-[Library]-(RJ-Three-gang-switch)
- `192.168.1.195` → Main-Hall-[Hallway]-(KS-602S)
- `192.168.1.218` → Attic-Power-Bar-[Cattic]-(Power-Strip-44USA)

### **Infrastructure & Servers**
- `192.168.1.1` → device-1 (Gateway)
- `192.168.1.114` → Gateway75A2A4
- `192.168.1.194` → monolith (Main server)
- `192.168.1.183` → TT0UOIP (Camera)
- `192.168.1.184` → IPCAM (Camera)

### **IoT & Smart Devices**  
- `192.168.1.129` → esp32-node06 (ESP32 sensor)
- `192.168.1.187` → dreame_vacuum_p2029 (Robot vacuum)
- `192.168.1.190` → Galaxy-Tab-S2 (Tablet)

## 🔍 **Technitium Interface Benefits**

In the Technitium web interface, you'll be able to:

1. **Quick Device Identification**: See at a glance what each device is and where it's located
2. **Room-based Organization**: Group devices by location using the [Location] tags
3. **Device Type Recognition**: Identify device types from (DeviceType) indicators
4. **Easy Troubleshooting**: Match IP addresses to specific devices and locations
5. **Network Planning**: Understand your smart home topology

## 📈 **Additional Data Available (Not Shown in DHCP)**

Your CSV also contains (for reference/future use):
- **Exact coordinates**: Lat/Long for each device
- **Device status**: Online/offline states  
- **Last seen times**: When devices were active
- **Technical IDs**: Unique identifiers for integration
- **Model numbers**: Detailed hardware information

## 🎯 **Practical Benefits**

When troubleshooting network issues, you'll easily see:
- **"The basement smart plug #4 isn't responding"** → Check 192.168.1.100
- **"Office lighting is acting up"** → Investigate 192.168.1.119, 192.168.1.124, 192.168.1.197
- **"Master bathroom devices offline"** → Look at 192.168.1.106, 192.168.1.222

## 🚀 **Ready to Deploy**

Your enhanced DHCP reservations will provide:
- ✅ **Clear device identification** 
- ✅ **Location-based organization**
- ✅ **Device type categorization**
- ✅ **Professional network management**

This transforms a basic IP/MAC list into a comprehensive smart home device inventory!
