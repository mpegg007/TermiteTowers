<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: infra/docker/README.nextcloud.md:139 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: b629c60ad8b08f78658c29351f1984b723f8b704 %
  %ccm_git_commit_id: 4b7c4d5292241b4ba1eb82f1b2ec0509b8fd544f %
  %ccm_git_commit_count: 139 %
  %ccm_git_commit_date: 2026-03-22 09:03:20 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: march updates %
  %ccm_git_modify_date: 2026-03-22 09:03:21 %
  %ccm_git_file_last_modified: 2026-03-22 09:03:21 %
  %ccm_git_file_name: README.nextcloud.md %
  %ccm_git_path: infra/docker/README.nextcloud.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: utf-8 %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 3739 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
<!-- %git_commit_history: unknown  unknown  unknown  % -->
# Nextcloud Stack (with Host PostgreSQL)

This stack provides Nextcloud file sync and sharing platform connected to the host PostgreSQL database (`ttdb_dev1`). It follows the TermiteTowers standard for Docker app deployment.

## 1. Ports and Networks
- Nextcloud: 3230 (internal 80)
- Network: app-services-net-dev1 (external)
- Database: PostgreSQL on host (ttdb_dev1)

## 2. PostgreSQL Setup on Host
Before starting Nextcloud, create the database and user on your PostgreSQL host:

```bash
sudo -u postgres psql
```

```sql
-- Connect to ttdb_dev1
\c ttdb_dev1

-- Create user and database
CREATE USER nextcloud WITH PASSWORD 'nextcloudPassword';
CREATE DATABASE nextcloud OWNER nextcloud;

-- Connect to nextcloud database
\c nextcloud

-- Grant privileges on public schema
GRANT ALL ON SCHEMA public TO nextcloud;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO nextcloud;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO nextcloud;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO nextcloud;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO nextcloud;

\q
```

### Configure pg_hba.conf for Docker network access
Edit PostgreSQL's pg_hba.conf to allow connections from Docker networks:

```bash
sudo nano /etc/postgresql/16/main/pg_hba.conf
```

Add this line before the local entries:
```
# Docker networks
host    nextcloud    nextcloud    10.10.0.0/16    md5
host    nextcloud    nextcloud    172.17.0.0/16   md5
```

Reload PostgreSQL:
```bash
sudo systemctl reload postgresql
```

## 3. Data Directories
Create and set permissions:

```bash
sudo mkdir -p /mnt/ai_storage/nextcloud/data
sudo mkdir -p /mnt/ai_storage/nextcloud/config
sudo mkdir -p /mnt/ai_storage/nextcloud/custom_apps
sudo chown -R 2001:1006 /mnt/ai_storage/nextcloud
sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/nextcloud
```

## 4. Compose File
- Located at infra/docker/nextcloud-dev1.yml
- Uses env_file: ./env/nextcloud.env (see .env.example)
- Attached to app-services-net-dev1
- Uses `host.docker.internal` to connect to host PostgreSQL

## 5. Secrets
Copy and fill in credentials:

```bash
cp infra/docker/env/nextcloud.env.example infra/docker/env/nextcloud.env
# Edit nextcloud.env with your database and admin passwords
```

## 6. Symlink for /srv/dev1
```bash
sudo mkdir -p /srv/dev1/nextcloud/docker
sudo mkdir -p /srv/dev1/nextcloud/docker/env
sudo ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/nextcloud-dev1.yml /srv/dev1/nextcloud/docker/nextcloud-dev1.yml
sudo ln -sf /home/mpegg-adm/source/TermiteTowers/infra/docker/env/nextcloud.env /srv/dev1/nextcloud/docker/env/nextcloud.env
```

## 7. Start the Stack
```bash
cd /srv/dev1/nextcloud/docker
docker compose -f nextcloud-dev1.yml up -d
```

## 8. Nginx Reverse Proxy
Enable the site:

```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/nextcloud.conf nextcloud
```

## 9. Chat Tile
Deploy the updated chat page:

```bash
bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-www.sh
```

## 10. DNS
Add CNAME record: `nextcloud` → `imono.termitetowers.ca`

## 11. Post-Installation
After first start, configure Nextcloud:
- Log in with admin credentials from env file
- Verify PostgreSQL connection
- Configure trusted domains if needed
- Install recommended apps

## Troubleshooting
- Check container logs: `docker logs nextcloud-dev1`
- Verify PostgreSQL connection from container:
  ```bash
  docker exec nextcloud-dev1 nc -zv host.docker.internal 5432
  ```
- Check Nextcloud admin interface for database status

---

See wiki/how-to-add-docker-app.md for full standards.
