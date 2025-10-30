<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/docker-networks.md:113 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: ee34580914badde5ffd88946a4e4cf8c77c45855 %
  %ccm_git_commit_id: 8b186f9039f2b3f1503219473a1e2de120c993d1 %
  %ccm_git_commit_count: 113 %
  %ccm_git_commit_date: 2025-10-30 12:44:42 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: commen block updates %
  %ccm_git_modify_date: 2025-10-30 12:44:46 %
  %ccm_git_file_last_modified: 2025-10-30 12:44:46 %
  %ccm_git_file_name: docker-networks.md %
  %ccm_git_path: wiki/docker-networks.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 6623 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: adding secret-service % -->
<!-- %git_commit_history: docker updates % -->
# Docker Networks Inventory
This page documents the current Docker network state, subnets, and container assignments for TermiteTowers. Use this as a reference to standardize and avoid conflicts when creating new networks or containers.

docker network ls --format '{{.Name}}' | xargs -n1 docker network inspect --format '{{.Name}}: {{range .IPAM.Config}}{{.Subnet}}{{end}}'

## Alphabetical Summary of New Network Names

| Network Name                | Subnet           | Containers/Apps Assigned                       |
|-----------------------------|------------------|------------------------------------------------|
| ai-services-net-dev1        | 10.10.0.0/20     | AI-related apps (e.g., LLM, Whisper, TensorFlow)|
| app-services-net-dev1       | 10.10.16.0/20    | General app services (e.g., Mealie, Homarr, KitchenOwl, SnipeIT)|
| core-infra-net-dev1         | 10.10.32.0/20    | Core infrastructure (e.g., DNS, DHCP, Nginx)   |
| docs-services-net-dev1      | 10.10.48.0/20    | Documentation and wiki services                |
| monitor-apps-net-dev1       | 10.10.64.0/20    | Monitoring/logging (e.g., Prometheus, Uptime Kuma, Dozzle)|
| productivity-apps-net-dev1  | 10.10.80.0/20    | Productivity apps (e.g., KitchenOwl, SearxNG)  |
| secret-service-net-dev1     | 10.10.96.0/20    | Vault, SOPS, ESO, other secrets hosting apps   |
| ...                         | ...              | ...                                            |

## Standardization Guidance
- Choose a subnet not listed above for new networks.
- Group related apps on shared networks for easier management.
- Document new networks and container assignments here after creation.
- Prune unused networks to keep this list clean.

_Last updated: 2025-10-30_

## Current Docker Container to Network Mapping

| Container                | New Network Name                  | OLD Network Name   | OLD Subnet         | Status      |
|--------------------------|-----------------------------------|--------------------|--------------------|------------|
| dbgate-dev1              | app-services-net-dev1              | dbgate-dev1_default | 172.30.0.0/16      | Migrated   |
| lobechat-dev1            | ai-services-net-dev1               | docker_default      | 172.18.0.0/16      | Migrated   |
| dozzle-dev1              | monitor-apps-net-dev1              | dozzle-dev1_default | 172.24.0.0/16      | Migrated   |
| homarr-dev1              | productivity-apps-net-dev1         | homarr-dev1_default | 172.25.0.0/16      | Migrated   |
| kitchenowl-dev1          | productivity-apps-net-dev1         | kitchenowl-dev1_default | 172.22.0.0/16      | Migrated   |
| llm-server-dev1          | ai-services-net-dev1               | llm-server-dev1_default | 192.168.32.0/20    | Migrated   |
| mealie-dev1              | productivity-apps-net-dev1         |                     |                    |            |
| openwebui-dev1           | ai-services-net-dev1               | openweb-dev1_default | 192.168.16.0/20    | Migrated   |
| powerdns-db-dev1         | core-infra-net-dev1                | powerdns-dev1_powerdns-net | 172.33.0.0/24      | Migrated   |
| powerdns-dev1            | core-infra-net-dev1                | powerdns-dev1_powerdns-net | 172.33.0.0/24      | Migrated   |
| powerdns-admin-dev1      | core-infra-net-dev1                | powerdns-dev1_powerdns-net | 172.33.0.0/24      | Migrated   |
| powerdns-admin-db-dev1   | core-infra-net-dev1                | powerdns-dev1_powerdns-net | 172.33.0.0/24      | Migrated   |
| pihole-dev1              | core-infra-net-dev1                | powerdns-dev1_powerdns-net | 172.33.0.0/24      | Migrated   |
| prometheus-dev1          | monitor-apps-net-dev1              | prometheus-network   | 192.168.48.0/20    | Migrated   |
| searxng-dev1             | app-services-net-dev1              | searxng-dev1_default | 172.27.0.0/16      | Migrated   |
| snipeit-db-dev1          | docs-services-net-dev1             | snipeit-dev1_default | 172.28.0.0/16      | Migrated   |
| snipeit-dev1             | docs-services-net-dev1             | snipeit-dev1_default | 172.28.0.0/16      | Migrated   |
| tensorflow-dev1          | ai-services-net-dev1               | tensorflow-network   | 192.168.64.0/20    | Migrated   |
| uptime-kuma-dev1         | monitor-apps-net-dev1              | uptime-kuma-dev1_default | 172.23.0.0/16      | Migrated   |
| wiki_app-dev1            | docs-services-net-dev1             | wikijs_wikinet       | 172.20.0.0/16      | Migrated   |
| wiki_postgres-dev1       | docs-services-net-dev1             | wikijs_wikinet       | 172.20.0.0/16      | Migrated   |
| eso-dev1                  | secret-service-net-dev1           |                      |                    |            |
| sops-dev1                 | secret-service-net-dev1           |                      |                    |            |
| vault-dev1                | secret-service-net-dev1           |                      |                    |            |


Status: Not started = legacy name in use; In use = standardized name adopted; Completed = all containers migrated.

Update this table as networks are renamed and containers are migrated.


## How to Create Docker Networks Manually

If you want to create the dev1 networks without referencing them in a Compose file, run the following commands:

```bash

docker network rm ai-services-net-dev1
docker network rm app-services-net-dev1
docker network rm core-infra-net-dev1
docker network rm docs-services-net-dev1
docker network rm monitor-apps-net-dev1
docker network rm productivity-apps-net-dev1
docker network rm secret-service-net-dev1


docker network create --driver bridge --subnet 10.10.0.0/20 --gateway 10.10.0.1 ai-services-net-dev1
docker network create --driver bridge --subnet 10.10.16.0/20 --gateway 10.10.16.1 app-services-net-dev1
docker network create --driver bridge --subnet 10.10.32.0/20 --gateway 10.10.32.1 core-infra-net-dev1
docker network create --driver bridge --subnet 10.10.48.0/20 --gateway 10.10.48.1 docs-services-net-dev1
docker network create --driver bridge --subnet 10.10.64.0/20 --gateway 10.10.64.1 monitor-apps-net-dev1
docker network create --driver bridge --subnet 10.10.80.0/20 --gateway 10.10.80.1 productivity-apps-net-dev1
docker network create --driver bridge --subnet 10.10.96.0/20 --gateway 10.10.96.1 secret-service-net-dev1
```

These commands will create all required dev1 networks with the correct subnets and gateways. Reference these network names in your Compose service files to attach containers.

