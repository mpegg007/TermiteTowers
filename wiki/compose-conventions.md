# Docker Compose Conventions (dev1)

Applies to files in `TermiteTowers/docker/*-dev1.yml`.

## Common keys
- `user: "${UID_SVC:-2001}:${GID_TT_AI:-1006}"` to write as storage-svc:tt-ai-storage
- `extra_hosts: ["host.docker.internal:host-gateway"]` to reach services on host
- `restart: unless-stopped`
- `logging: { driver: json-file, options: { max-size: "50m", max-file: "5" } }`

## Caches and models
- Mount model caches under `/cache/*`:
  - `/mnt/ai_storage/models/huggingface:/cache/huggingface`
  - `/mnt/ai_storage/models/pip:/cache/pip`
  - `/mnt/ai_storage/models/torch:/cache/torch`
- For app-specific models:
  - Whisper: `/mnt/ai_storage/models/whisper:/app/models`

## Umask & init
- Use `bash -lc "umask 002 && <init> && <command>"` pattern when a service writes files.

## Ports
- Bind explicitly: `"0.0.0.0:HOST:CONTAINER"` for clarity on Linux.

### Network/ports map (Mermaid)
```mermaid
flowchart LR
  Browser -->|3000| OpenWebUI
  Browser -->|3100| LobeChat
  Browser -->|3200| WikiJS
  OpenWebUI -. host.docker.internal:11434 .-> Ollama[(Ollama on host)]
  LobeChat -. host.docker.internal:11434/v1 .-> Ollama
```

## Paths & symlinks
- Dev1 symlink pattern:
  - `/srv/dev1/<service>/docker/<name>-dev1.yml -> /home/mpegg-adm/source/TermiteTowers/docker/<name>-dev1.yml`

## Examples
- See `openweb-dev1.yml`, `lobechat-dev1.yml`, `tortoise-dev1.yml`, `whisper-dev1.yml`, `wiki-dev1.yml` for concrete patterns.
