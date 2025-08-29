# Paths and Symlinks (dev1)

## Compose files
- Source: `/home/mpegg-adm/source/TermiteTowers/docker/*-dev1.yml`
- Symlinks: `/srv/dev1/<service>/docker/*-dev1.yml`

### Symlink/layout (Mermaid)
```mermaid
flowchart TD
	A[/srv/dev1/<service>/docker/*-dev1.yml/] -->|symlink| B[/home/mpegg-adm/source/TermiteTowers/docker/*-dev1.yml/]
	subgraph Data [/mnt/ai_storage/]
		HF[huggingface]
		PIP[pip]
		TORCH[torch]
		WIKI[wiki/*]
		TORT[tortoise/*]
	end
```

## Key data dirs
- `/mnt/ai_storage/models/huggingface`
- `/mnt/ai_storage/models/pip`
- `/mnt/ai_storage/models/torch`
- `/mnt/ai_storage/models/whisper`
- `/mnt/ai_storage/openwebui/data`
- `/mnt/ai_storage/tortoise/voices`
- `/mnt/ai_storage/tortoise/outputs`
- `/mnt/ai_storage/wiki/postgres-data`
- `/mnt/ai_storage/wiki/wikijs-data`

## Ownership & perms
- `storage-svc:tt-ai-storage`, mode `2775` dirs, default ACLs grant group rwx

## Quick checks
- `id storage-svc` and `getent group tt-ai-storage`
- `getfacl -p /mnt/ai_storage/<dir>`
- `docker run --rm -u 2001:1006 -v /mnt/ai_storage/tortoise/outputs:/out busybox sh -lc 'umask 002; echo ok > /out/test.txt; ls -l /out/test.txt'`
