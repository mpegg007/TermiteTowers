#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
#  %ccm_git_repo: TermiteTowers %
#  %ccm_git_branch: dev1 %
#  %ccm_git_object_id: wiki/snipeit-postgres-migration.md:111 %
#  %ccm_git_author: mpegg %
#  %ccm_git_author_email: mpegg@hotmail.com %
#  %ccm_git_blob_sha: 745be330d9166187ab0dcba42e697f551a8a9d25 %
#  %ccm_git_commit_id: c95decaaa02c45bee627cd315be8d2b7aefd7fc5 %
#  %ccm_git_commit_count: 111 %
#  %ccm_git_commit_date: 2025-10-29 19:12:44 -0400 %
#  %ccm_git_commit_author: mpegg %
#  %ccm_git_commit_email: mpegg@hotmail.com %
#  %ccm_git_commit_message: docker updates %
#  %ccm_git_modify_date: 2025-10-29 19:12:45 %
#  %ccm_git_file_last_modified: 2025-10-08 07:33:20 %
#  %ccm_git_file_name: snipeit-postgres-migration.md %
#  %ccm_git_path: wiki/snipeit-postgres-migration.md %
#  %ccm_git_language_mode: dockerfile %
#  %ccm_git_file_type: text/plain %
#  %ccm_git_file_encoding: us-ascii %
#  %ccm_git_file_eol: CRLF %
#  %ccm_git_exec: no %
#  %ccm_git_size: 4112 %
#  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  
# Migrating Snipe-IT to Host PostgreSQL (snipeit-dev2)

## Overview
This guide covers how to configure a new Snipe-IT Docker container (`snipeit-dev2`) to use a host PostgreSQL database (`ttdb_dev1`) instead of the default MySQL container. It includes Docker Compose changes, PostgreSQL user/role setup, connection security, and optional schema migration steps.

---


## 1. Docker Compose & Custom Image Changes

**IMPORTANT:** The official Snipe-IT Docker image does NOT include the PostgreSQL PHP driver (`php8.3-pgsql`). You MUST build a custom image to use PostgreSQL.

### a. Create a Dockerfile for Snipe-IT with PostgreSQL Support

Create `/mnt/ai_storage/snipeit/Dockerfile` with:

```Dockerfile
FROM snipe/snipe-it:latest
USER root
RUN apt-get update && apt-get install -y php8.3-pgsql
USER docker
```

### b. Update `snipeit-dev2.yml` to Use the Custom Image

```yaml
version: '3.8'
services:
  snipeit:
    build:
      context: /mnt/ai_storage/snipeit
      dockerfile: Dockerfile
    image: snipeit-custom:latest
    container_name: snipeit-dev2
    environment:
      - DB_CONNECTION=pgsql
      - DB_HOST=host.docker.internal  # Or your host IP
      - DB_PORT=5432
      - DB_DATABASE=ttdb_dev1
      - DB_USERNAME=snipeit
      - DB_PASSWORD=snipeitPassword
      - DB_SCHEMA=snipeit
    ports:
      - "3901:80"
    restart: unless-stopped
    # ...other config as needed...
```

---

---

## 2. PostgreSQL User/Role Creation
On your PostgreSQL host, follow these steps:

1. Launch psql as the postgres superuser:
  ```bash
  sudo -u postgres psql
  ```

2. Create the database if it doesn't exist:
  ```sql
  CREATE DATABASE ttdb_dev1;
  ```

3. Connect to the ttdb_dev1 database:
  ```sql
  \c ttdb_dev1
  ```

4. Create the user/role for Snipe-IT:
  ```sql
  CREATE USER snipeit WITH PASSWORD 'snipeitPassword';
  ```

5. Create a dedicated schema owned by snipeit:
  ```sql
  CREATE SCHEMA snipeit AUTHORIZATION snipeit;
  ```

6. Grant usage and create privileges on the schema:
  ```sql
  GRANT USAGE ON SCHEMA snipeit TO snipeit;
  GRANT CREATE ON SCHEMA snipeit TO snipeit;
  ```

7. (Optional) Set the default schema for snipeit user:
  ```sql
  ALTER ROLE snipeit SET search_path = snipeit;
  ```

When Snipe-IT runs migrations, tables will be created in the snipeit schema and owned by snipeit.

---

## 3. PostgreSQL Connection Security

Edit your PostgreSQL `pg_hba.conf` to restrict access for `snipeit`:

```conf
# Example entry for Docker host access
host    ttdb_dev1    snipeit    <docker_host_ip>/32    md5
```

- Reload PostgreSQL config after changes:
  ```bash
  sudo systemctl reload postgresql
  ```

---

## 4. Create Schema (if needed)

If `ttdb_dev1` is a new database, Snipe-IT will create its schema in the `snipeit` schema on first run. If migrating from MySQL:
- Use Snipe-IT's built-in migration tools or export/import data as needed.
- For manual migration, export MySQL data and use a tool like `pgloader` to import into PostgreSQL (targeting the `snipeit` schema).

---

## 5. Export/Import Steps (Optional)

If you need to migrate existing data:
- Export MySQL data:
  ```bash
  mysqldump -u root -p snipeit_db > snipeit_db.sql
  ```
- Use `pgloader` to import (targeting the snipeit schema):
  ```bash
  pgloader snipeit_db.sql postgresql://snipeit:snipeitPassword@localhost/ttdb_dev1
  ```

---

## 6. Final Steps
- Build and start the new container:
  ```bash
  docker compose -f infra/docker/snipeit-dev2.yml build
  docker compose -f infra/docker/snipeit-dev2.yml up -d
  ```
- Verify Snipe-IT connects to PostgreSQL and initializes the schema.
- Log in to Snipe-IT and confirm functionality.
- If you see errors about missing `pdo_pgsql` or database connection, confirm your custom image is built and used.

---


## References
- [Snipe-IT Docker Documentation](https://github.com/snipe/snipe-it)
- [Snipe-IT Official Dockerfile](https://github.com/snipe/snipe-it/blob/master/Dockerfile)
- [PostgreSQL Documentation](https://www.postgresql.org/docs/)
- [pgloader Migration Tool](https://pgloader.io/)

---

*Prepared by GitHub Copilot, October 2025.*
