<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: https://github.com/mpegg007/TermiteTowers.git %
  %ccm_git_branch: main %
  %ccm_git_object_id: infra/docker/MCP-Docker-Setup-Guide.md:97 %
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
# Docker Application Setup - MCP Prompts Guide

This document contains useful MCP prompts for easily adding new Docker applications to the TermiteTowers infrastructure.

## 1. Creating a New Docker App Setup

Use this prompt to create a complete Docker setup for a new application:

```text
Create a new Docker setup for [APP_NAME] in the TermiteTowers infra/docker folder following the existing pattern. 

Requirements:
- Follow the CCM header template from existing files
- Use the naming pattern: [app-name]-dev1.yml
- Include proper logging configuration with 50m max-size and 5 max files
- Mount volumes to /mnt/ai_storage/[app-name]/
- Use port mapping format: "0.0.0.0:[UNIQUE_PORT]:[CONTAINER_PORT]"
- Include env_file reference to ./env/[app-name].env if needed
- Add usage comments at the bottom with mkdir, chown (storage-svc:tt-ai-storage), chmod, and docker compose commands
- Set container name to [app-name]-dev1
- Use restart: unless-stopped

Application details:
- Docker image: [IMAGE_NAME:TAG]
- Default port: [PORT]
- Required volumes: [LIST_VOLUMES]
- Environment variables needed: [LIST_ENV_VARS]
- Any database dependencies: [DB_INFO]
```

## 2. Creating Environment File

Use this prompt to create the corresponding environment file:

```text
Create an environment file template at infra/docker/env/[app-name].env.example for [APP_NAME]. 

Include:
- All required environment variables with descriptions
- Optional variables marked as "# Optional"
- Instructions for generating secrets if needed
- Default values where appropriate
- Comments explaining how to use each setting
```

## 3. Adding Database Support

For apps requiring a database, use this prompt:

```text
Modify the Docker setup for [APP_NAME] to include a [DATABASE_TYPE] database service.

Requirements:
- Use separate database container with name [app-name]-db-dev1
- Use Docker secrets for passwords stored in ./env/[app-name]_mysql_password.txt
- Mount database data to /mnt/ai_storage/[app-name]/[db-type]
- Add depends_on relationship
- Update usage comments to include password generation commands
```

## 4. Port Assignment Guidelines

When adding new applications, use these port ranges:

- 3300-3399: Web applications and dashboards
- 3400-3499: API services
- 3500-3599: Database services (if exposed)
- 3600-3699: Monitoring and logging
- 3700-3799: Development tools
- 3800-3899: Media and content services

## 5. Common Docker Compose Patterns

### Basic Web Application

```yaml
services:
  app-name:
    image: app/image:latest
    container_name: app-name-dev1
    restart: unless-stopped
    ports:
      - "0.0.0.0:33XX:YYYY"
    env_file:
      - ./env/app-name.env
    volumes:
      - /mnt/ai_storage/app-name/data:/app/data
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"
```

### Application with Database

```yaml
services:
  app-db:
    image: postgres:15
    container_name: app-db-dev1
    restart: unless-stopped
    environment:
      - POSTGRES_DB=appname
      - POSTGRES_USER=appname
      - POSTGRES_PASSWORD_FILE=/run/secrets/db_password
    secrets:
      - db_password
    volumes:
      - /mnt/ai_storage/app-name/postgres:/var/lib/postgresql/data

  app:
    image: app/image:latest
    container_name: app-dev1
    restart: unless-stopped
    depends_on:
      - app-db
    ports:
      - "0.0.0.0:33XX:YYYY"
    environment:
      - DATABASE_URL=postgresql://appname@app-db:5432/appname
    secrets:
      - db_password

secrets:
  db_password:
    file: ./env/app_db_password.txt
```

## 6. Standard Usage Commands Template

Always include these commands in the usage comments:

```bash
# Usage:
#   sudo mkdir -p /mnt/ai_storage/[app-name]/{data,logs,config} && \
#   sudo chown -R storage-svc:tt-ai-storage /mnt/ai_storage/[app-name] && \
#   sudo chmod -R u+rwX,g+rwX /mnt/ai_storage/[app-name] && \
#   [ADDITIONAL_SETUP_COMMANDS] \
#   docker compose -f infra/docker/[app-name]-dev1.yml up -d
```

For apps with databases, add password generation:

```bash
#   openssl rand -base64 32 | sudo tee /path/to/password.txt && \
#   sudo chmod 600 /path/to/password.txt && \
```

## 7. Testing New Docker Setup

Use this prompt to verify a new Docker setup:

```text
Test the new Docker setup for [APP_NAME] by:
1. Validating the YAML syntax
2. Checking that all volume paths are correct
3. Verifying port conflicts with existing services
4. Ensuring environment variables are properly referenced
5. Testing the usage commands work correctly
```

## 8. Quick Setup Prompt for Simple Apps

For simple single-container applications:

```text
Create a simple Docker setup for [APP_NAME] using image [IMAGE:TAG], exposing port [PORT] on host port [HOST_PORT], with data volume at /mnt/ai_storage/[app-name]/data, following the TermiteTowers Docker patterns.
```

## 9. Port Conflict Check

Before creating new setups, use this prompt:

```text
Check the TermiteTowers infra/docker folder for existing port assignments and suggest the next available port in the 3300-3399 range for a new [APP_TYPE] application.
```

## 10. Environment File Security Check

Use this prompt to review security of environment files:

```text
Review the environment configuration for [APP_NAME] and identify any sensitive values that should be moved to Docker secrets or external files instead of being in the .env file directly.
```

## 11. Website Setup with Nginx

For applications that need to be accessible via a custom domain, use this prompt:

```text
Create nginx configuration for [APP_NAME] at [SUBDOMAIN].termitetowers.ca that proxies to localhost:[PORT].

Requirements:
- Follow the CCM header template from existing nginx configs
- HTTP to HTTPS redirect on port 80
- SSL configuration using /etc/letsencrypt/live/termitetowers.ca/ certificates
- Proper proxy headers for backend application
- Security headers (X-Frame-Options, X-Content-Type-Options, etc.)
- Appropriate timeout settings for the application type
- Client max body size if file uploads are needed

Save as: infra/nginx/sites-available/[subdomain].conf
```

### Website Setup Process

1. **Create nginx configuration**: Use the prompt above to generate the config file (without .conf extension)
2. **Update Docker environment**: Change APP_URL to https://[subdomain].termitetowers.ca  
3. **Create deployment structure**:

```bash
# Create deployment folder structure following TermiteTowers convention
# Pattern: /srv/dev1/[app-name]/docker/
sudo mkdir -p /srv/dev1/[app-name]/docker
sudo chown -R mpegg-adm:mpegg-adm /srv/dev1/[app-name]

# Create symlink to docker compose file (maintains single source of truth)
ln -s /home/mpegg-adm/source/TermiteTowers/infra/docker/[app-name]-dev1.yml /srv/dev1/[app-name]/docker/

# Copy environment files to deployment location (local overrides)
mkdir -p /srv/dev1/[app-name]/docker/env
cp /home/mpegg-adm/source/TermiteTowers/infra/docker/env/[app-name]* /srv/dev1/[app-name]/docker/env/

# IMPORTANT: Always start from deployment directory, not source
cd /srv/dev1/[app-name]/docker
docker compose -f [app-name]-dev1.yml up -d
```

**Key Points about Deployment Structure:**
- **Source files** live in `/home/mpegg-adm/source/TermiteTowers/infra/docker/`
- **Deployments** run from `/srv/dev1/[app-name]/docker/`  
- **Symlinks** connect deployment to source (single source of truth)
- **Environment files** are copied locally (allows per-deployment customization)
- **Always `cd`** to deployment directory before running docker commands

4. **Deploy nginx configuration**:

```bash
# Copy config to nginx sites-available (without .conf extension)
sudo cp infra/nginx/sites-available/[subdomain].conf /etc/nginx/sites-available/[subdomain]

# Enable the site
sudo ln -sf /etc/nginx/sites-available/[subdomain] /etc/nginx/sites-enabled/

# Test nginx configuration
sudo nginx -t

# Reload nginx
sudo systemctl reload nginx
```

5. **DNS Setup**: Ensure [subdomain].termitetowers.ca points to your server
6. **SSL Certificate**: The wildcard cert for *.termitetowers.ca should already cover the subdomain

### Common Nginx Patterns

#### Basic Web Application Proxy

```nginx
server {
    listen 443 ssl http2;
    server_name [subdomain].termitetowers.ca;

    ssl_certificate     /etc/letsencrypt/live/termitetowers.ca/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/termitetowers.ca/privkey.pem;

    location / {
        proxy_pass http://localhost:[PORT]/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

#### Application with File Uploads

```nginx
server {
    listen 443 ssl http2;
    server_name [subdomain].termitetowers.ca;

    ssl_certificate     /etc/letsencrypt/live/termitetowers.ca/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/termitetowers.ca/privkey.pem;

    # Security headers
    add_header X-Frame-Options SAMEORIGIN;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";

    # Allow larger uploads
    client_max_body_size 100M;

    location / {
        proxy_pass http://localhost:[PORT]/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Extended timeouts for uploads
        proxy_connect_timeout 300;
        proxy_send_timeout 300;
        proxy_read_timeout 300;
    }
}
```

#### WebSocket Support

```nginx
server {
    listen 443 ssl http2;
    server_name [subdomain].termitetowers.ca;

    ssl_certificate     /etc/letsencrypt/live/termitetowers.ca/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/termitetowers.ca/privkey.pem;

    location / {
        proxy_pass http://localhost:[PORT]/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

## 12. Environment Configuration Best Practices

### ⚠️ **CRITICAL: env_file vs environment in Docker Compose**

**DO NOT** use `env_file` for applications that require `.env` files in their container filesystem (like Laravel/PHP apps). The `env_file` directive only sets environment variables - it does not create a `.env` file inside the container.

#### ❌ **WRONG** - For apps that need .env files:
```yaml
services:
  app:
    image: laravel-app:latest
    env_file:
      - ./env/app.env  # This only sets environment variables, doesn't create /var/www/html/.env
```

#### ✅ **CORRECT** - Use direct environment variables:
```yaml
services:
  app:
    image: laravel-app:latest
    environment:
      - APP_KEY=base64:your-key-here
      - DB_HOST=database
      - APP_URL=https://yourapp.domain.com
```

#### ✅ **ALTERNATIVE** - Volume mount for .env file:
```yaml
services:
  app:
    image: laravel-app:latest
    volumes:
      - ./env/app.env:/var/www/html/.env:ro
```

### When to Use Each Approach

- **Use `environment:`** for Laravel, Symfony, and other apps that need .env files
- **Use `env_file:`** for simple apps that only read environment variables
- **Use volume mounts** when you need the exact file present in the container

### Laravel/PHP Specific Notes

1. **APP_KEY Generation**: Always generate proper base64 keys:
   ```bash
   docker exec [container] php artisan key:generate --show
   ```

2. **Cache Clearing**: After changing APP_URL or other config:
   ```bash
   docker exec [container] php artisan config:clear
   docker exec [container] php artisan config:cache
   ```

3. **Database Migrations**: Run after first deployment:
   ```bash
   docker exec [container] php artisan migrate --force
   ```

4. **Storage Permissions**: Fix common Laravel permissions issues:
   ```bash
   docker exec [container] chown -R www-data:www-data /var/www/html/storage
   docker exec [container] chmod -R 755 /var/www/html/storage
   docker exec [container] chown -R www-data:www-data /var/www/html/bootstrap/cache
   docker exec [container] chmod -R 755 /var/www/html/bootstrap/cache
   ```

## 13. Troubleshooting Common Issues

### Container Restart Loops
- **Check logs**: `docker logs [container] --tail 50`
- **Verify environment**: `docker exec [container] printenv | grep APP`
- **Check file mounts**: `docker exec [container] ls -la /path/to/file`

### 502 Bad Gateway (nginx)
1. Check if container is running: `docker ps | grep [app]`
2. Test direct port access: `curl -I http://localhost:[port]`
3. Verify nginx config: `sudo nginx -t`
4. Check nginx logs: `sudo tail -f /var/log/nginx/error.log`

### 🚨 Docker Volume Mount Permission Issues

**CRITICAL:** When containers show file permission errors despite being properly configured:

1. **Don't change container permissions** - the container is likely correct
2. **Check host directory ownership** for mounted volumes
3. **Find container user UID**: `docker exec [container] id [username]`
4. **Fix host directory ownership**: `sudo chown -R [UID]:[GID] /host/mount/path`

**Example from Snipe-IT:**
- Error: "storage directory not writable by web-server"
- Container user: `docker exec snipeit-dev1 ps aux | grep apache` (runs as `docker` user)
- Container UID: `docker exec snipeit-dev1 id docker` (UID 10000, GID 50)
- Fix: `sudo chown -R 10000:50 /mnt/ai_storage/snipeit/logs`

**Why this happens:**
- Docker containers work perfectly internally
- Host volume mounts need matching UIDs between host and container
- Default host directories may be owned by root, www-data, etc.
- Container processes run as different UIDs (often 10000+)

### Database Connection Issues
1. Check if database container is running
2. Verify connection from app container:
   ```bash
   docker exec [app-container] nc -zv [db-container] 3306
   ```
3. Check database logs: `docker logs [db-container]`

## 14. Complete Deployment Workflow

Use this comprehensive prompt for full application deployment:

```text
Create a complete deployment setup for [APP_NAME] including:

1. Docker Compose configuration (following TermiteTowers patterns)
2. Environment file template with all required variables  
3. Nginx configuration for [SUBDOMAIN].termitetowers.ca
4. Complete deployment script with all necessary commands

Application details:
- Docker image: [IMAGE:TAG]
- Port: [PORT]
- Required volumes: [VOLUMES]
- Database: [DB_TYPE if needed]
- Special requirements: [LIST_REQUIREMENTS]

IMPORTANT: If this is a Laravel/PHP app or any app that requires .env files in the container, use direct environment variables instead of env_file.
```

````
