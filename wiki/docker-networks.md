<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/docker-networks.md:111 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 1aaff27efa823a1885e8b7227ecd063fbc4cbcdb %
  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
  %ccm_git_commit_count: 111 %
  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: docker updates %
  %ccm_git_modify_date: 2025-10-29 19:12:45 %
  %ccm_git_file_last_modified: 2025-10-29 16:52:04 %
  %ccm_git_file_name: docker-networks.md %
  %ccm_git_path: wiki/docker-networks.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 8381 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
# Docker Networks Inventory
``` 

This page documents the current Docker network state, subnets, and container assignments for TermiteTowers. Use this as a reference to standardize and avoid conflicts when creating new networks or containers.


| Network Name                      | Subnet             | Containers                                      |
|-----------------------------------|--------------------|-------------------------------------------------|
| bridge                           | 172.17.0.0/16      |                                                 |
| dbgate-dev1_default              | 172.30.0.0/16      | dbgate-dev1                                     |
| docker_default                   | 172.18.0.0/16      | lobechat-dev1                                   |
| dozzle-dev1_default              | 172.24.0.0/16      | dozzle-dev1                                     |
| esphome-dev1_default             | 192.168.96.0/20    |                                                 |
| homarr-dev1_default              | 172.25.0.0/16      | homarr-dev1                                     |
| host                             |                    |                                                 |
| kea-dev1_dns-dhcp-net            | 172.29.0.0/24      |                                                 |
| kitchenowl-dev1_default          | 172.22.0.0/16      | kitchenowl-dev1                                 |
| llm-server-dev1_default          | 192.168.32.0/20    | llm-server-dev1                                 |
| lobechat-dev1_default            | 192.168.112.0/20   |                                                 |
| none                             |                    |                                                 |
| openweb-dev1_default             | 192.168.16.0/20    | openwebui-dev1                                  |
| pihole-dev1_default              | 192.168.80.0/20    |                                                 |
| powerdns-dev1_powerdns-net       | 172.33.0.0/24      | powerdns-db-dev1, powerdns-dev1, powerdns-admin-dev1, powerdns-admin-db-dev1, pihole-dev1 |
| prometheus-network               | 192.168.48.0/20    | prometheus-dev1                                 |
| searxng-dev1_default             | 172.27.0.0/16      | searxng-dev1                                    |
| snipeit-dev1_default             | 172.28.0.0/16      | snipeit-db-dev1, snipeit-dev1                   |
| technitium-dns-dev1_technitium-net| 172.31.0.0/24      |                                                 |
| tensorflow-network               | 192.168.64.0/20    | tensorflow-dev1                                 |
| tortoise_default                 | 172.21.0.0/16      |                                                 |
| uptime-kuma-dev1_default         | 172.23.0.0/16      | uptime-kuma-dev1                                |
| vault-dev1_default               | 172.26.0.0/16      |                                                 |
| wikijs_default                   | 172.19.0.0/16      |                                                 |
| wikijs_wikinet                   | 172.20.0.0/16      | wiki_postgres-dev1, wiki_app-dev1               |

## Standardization Guidance
- Choose a subnet not listed above for new networks.
- Group related apps on shared networks for easier management.
- Document new networks and container assignments here after creation.
- Prune unused networks to keep this list clean.

_Last updated: 2025-10-29_

## Current Docker Container to Network Mapping

| Container                | OLD Network Name                  | New Network Name   | OLD Subnet         |
|--------------------------|-----------------------------------|--------------------|--------------------|
| dbgate-dev1              | dbgate-dev1_default               | app-services-net-dev1 | 172.30.0.0/16      |
| lobechat-dev1            | docker_default                    | ai-services-net-dev1 | 172.18.0.0/16      |
| dozzle-dev1              | dozzle-dev1_default               | monitor-apps-net-dev1 | 172.24.0.0/16      |
| homarr-dev1              | homarr-dev1_default               | productivity-apps-net-dev1 | 172.25.0.0/16      |
| kitchenowl-dev1          | kitchenowl-dev1_default           | productivity-apps-net-dev1 | 172.22.0.0/16      |
| llm-server-dev1          | llm-server-dev1_default           | ai-services-net-dev1 | 192.168.32.0/20    |
| openwebui-dev1           | openweb-dev1_default              | ai-services-net-dev1 | 192.168.16.0/20    |
| powerdns-db-dev1         | powerdns-dev1_powerdns-net        | core-infra-net-dev1 | 172.33.0.0/24      |
| powerdns-dev1            | powerdns-dev1_powerdns-net        | core-infra-net-dev1 | 172.33.0.0/24      |
| powerdns-admin-dev1      | powerdns-dev1_powerdns-net        | core-infra-net-dev1 | 172.33.0.0/24      |
| powerdns-admin-db-dev1   | powerdns-dev1_powerdns-net        | core-infra-net-dev1 | 172.33.0.0/24      |
| pihole-dev1              | powerdns-dev1_powerdns-net        | core-infra-net-dev1 | 172.33.0.0/24      |
| prometheus-dev1          | prometheus-network                 | monitor-apps-net-dev1 | 192.168.48.0/20    |
| searxng-dev1             | searxng-dev1_default              | app-services-net-dev1 | 172.27.0.0/16      |
| snipeit-db-dev1          | snipeit-dev1_default              | docs-services-net-dev1 | 172.28.0.0/16      |
| snipeit-dev1             | snipeit-dev1_default              | docs-services-net-dev1 | 172.28.0.0/16      |
| tensorflow-dev1          | tensorflow-network                 | ai-services-net-dev1 | 192.168.64.0/20    |
| uptime-kuma-dev1         | uptime-kuma-dev1_default          | monitor-apps-net-dev1 | 172.23.0.0/16      |
| wiki_app-dev1            | wikijs_wikinet                    | docs-services-net-dev1     | 172.20.0.0/16      |
| wiki_postgres-dev1       | wikijs_wikinet                    | docs-services-net-dev1     | 172.20.0.0/16      |


- Migration Status: Not started = legacy name in use; In use = standardized name adopted; Completed = all containers migrated.

Update this table as networks are renamed and containers are migrated.

## Alphabetical Summary of New Network Names

| New Network Name              | Containers                                             | NEW Subnet         |
|------------------------------|--------------------------------------------------------|--------------------|
| ai-services-net-dev1         | lobechat-dev1, llm-server-dev1, openwebui-dev1, tensorflow-dev1 | 10.10.0.0/20       |
| app-services-net-dev1        | dbgate-dev1, searxng-dev1                              | 10.10.16.0/20      |
| core-infra-net-dev1          | powerdns-db-dev1, powerdns-dev1, powerdns-admin-dev1, powerdns-admin-db-dev1, pihole-dev1 | 10.10.32.0/20      |
| docs-services-net-dev1       | snipeit-db-dev1, snipeit-dev1, wiki_app-dev1, wiki_postgres-dev1 | 10.10.48.0/20      |
| monitor-apps-net-dev1        | dozzle-dev1, prometheus-dev1, uptime-kuma-dev1         | 10.10.64.0/20      |
| productivity-apps-net-dev1   | homarr-dev1, kitchenowl-dev1                           | 10.10.80.0/20      |


## How to Create Docker Networks Manually

If you want to create the dev1 networks without referencing them in a Compose file, run the following commands:

```bash

docker network rm ai-services-net-dev1
docker network rm app-services-net-dev1
docker network rm core-infra-net-dev1
docker network rm docs-services-net-dev1
docker network rm monitor-apps-net-dev1
docker network rm productivity-apps-net-dev1


docker network create --driver bridge --subnet 10.10.0.0/20 --gateway 10.10.0.1 ai-services-net-dev1
docker network create --driver bridge --subnet 10.10.16.0/20 --gateway 10.10.16.1 app-services-net-dev1
docker network create --driver bridge --subnet 10.10.32.0/20 --gateway 10.10.32.1 core-infra-net-dev1
docker network create --driver bridge --subnet 10.10.48.0/20 --gateway 10.10.48.1 docs-services-net-dev1
docker network create --driver bridge --subnet 10.10.64.0/20 --gateway 10.10.64.1 monitor-apps-net-dev1
docker network create --driver bridge --subnet 10.10.80.0/20 --gateway 10.10.80.1 productivity-apps-net-dev1
```

These commands will create all required dev1 networks with the correct subnets and gateways. Reference these network names in your Compose service files to attach containers.

