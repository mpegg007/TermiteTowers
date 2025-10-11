<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: infra/dhcp/docs/SCOPE_STRATEGY.md:97 %
  %ccm_git_author: CCM Maintainer %
  %ccm_git_author_email: ccm@test %
  %ccm_git_blob_sha: c6e37f823b5cd0fac36e29c3b4e5002867697277 %
  %ccm_git_commit_id: f8d51ae7fe101541b1ccd2f91922878ece0bb306 %
  %ccm_git_commit_count: 97 %
  %ccm_git_commit_date: 2025-10-10 20:55:46 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: big update %
  %ccm_git_modify_date: 2025-08-29 07:37:53 %
  %ccm_git_file_last_modified: 2025-08-29 07:37:52 %
  %ccm_git_file_name: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_path: CCM_HEADER_TEMPLATE.txt %
  %ccm_git_language_mode:  %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 659 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: service updates % -->
# DHCP Scope Strategy for Your Network

## 🎯 **The Scope Concept - Simplified**

Think of a DHCP scope as a **"pool of IP addresses"** that the server can hand out automatically. You can:

1. **Define the pool range** (e.g., 192.168.1.100 - 192.168.1.254)
2. **Create exclusions** (remove specific IPs from auto-assignment)
3. **Add reservations** (guarantee specific devices get specific IPs)

## 🏗️ **Your Current Situation**

Based on your network, you likely have:

```
Current Setup (Default):
┌─────────────────────────────────────────────────────┐
│ Single Scope: "LAN"                                │
│ Range: 192.168.1.1 - 192.168.1.254                │
│ Pool: All 254 addresses available for assignment   │
│ Problem: DHCP could assign 192.168.1.1-8 to guests!│
└─────────────────────────────────────────────────────┘
```

## 🎯 **Recommended Strategy: Single Scope + Exclusions**

```
Improved Setup (What we'll implement):
┌─────────────────────────────────────────────────────┐
│ Scope: "LAN"                                       │
│ Range: 192.168.1.1 - 192.168.1.254               │
│                                                    │
│ 🚫 EXCLUSIONS (Never auto-assigned):              │
│    • 192.168.1.1 - 1.9    (Infrastructure)       │
│    • 192.168.1.10 - 1.99  (Servers)              │
│                                                    │
│ ✅ DYNAMIC POOL (Auto-assignment):                │
│    • 192.168.1.100 - 1.254 (155 addresses)       │
│                                                    │
│ 📌 RESERVATIONS (Fixed assignments):              │
│    • Your 63 smart devices get specific IPs       │
└─────────────────────────────────────────────────────┘
```

## 🔒 **Protected Ranges (Your Request)**

### **192.168.1.1 - 1.9: "Network Appliances"**
- **Purpose**: Routers, switches, access points, core infrastructure
- **Policy**: **Never auto-assigned** by DHCP
- **Management**: Manual configuration only
- **Example devices**: 
  - 192.168.1.1 → Main router/gateway
  - 192.168.1.2 → Main switch  
  - 192.168.1.3 → Wi-Fi access point
  - 192.168.1.4-9 → Future infrastructure

### **192.168.1.10 - 1.99: "Server Infrastructure"**  
- **Purpose**: Servers, NAS, containers, critical services
- **Policy**: **Never auto-assigned** by DHCP
- **Management**: Manual or reserved assignments
- **Current devices**:
  - 192.168.1.12 → terminus
  - 192.168.1.32 → (existing device)
  - 192.168.1.85 → homeassistant (could move here)

## 🏠 **Smart Home Range (Your Existing Devices)**

### **192.168.1.100 - 1.199: "Smart Home Devices"**
- **Your current devices**: 40+ smart devices already here
- **Policy**: DHCP reservations (fixed IPs) 
- **Auto-assignment**: Limited (for new smart devices)

## 📱 **Dynamic Client Range**

### **192.168.1.200 - 1.254: "Dynamic Clients"**
- **Purpose**: Laptops, phones, tablets, guests
- **Policy**: Full dynamic assignment
- **Pool size**: 55 addresses (plenty for guests)

## ⚙️ **Implementation Steps**

### **Step 1: Check Current Configuration**
```bash
cd /home/mpegg-adm/source/TermiteTowers/infra/dhcp
./scripts/management/manage-dhcp.sh show-scopes
```

### **Step 2: Add Protection (Exclusions)**
```bash
./scripts/management/manage-dhcp.sh setup-exclusions
```
This will add exclusions for:
- 192.168.1.1-9 (Infrastructure protection)
- 192.168.1.10-99 (Server protection)

### **Step 3: Add Your Device Reservations**
```bash
./scripts/management/manage-dhcp.sh add-all --skip-existing
```

## 🎯 **Benefits of This Approach**

### **✅ Infrastructure Protection**
- **Network appliances (1-8) are safe** - DHCP will never assign these
- **Server range (10-99) protected** - no accidental assignments
- **Critical devices stay stable**

### **✅ Organized Network**
- **Easy troubleshooting**: "192.168.1.5 = network device, 192.168.1.205 = guest"
- **Clear range purposes**: Infrastructure, servers, smart home, guests
- **Scalable**: Room to grow in each category

### **✅ Simple Management**  
- **Single scope to manage** (not multiple scopes)
- **Flexible reservations** can go anywhere in allowed ranges
- **Dynamic pool** handles guests automatically

## 🚀 **Ready to Implement?**

Your network will be organized as:

```
1-9:     🏢 Network Infrastructure (Protected)
10-99:   🖥️  Servers & Services (Protected)  
100-199: 🏠 Smart Home Devices (Your 63 devices - Reserved)
200-254: 📱 Guests & Mobile (Dynamic pool)
```

This gives you the **network appliance range protection** you requested while keeping everything manageable in a single, well-organized scope!

Would you like me to show you your current scope configuration first, or are you ready to implement the exclusions?
