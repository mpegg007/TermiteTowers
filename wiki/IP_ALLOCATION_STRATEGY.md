<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/IP_ALLOCATION_STRATEGY.md:121 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 751feecbe5f3c9e0e659da19e9ef963b730a251c %
  %ccm_git_commit_id: 4a1cbe1072eb42723822f202e3fcd45247e1aa03 %
  %ccm_git_commit_count: 121 %
  %ccm_git_commit_date: 2025-11-30 12:26:01 -0500 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: cleanup %
  %ccm_git_modify_date: 2025-11-30 12:27:20 %
  %ccm_git_file_last_modified: 2025-11-30 12:27:20 %
  %ccm_git_file_name: IP_ALLOCATION_STRATEGY.md %
  %ccm_git_path: wiki/IP_ALLOCATION_STRATEGY.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 7291 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: november changes % -->
# IP Allocation Strategy

## Purpose
This document defines the authoritative strategy for IP address allocation in the TermiteTowers network. It provides clear ranges for infrastructure, servers, VOIP, WiFi, smart devices, and dynamic clients, so you always know what IP to assign to a new device.

---

## Subnet: 192.168.1.0/24

| Range                | Usage                        | Notes/Examples                      |
|----------------------|------------------------------|-------------------------------------|
| 192.168.1.1          | Default Gateway/Router       | Main router                         |
| 192.168.1.2 - .9     | Core Infrastructure          | Switches, controllers, firewalls    |
| 192.168.1.10 - .49   | Servers                      | NAS, Pi-hole, PowerDNS, Prometheus  |
| 192.168.1.50 - .99   | Reserved (future infra)      | For future expansion                |
| 192.168.1.100 - .149 | VOIP Devices                 | Phones, ATAs (e.g., .100-.110)      |
| 192.168.1.150 - .199 | Smart Home/IoT               | Plugs, bulbs, sensors               |
| 192.168.1.200 - .240 | Dynamic Clients (DHCP Pool)  | Laptops, phones, guests             |
| 192.168.1.241 - .250 | Printers, Cameras            | Static or reserved                  |
| 192.168.1.251 - .253 | WiFi Access Points           | APs (e.g., .251, .252, .253)        |
| 192.168.1.254        | Broadcast                    |                                     |

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
