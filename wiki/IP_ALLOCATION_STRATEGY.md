<!--||  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
||  %ccm_git_repo: TermiteTowers %
||  %ccm_git_branch: dev1 %
||  %ccm_git_object_id: wiki/IP_ALLOCATION_STRATEGY.md:136 %
||  %ccm_git_author: Matthew Pegg %
||  %ccm_git_author_email: mpegg@hotmail.com %
||  %ccm_git_blob_sha: 796cc2338d1aba608c00976d7ae0c8437b900f13 %
||  %ccm_git_commit_id: bc247a4e65bdd9936cbca62c9b8ae30ec02c3198 %
||  %ccm_git_commit_count: 136 %
||  %ccm_git_commit_date: 2026-03-01 12:34:10 -0500 %
||  %ccm_git_commit_author: Matthew Pegg %
||  %ccm_git_commit_email: mpegg@hotmail.com %
||  %ccm_git_commit_message: flaresolver startup script fix %
||  %ccm_git_modify_date: 2026-03-01 12:34:18 %
||  %ccm_git_file_last_modified: 2026-03-01 12:34:18 %
||  %ccm_git_file_name: IP_ALLOCATION_STRATEGY.md %
||  %ccm_git_path: wiki/IP_ALLOCATION_STRATEGY.md %
||  %ccm_git_language_mode: markdown %
||  %ccm_git_file_type: text/plain %
||  %ccm_git_file_encoding: utf-8 %
||  %ccm_git_file_eol: CRLF %
||  %ccm_git_exec: no %
||  %ccm_git_size: 13223 %
||  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % 
|| ##COMMIT_HISTORY: %git_commit_history: $DATE $AUTHOR $MESSAGE % -->
<!--|| %git_commit_history:   %ccm_git_commit_message: flaresolver startup script fix % -->
<!-- %git_commit_history: november changes % -->
# IP Allocation Strategy

## Purpose
This document defines the authoritative strategy for IP address allocation in the TermiteTowers network. It provides clear ranges for infrastructure, servers, VOIP, WiFi, smart devices, and dynamic clients, so you always know what IP to assign to a new device.

---

## Network Topology
- **Subnet:** 192.168.1.0/24
- **Gateway:** 192.168.1.1
- **Broadcast:** 192.168.1.255
- **DHCP Pool:** 192.168.1.200-.240 (dynamic), all other IPs are reserved or static
- **Philosophy:** IPs never change when devices are moved or renamed

---

## Subnet: 192.168.1.0/24

| Range                | Usage                        | Notes/Examples                      |
|----------------------|------------------------------|-------------------------------------|
| 192.168.1.1          | Default Gateway/Router       | rt01-nexus-main                     |
| 192.168.1.2 - .9     | Core Infrastructure          | Switches, controllers, firewalls    |
| 192.168.1.10 - .49   | Servers                      | NAS, Pi-hole, PowerDNS, Prometheus  |
| 192.168.1.50 - .84   | Reserved / Future Expansion  | Available for servers or IoT growth |
| 192.168.1.85         | **Home Assistant (hal)**      | **NEVER CHANGE** - critical system  |
| 192.168.1.86 - .99   | Reserved / Future Expansion  | Available for servers or IoT growth |
| 192.168.1.100 - .149 | VOIP Devices                 | Phones, ATAs (e.g., .100-.110)      |
| 192.168.1.150 - .199 | Smart Home/IoT               | Plugs, bulbs, sensors, ESP32 nodes  |
| 192.168.1.200 - .240 | Dynamic Clients (DHCP Pool)  | Laptops, phones, guests             |
| 192.168.1.241 - .250 | Printers, Cameras            | Static or reserved                  |
| 192.168.1.251 - .253 | WiFi Access Points           | APs                                 |
| 192.168.1.254        | Main Switch                  | sw01-stellar-main                   |
| 192.168.1.255        | Broadcast (not assignable)   |                                     |

> **Note:** .85 (Home Assistant / hal) is a permanent exception pinned in the reserved range.
> It must never be reassigned or changed - the entire home automation stack depends on it.

---

## General Rules
- **Gateways, DNS, DHCP servers:** Always use a fixed IP in the infrastructure or server range.
- **VOIP Devices:** Assign from 192.168.1.100 upward (e.g., .100, .101, .102, ...).
- **WiFi Access Points:** Use 192.168.1.251, .252, .253.
- **Dynamic clients:** Use DHCP pool 192.168.1.200-240.
- **Reservations:** Use DHCP reservations for any device that must always get the same IP.
- **Never assign static IPs from the dynamic pool.**

> **Note:**
> Only addresses in the range **192.168.1.200–249** are dynamically assigned by DHCP. All other addresses (below 200 and above 249) must be reserved (via DHCP reservation) or statically assigned. These should never be handed out dynamically to avoid conflicts with infrastructure, servers, VOIP, APs, and other critical devices.

---

## Example Assignments
- New switch: 192.168.1.3 (if available)
- New VOIP phone: 192.168.1.104
- New WiFi AP: 192.168.1.252
- New server: 192.168.1.12
- New smart plug: 192.168.1.151

---

## DHCP Scope Configuration
- **Scope:** 192.168.1.1 - 192.168.1.254
- **Exclusions:** 1-199, 241-254 (reserved for static/fixed)
- **DHCP Pool:** 200-240
- **Reservations:** For all infrastructure, servers, VOIP, APs, printers, etc.

---

## Name Servers
- Use internal DNS (e.g., Pi-hole, PowerDNS) at fixed IPs in the server range.

---

## Updating This Document
If you add a new device type or subnet, update this doc so everyone knows the correct range to use.

---

## See Also
- [PORTS_STRATEGY.md](./PORTS_STRATEGY.md)
- [DHCP_SCOPES_EXPLAINED.md](../infra/dhcp/docs/DHCP_SCOPES_EXPLAINED.md)
- [Device-Naming-Standard.md](./Device-Naming-Standard.md)

---

## Device Type Reference Table

| Device Type         | Typical Role/Function                | Example Devices                | Recommended IP Range         |
|---------------------|--------------------------------------|-------------------------------|------------------------------|
| Gateway/Router      | Main network gateway, routing, NAT   | pfSense, Ubiquiti EdgeRouter  | 192.168.1.1                  |
| Switch              | Layer 2/3 switching, VLANs           | Netgear, Cisco, TP-Link       | 192.168.1.2–1.5              |
| Controller          | Network management, AP control       | UniFi Controller, Omada       | 192.168.1.6–1.9              |
| Firewall            | Security, traffic filtering          | pfSense, OPNsense             | 192.168.1.2–1.5 (if separate)|
| Server              | Core services, DNS, DHCP, NTP, etc.  | Pi-hole, PowerDNS, NAS        | 192.168.1.10–1.49            |
| VOIP ATA/Phone      | Voice gateway, SIP/RTP endpoints     | Grandstream, Cisco ATA        | 192.168.1.100–1.110          |
| WiFi Access Point   | Wireless client access               | UniFi AP, TP-Link EAP         | 192.168.1.251–1.253          |
| Printer/Camera      | Printing, surveillance               | HP LaserJet, Reolink          | 192.168.1.241–1.250          |
| Smart Home/IoT      | Automation, sensors, plugs, bulbs    | GlobePlug, Sonoff, Shelly     | 192.168.1.150–1.199          |
| Home Automation Hub | Central automation controller        | Home Assistant (hal)          | 192.168.1.85 (**pinned**)    |
| Dynamic Client      | Laptops, phones, guests              | Windows, Mac, iPhone, Android | 192.168.1.200–1.249 (DHCP)   |

---

## Network Device Roles Explained

- **Router:** Directs traffic between different networks (e.g., LAN and internet) using IP addresses. Most home routers also include basic firewall features.
- **Firewall:** Controls which traffic is allowed or blocked between networks, based on rules. Dedicated firewalls (like pfSense, OPNsense) offer advanced filtering, VPN, IDS/IPS, etc. Many routers have built-in firewalls, but a dedicated firewall is more powerful and flexible.
- **Switch:** Connects devices within the same network (LAN) and forwards traffic based on MAC addresses. Managed switches allow VLANs, port mirroring, QoS, and sometimes limited routing.
- **Controller:** Manages and configures multiple network devices (e.g., UniFi Controller for APs and switches). Not a network device itself, but a management platform.
- **Gateway:** The device that acts as the “exit” point from your LAN to other networks (usually the internet). In most setups, the router is the gateway. In mesh systems (like Eero), the main unit may combine switch, router, firewall, and gateway roles.

**Overlap:**
- Many devices combine these roles (e.g., a home router is often a router, firewall, switch, and gateway in one box).
- Mesh systems (Eero, etc.) often combine switch, router, firewall, and gateway.
- pfSense/OPNsense can be router, firewall, and gateway.

**Summary Table:**

| Role         | Main Function                        | Can be combined with |
|--------------|--------------------------------------|---------------------|
| Router       | Moves traffic between networks       | Firewall, Gateway   |
| Firewall     | Controls/filters traffic            | Router, Gateway     |
| Switch       | Connects devices within a network   | Router (in one box) |
| Controller   | Manages network devices             | (Mgmt only)         |
| Gateway      | Network “way out” (usually router)  | Router, Firewall    |

---

## Recommended Management IP Allocation Scheme

- **Controllers:** 192.168.1.7, .8, .9 (up to 3 management platforms; e.g., UniFi, Omada, lab/test controller)
- **Firewalls:** 192.168.1.2, .3, .4 (ascending order)
- **Switches:** 192.168.1.6, .5, .4 (descending order; .4 is the overlap if needed)

> This scheme allows for clear separation, easy identification, and future growth. The overlap at .4 is intentional for flexibility if you ever need to repurpose or reassign a device.

---

> **Note:**
> VOIP ATAs/phones are not considered core infrastructure, so they are assigned from the 100+ range. This makes firewall and QoS rules easier to manage and keeps infrastructure addresses reserved for networking equipment.


### **192.168.1.10 - 1.99: "Server Infrastructure"**  
**Purpose**: Servers, NAS, containers, critical services
**Policy**: **Never auto-assigned** by DHCP
**Management**: Manual or reserved assignments
**Current devices**:

#### Suggested Server Allocation Table (192.168.1.10–1.49)

| IP Address      | Purpose/Reservation         | Notes                        |
|-----------------|----------------------------|------------------------------|
| 192.168.1.10-19 | Physical Servers           | Dedicated hardware           |
| 192.168.1.20    | Reserved (future use)      | Buffer for expansion         |
| 192.168.1.21-23 | DHCP Servers               | Primary, backup, expansion   |
| 192.168.1.24-25 | NTP Servers                | Primary, backup              |
| 192.168.1.26-28 | DNS Servers                | Primary, secondary, tertiary |
| 192.168.1.29-31 | Database Servers           | Primary, replica, expansion  |
| 192.168.1.32-34 | Web Servers                | Main, backup, staging        |
| 192.168.1.35-37 | App Servers                | Application frontends, microservices |
| 192.168.1.38-39 | NAS/Storage                | File servers                 |
| 192.168.1.40-42 | Reserved (future use)      | Buffer for growth            |
| 192.168.1.40-49 | Reserved (misc servers)    |                              |
You can adjust the categories and reservations as needed for your environment. This approach gives you:

- Dedicated slots for core infrastructure (DNS, DHCP, NTP, web, database, NAS)
- Room for future servers and easy expansion
- Clear separation of roles for easier management and troubleshooting
- Flexibility to adjust as your environment grows

---

## Current Device Assignments

### Infrastructure
| IP Address       | Device              | Hostname              | Notes                      |
|------------------|---------------------|-----------------------|----------------------------|
| 192.168.1.1      | Primary Router      | rt01-nexus-main       | Gateway                    |
| 192.168.1.2-8    | Core Infrastructure | -                     | Reserved for network gear  |
| 192.168.1.251    | Wireless AP #3      | ap03-apollo-garage    | Access Point 3             |
| 192.168.1.252    | Wireless AP #2      | ap02-vega-workshop    | Access Point 2             |
| 192.168.1.253    | Wireless AP #1      | ap01-hermes-office    | Access Point 1             |
| 192.168.1.254    | Main Switch         | sw01-stellar-main     | Primary network switch     |

### Servers & Critical Systems
| IP Address       | Device              | Hostname              | Notes                      |
|------------------|---------------------|-----------------------|----------------------------|
| 192.168.1.85     | Home Assistant VM   | hal (vm-haos-hal)     | **NEVER CHANGE**           |

### ESP32 / IoT Nodes
ESP32 devices are assigned sequentially starting from .101 as they come online:

| IP Address       | Device Name   | Purpose                        | Status               |
|------------------|---------------|--------------------------------|----------------------|
| 192.168.1.101    | esp32-node01  | Primary test bed (all sensors) | Assigned             |
| 192.168.1.102    | esp32-node02  | Secondary test bed (bedroom)   | Assigned             |
| 192.168.1.103    | esp32-node03  | New device #1                  | Ready for assignment |
| 192.168.1.104    | esp32-node04  | New device #2                  | Ready for assignment |
| 192.168.1.105    | esp32-node05  | New device #3                  | Ready for assignment |
| 192.168.1.106+   | esp32-node06+ | Future ESP32 devices           | Available            |

---

## New Device Workflow
1. **Device comes online** - gets temporary DHCP IP from dynamic pool
2. **Determine appropriate range** - match device type to the allocation table above
3. **Assign next available IP** in the correct range
4. **Create DHCP reservation** - device gets the same IP every time
5. **Document assignment** - update this file

---

## Capacity Planning

### Current Utilization
- **Infrastructure (1-9, 251-254):** ~8 used / 12 available
- **Servers (10-49):** 1 used / 40 available
- **IoT/Smart Home (150-199):** ~2 used / 50 available
- **DHCP Dynamic (200-240):** 41 addresses for guests/transient devices

### Growth Projections
- Server capacity of 40 slots is generous for a home lab
- IoT capacity of 50+ supports significant smart home expansion
- 41-address DHCP pool is adequate for dynamic clients

---

## Future Considerations
- **Additional subnets:** 192.168.2.x for guest network isolation
- **VLAN segmentation:** Separate IoT traffic from servers
- **IPv6:** Dual-stack for future-proofing

### Migration Planning
If network restructuring becomes necessary:
1. Plan during low-usage periods
2. Update all DHCP reservations simultaneously
3. Update device configurations as needed
4. Test critical systems (especially Home Assistant at .85)
