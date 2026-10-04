<!--  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  %
  %ccm_git_repo: TermiteTowers %
  %ccm_git_branch: dev1 %
  %ccm_git_object_id: wiki/runbook-ollama.md:147 %
  %ccm_git_author: mpegg %
  %ccm_git_author_email: mpegg@hotmail.com %
  %ccm_git_blob_sha: 44d6bea22cbe87a163c7232b7cd324c8192d693e %
  %ccm_git_commit_id: 875dba4d1edbc0fb2fe425346b22faa6070d5e41 %
  %ccm_git_commit_count: 147 %
  %ccm_git_commit_date: 2026-06-10 17:10:31 -0400 %
  %ccm_git_commit_author: mpegg %
  %ccm_git_commit_email: mpegg@hotmail.com %
  %ccm_git_commit_message: june bulk update %
  %ccm_git_modify_date: 2026-06-10 17:10:33 %
  %ccm_git_file_last_modified: 2026-06-10 17:10:33 %
  %ccm_git_file_name: runbook-ollama.md %
  %ccm_git_path: wiki/runbook-ollama.md %
  %ccm_git_language_mode: markdown %
  %ccm_git_file_type: text/plain %
  %ccm_git_file_encoding: us-ascii %
  %ccm_git_file_eol: CRLF %
  %ccm_git_exec: no %
  %ccm_git_size: 7222 %
  TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  %  -->
<!--
-->

# Runbook: Ollama (dev1)

## Install
- scripts/system/setup-ollama-dev1.sh (SERVICE_USER/GROUP supported; defaults `ollama:tt-ai-storage`)

## Start/Stop
- Start: `sudo systemctl start ollama-dev1`
- Stop: `sudo systemctl stop ollama-dev1`
- Enable on boot: `sudo systemctl enable ollama-dev1`
- Status/logs: `sudo systemctl status ollama-dev1 -l` and `journalctl -u ollama-dev1 -f`

## Ports
- HTTP API: 0.0.0.0:11434

## Paths
- Binary: `/usr/lib/ollama/bin/ollama` (via the `/usr/lib/ollama` symlink)
- Versions: `/usr/lib/ollama-<version>/` (one dir per installed version)
- WorkingDir/Home: /srv/dev1/ollama
- Models: /mnt/ai_storage/models/ollama (OLLAMA_MODELS)

## Notes
- Open WebUI and Lobe Chat use host.docker.internal:11434
- Service account: `ollama:tt-ai-storage` (shared storage group, GID 1006)

## Troubleshooting
- Permission errors: `sudo chown -R ollama:tt-ai-storage /mnt/ai_storage/models/ollama`
- Check connectivity: `curl http://localhost:11434/api/tags`


## Migrate the existing install (one-time)

The current install predates the versioned layout: the binary is `/usr/bin/ollama`
and its libs are a real directory at `/usr/lib/ollama/`. Repackage them into the
versioned layout once to confirm the symlink mechanism before the first upgrade
(no download required). `mv` is used because both paths live on the same
filesystem under `/usr/lib`.

1. Stop the service:

   ```bash
   sudo systemctl stop ollama-dev1
   ```

2. Get the current version and name the folder:

   ```bash
   /usr/bin/ollama -v          # e.g. "ollama version is 0.32.9"
   VER=0.32.9                  # set to whatever was reported
   ```

3. Move the existing binary and libs into the versioned layout:

   ```bash
   sudo mkdir -p "/usr/lib/ollama-${VER}/bin" "/usr/lib/ollama-${VER}/lib"
   sudo mv /usr/bin/ollama "/usr/lib/ollama-${VER}/bin/ollama"
   sudo mv /usr/lib/ollama "/usr/lib/ollama-${VER}/lib/ollama"
   ```

4. Create the `/usr/lib/ollama` symlink and verify it resolves:

   ```bash
   sudo ln -s "/usr/lib/ollama-${VER}" /usr/lib/ollama
   readlink -f /usr/lib/ollama
   /usr/lib/ollama/bin/ollama -v
   ```

5. Install the updated unit (`ExecStart` now uses the symlink) and restart:

   ```bash
   sudo install -m 0644 /home/mpegg-adm/source/TermiteTowers/infra/systemd/ollama-dev1.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl start ollama-dev1
   systemctl status ollama-dev1 --no-pager
   curl http://localhost:11434/api/tags
   ```

6. Optional: put the `ollama` CLI back on PATH:

   ```bash
   sudo ln -sfn /usr/lib/ollama/bin/ollama /usr/local/bin/ollama
   ```

Once `curl http://localhost:11434/api/tags` returns the tag list, the versioned
layout is working; the next upgrade is just [extract + symlink swap](#upgrade).


## Upgrade

> **Do not run the official installer** (`curl -fsSL https://ollama.com/install.sh | sh`)
> on this host. It creates and enables its own `ollama.service`, which collides with
> `ollama-dev1` on port 11434. Upgrade the binary manually instead.

Each version is installed into its own dir (`/usr/lib/ollama-<version>/`) and the
active version is selected by the `/usr/lib/ollama` symlink. Models live in
`/mnt/ai_storage/models/ollama` and are not touched by an upgrade. The service runs
as `ollama:tt-ai-storage` (`User`/`Group` are set in `ollama-dev1.service`, with a
drop-in override at `/etc/systemd/system/ollama-dev1.service.d/override.conf`).

1. Record the current version:

   ```bash
   /usr/lib/ollama/bin/ollama -v
   ```

2. Stop the service:

   ```bash
   sudo systemctl stop ollama-dev1
   ```

3. Download the version you want and extract it into its own versioned dir
   (set `VER` to the release you want; use `ollama-linux-arm64` on ARM or the
   `-rocm` build on AMD GPUs):

   ```bash
   VER=0.33.0
   sudo curl -L "https://github.com/ollama/ollama/releases/download/v${VER}/ollama-linux-amd64.tar.zst" \
     -o "/tmp/ollama-${VER}.tar.zst"
   sudo mkdir -p "/usr/lib/ollama-${VER}"
   sudo tar --zstd -xf "/tmp/ollama-${VER}.tar.zst" -C "/usr/lib/ollama-${VER}"
   ```

   If `tar --zstd` is unavailable (older GNU tar), use:

   ```bash
   zstd -dc "/tmp/ollama-${VER}.tar.zst" | sudo tar -xf - -C "/usr/lib/ollama-${VER}"
   ```

   This produces `/usr/lib/ollama-${VER}/bin/ollama` and its libs under
   `/usr/lib/ollama-${VER}/lib/ollama/`.

4. Point the `/usr/lib/ollama` symlink at the new version (atomic swap) and
   verify it resolves:

   ```bash
   sudo ln -s "/usr/lib/ollama-${VER}" /usr/lib/ollama.new
   sudo mv -Tf /usr/lib/ollama.new /usr/lib/ollama
   readlink -f /usr/lib/ollama
   /usr/lib/ollama/bin/ollama -v
   ```

   Optional: keep the `ollama` CLI on PATH:

   ```bash
   sudo ln -sfn /usr/lib/ollama/bin/ollama /usr/local/bin/ollama
   ```

5. Start the service and confirm it is healthy:

   ```bash
   sudo systemctl start ollama-dev1
   systemctl status ollama-dev1 --no-pager
   curl http://localhost:11434/api/tags
   ```

6. Reinstall the systemd unit **only** if `infra/systemd/ollama-dev1.service`
   changed in the repo:

   ```bash
   sudo install -m 0644 /home/mpegg-adm/source/TermiteTowers/infra/systemd/ollama-dev1.service /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl restart ollama-dev1
   ```

   The `User=`/`Group=` drop-in is separate, so the service account remains
   `ollama:tt-ai-storage`.

### Rollback

If the new version misbehaves, repoint the symlink at a previous version and
restart — no re-download or reinstall needed:

```bash
sudo ln -s /usr/lib/ollama-0.32.9 /usr/lib/ollama.new
sudo mv -Tf /usr/lib/ollama.new /usr/lib/ollama
sudo systemctl restart ollama-dev1
/usr/lib/ollama/bin/ollama -v
```

Keep old version dirs until you are confident in the new one; remove them when
no longer needed with `sudo rm -rf /usr/lib/ollama-<old-version>`.

### What not to do

- Do not edit `ExecStart` to `ollama start --config ...` — the correct command is
  `/usr/lib/ollama/bin/ollama serve`, and this setup uses environment variables
  (`OLLAMA_HOST`, `OLLAMA_MODELS`) in the unit, not a config file.
- Do not overwrite `/usr/lib/ollama-<version>` for a version that is currently
  selected — extract each release into its own dir so rollback stays possible.
- Do not `chown` `/srv/dev1/ollama` or the models dir to `ollama:ollama` — use
  `ollama:tt-ai-storage` (shared storage group), and models live in
  `/mnt/ai_storage/models/ollama`.
- Do not disable the service during the upgrade; a plain `stop`/`start` is enough.

