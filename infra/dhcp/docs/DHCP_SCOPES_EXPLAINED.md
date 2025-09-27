<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/dhcp/docs/DHCP_SCOPES_EXPLAINED.md:0 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 594312577b3b668e60950b47f9f3c9fe2038594c %
  %ccm_git_commit_id: unknown %
  %ccm_git_commit_count: 0 %
  %ccm_git_commit_date: 1970-01-01 00:00:00 +0000 %
  %ccm_git_commit_author: unknown %
  %ccm_git_commit_email: unknown %
  %ccm_git_commit_message: unknown %
  %ccm_git_modify_date: 2025-09-27 11:12:09 %
  %ccm_git_file_last_modified: 2025-09-25 18:26:27 %
  %ccm_git_file_name: DHCP_SCOPES_EXPLAINED.md %
  %ccm_git_path: infra/dhcp/docs/DHCP_SCOPES_EXPLAINED.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 4742 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# DHCP Scopes in Technitium DNS Server

## What Are DHCP Scopes?

A **DHCP scope** defines a range of IP addresses that the DHCP server can assign to clients, along with configuration options like subnet mask, gateway, DNS servers, and lease duration.

## 🏗️ **Scope Architecture Concepts**

### **Single Scope Approach (Current Default)**
```
Scope: "LAN" 
Range: 192.168.1.1 - 192.168.1.254
- Everything in one big pool
- DHCP assigns from available addresses
- Static reservations "carve out" specific IPs
```

### **Multiple Scope Approach (Your Idea)**
```
Scope 1: "Network-Appliances" (192.168.1.1 - 192.168.1.8)
- Routers, switches, access points
- No dynamic allocation - reservations only

Scope 2: "Servers" (192.168.1.10 - 192.168.1.50) 
- Static servers, NAS, critical infrastructure
- No dynamic allocation - reservations only

Scope 3: "Smart-Home" (192.168.1.100 - 192.168.1.199)
- IoT devices, smart plugs, bulbs
- Mix of reservations + some dynamic

Scope 4: "Dynamic-Clients" (192.168.1.200 - 192.168.1.250)
- Laptops, phones, guests
- Pure dynamic allocation
```

## 🎯 **Benefits of Multiple Scopes**

### **1. Network Segmentation**
- **Logical organization** by device type
- **Easy identification** of IP ranges
- **Clear allocation policies** per device category

### **2. IP Management Control**
- **Reserved ranges** that never auto-assign (1-8 for appliances)
- **Controlled assignment** for critical infrastructure
- **Dynamic pools** only where needed

### **3. Troubleshooting Benefits**
- **Instant categorization**: "192.168.1.5 = network appliance"
- **Range-based filtering** in monitoring tools
- **Clear network topology** understanding

## 📊 **Your Network Analysis**

Based on your CSV data, here's a suggested scope design:

### **Scope 1: "Core-Infrastructure" (192.168.1.1-1.9)**
```
Purpose: Network core devices
Policy: Reservations only, no dynamic assignment
Devices:
- 192.168.1.1 → Gateway/Router
- 192.168.1.2-1.9 → Switches, APs, core infrastructure
```

### **Scope 2: "Servers" (192.168.1.10-1.49)**
```
Purpose: Server infrastructure  
Policy: Reservations only
Current devices:
- 192.168.1.12 → terminus
- 192.168.1.32 → (unknown server)
- Room for: NAS, Docker hosts, databases
```

### **Scope 3: "Smart-Home-Fixed" (192.168.1.100-1.199)**
```
Purpose: Smart home devices with fixed IPs
Policy: Reservations preferred, limited dynamic
Current devices: Your 40+ smart devices (plugs, bulbs, switches)
```

### **Scope 4: "Dynamic-Clients" (192.168.1.200-1.249)**
```
Purpose: Mobile devices, laptops, guests
Policy: Dynamic assignment preferred
Current devices: 
- 192.168.1.207 → Could move to smart-home scope
```

### **Scope 5: "Special-Services" (192.168.1.250-1.254)**
```
Purpose: Broadcast, special services
Policy: Reservations only
Usage: Broadcast addresses, special services
```

## ⚙️ **Implementation in Technitium**

### **Option 1: Single Scope with Exclusions (Simpler)**
```
Scope: "LAN"
Range: 192.168.1.1 - 192.168.1.254
Exclusions: 
- 192.168.1.1 - 192.168.1.9 (Infrastructure - manual only)
- 192.168.1.10 - 192.168.1.49 (Servers - manual only)
Dynamic Pool: 192.168.1.200 - 192.168.1.249
Reservations: Everything else
```

### **Option 2: Multiple Scopes (More Control)**
```
Create separate scopes for each range
Each with its own policies and options
More complex but more organized
```

## 🚀 **Recommendation for Your Network**

Given your current setup, I recommend **Option 1** (single scope with exclusions):

### **Advantages:**
- ✅ **Simpler management** - one scope to configure
- ✅ **Easy migration** - current devices stay as-is
- ✅ **Flexible reservations** - can place devices anywhere
- ✅ **Clear dynamic pool** - guests get 200-249 range

### **Configuration:**
```bash
# Your current approach but with exclusions:
Scope Name: "LAN"
Start IP: 192.168.1.1
End IP: 192.168.1.254
Subnet: 255.255.255.0
Gateway: 192.168.1.1

# Add these exclusions to prevent dynamic assignment:
Exclusion 1: 192.168.1.1 - 192.168.1.9    (Infrastructure)
Exclusion 2: 192.168.1.10 - 192.168.1.99   (Servers/Special)

# Dynamic pool becomes: 192.168.1.100-199 + 200-254
# Your smart devices (100-199) get reservations
# Guests/laptops get 200+ dynamically
```

## 🔧 **Updating Your Script**

Should I modify your automation script to:

1. **Check current scope configuration**
2. **Add exclusion ranges** automatically  
3. **Organize reservations** by IP range categories
4. **Create multiple scopes** if desired

This would give you the **network appliance range protection** you want while keeping your current setup manageable!

What's your preference - single scope with exclusions, or multiple scopes for maximum organization?
