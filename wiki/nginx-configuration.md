<!--
TermiteTowers Continuous Code Management Header TEMPLATE
% ccm_modify_date: 2025-09-01 15:47:12 %
% ccm_author: mpegg %
% ccm_author_email: mpegg@hotmail.com %
% ccm_repo: https://github.com/mpegg007/TermiteTowers.git %
% ccm_branch: dev1 %
% ccm_object_id: wiki/nginx-configuration.md:0 %
% ccm_commit_id: unknown %
% ccm_commit_count: 0 %
% ccm_commit_message: unknown %
% ccm_commit_author: unknown %
% ccm_commit_email: unknown %
% ccm_commit_date: 1970-01-01 00:00:00 +0000 %
% ccm_file_last_modified: 2025-09-01 15:47:12 %
% ccm_file_name: nginx-configuration.md %
% ccm_file_type: text/plain %
% ccm_file_encoding: us-ascii %
% ccm_file_eol: CRLF %
% ccm_path: wiki/nginx-configuration.md %
% ccm_blob_sha: 652c0ea1a466a0be5db0d7ea229d5834ebf27b05 %
% ccm_exec: no %
% ccm_size: 2851 %
% ccm_tag:  %
tt-ccm.header.end
-->

# Nginx Configuration for Vault, ESO, and SOPS

## Overview
This document outlines the Nginx configuration for the following services:
- Vault
- ESO
- SOPS

Each service follows the pattern established in `lobe.conf`, including HTTPS support and fully qualified domain names.

## Configuration Details

### Vault
- **File**: `/etc/nginx/sites-available/vault`
- **Symlink**: `/etc/nginx/sites-enabled/vault`
- **Server Name**: `vault.termitetowers.ca`
- **Ports**: Redirects HTTP to HTTPS, listens on 443 for HTTPS.

### ESO
- **File**: `/etc/nginx/sites-available/eso`
- **Symlink**: `/etc/nginx/sites-enabled/eso`
- **Server Name**: `eso.termitetowers.ca`
- **Ports**: Redirects HTTP to HTTPS, listens on 443 for HTTPS.

### SOPS
- **File**: `/etc/nginx/sites-available/sops`
- **Symlink**: `/etc/nginx/sites-enabled/sops`
- **Server Name**: `sops.termitetowers.ca`
- **Ports**: Redirects HTTP to HTTPS, listens on 443 for HTTPS.

## SSL Certificates
All configurations use the following SSL certificates:
- **Certificate**: `/etc/letsencrypt/live/termitetowers.ca/fullchain.pem`
- **Key**: `/etc/letsencrypt/live/termitetowers.ca/privkey.pem`

## Proxy Settings
Each service proxies requests to its respective backend:
- Vault: `http://127.0.0.1:3304`
- ESO: `http://127.0.0.1:3305`
- SOPS: `http://127.0.0.1:3306`

## Example Configuration
Below is an example configuration for Vault:

```nginx
server {
    listen 80;
    server_name vault.termitetowers.ca;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl http2;
    server_name vault.termitetowers.ca;

    ssl_certificate     /etc/letsencrypt/live/termitetowers.ca/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/termitetowers.ca/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:3304;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```
