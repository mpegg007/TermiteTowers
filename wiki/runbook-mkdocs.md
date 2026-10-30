<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/runbook-mkdocs.md % -->
<!-- %ccm_git_object_id: wiki/runbook-mkdocs.md@195 % -->
<!-- %ccm_git_commit_date: 2026-10-29 21:42:03 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: mkdocs updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: 2025-12-15 mpegg monday drop -->
<!-- %git_commit_history: Add MkDocs documentation site % -->

# Runbook: MkDocs (dev1)

## Overview
MkDocs Material documentation site serving the TermiteTowers wiki folder. Git-first workflow - edit markdown files directly in the repo, changes appear immediately in dev mode.

## Service Details
- **Subdomain**: docs.termitetowers.ca
- **Host Port**: 3210
- **Container Port**: 8000
- **Category**: Content & Documentation (3200-3299 range)
- **Network**: productivity-apps-net-dev1

## Start/Stop

- Start: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml up -d`
- Logs: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml logs -f`
- Stop: `docker compose -f /home/mpegg-adm/source/TermiteTowers/infra/docker/mkdocs-dev1.yml down`

## Deployment Checklist

Initial setup requires these steps (already completed):

1. ✅ Create data directory: `sudo mkdir -p /mnt/ai_storage/mkdocs/site && sudo chown -R 2001:1006 /mnt/ai_storage/mkdocs`
2. ✅ Start container (see Start command above)
3. ✅ Enable Nginx site: `bash /home/mpegg-adm/source/TermiteTowers/scripts/nginx-enable-site.sh /home/mpegg-adm/source/TermiteTowers/infra/nginx/sites-available/docs.conf docs`
4. ✅ Test Nginx: `sudo nginx -t && sudo systemctl reload nginx`
5. ✅ Deploy chat tile: `bash /home/mpegg-adm/source/TermiteTowers/scripts/deploy-www.sh`
6. ✅ Add DNS CNAME: `docs` -> `imono.termitetowers.ca`
7. ✅ Update wiki/ports.md
8. ✅ Create this runbook

## Mounts
- `/home/mpegg-adm/source/TermiteTowers:/docs` (repo mounted for mkdocs.yml + wiki source files)
- `/mnt/ai_storage/mkdocs/site:/docs/site` (build output cache)

## Configuration
- **mkdocs.yml**: Located at repo root `/home/mpegg-adm/source/TermiteTowers/mkdocs.yml`
- **docs_dir**: Points to `wiki` subfolder
- **Theme**: Material theme with dark/light mode toggle, `font: false` (system font stack, no Google Fonts request)
- **Features**: Navigation tabs, search, code copy, Mermaid diagrams
- **Navigation**: explicit `nav:` with seven tabs. New pages must be added to it or they build unreachable.
- **`navigation.instant` and `navigation.expand` are intentionally absent** — see the comments in `mkdocs.yml`.

## Usage
1. Edit markdown files in `/home/mpegg-adm/source/TermiteTowers/wiki/`
2. **Restart the container to publish the change:**
   `docker restart mkdocs_app-dev1`
3. Access at https://docs.termitetowers.ca (or http://localhost:3210)

Live reload is not reliable here — see "Changes not appearing" under Troubleshooting.
Editing a file and waiting is not enough; the reload build dies and the container keeps
serving the previous build, so you can spend a long time looking at stale pages.

## Production Build
To build the static site for production:
```bash
docker run --rm -v /home/mpegg-adm/source/TermiteTowers:/docs squidfunk/mkdocs-material:latest build
```
Output lands in `site/` inside the container, which is the bind mount
`/mnt/ai_storage/mkdocs/site` on the host. That directory is currently unused: the
running container serves with `mkdocs serve`, not from a build.

## Navigation Structure
Navigation is defined explicitly in `mkdocs.yml` (`nav:`) in seven tabs:

| Tab | Covers |
|---|---|
| Infrastructure | Ports, IP allocation, domains, paths, env vars, storage, backups, TLS, nginx, databases, naming standards |
| Services | One runbook per container, plus Snipe-IT migration |
| Home Assistant | House layout, routines, sensors, dashboards, HA runbooks, ESPHome nodes |
| AI and Voice | Model bases/subjects/trainers, voice architecture, WebUI and ComfyUI, MCP |
| Docker and Dev | Add/decommission an app, compose conventions, scheduler, logging, git automation, VS Code |
| Infra Source | Per-directory notes in `infra/` that live beside the code they describe |

The landing page is `wiki/index.md` (not `README.md`; MkDocs maps `README.md` to the
directory index, so having both makes it drop one of them with a warning).

## Notes
- Runs as user 2001:1006 (storage-svc:tt-ai-storage)
- No database required - pure Git workflow
- Supports Mermaid diagrams, code syntax highlighting, search
- Material theme includes navigation, search, and content features
- Container has access to host via host.docker.internal

## Troubleshooting

### Site renders as unstyled HTML (no colored header, no sidebar, no search box)
This is the theme assets 404ing, not a theme or CSS mistake. `/assets/stylesheets/main.*.css`
returns 404 while `stylesheets/extra.css` returns 200.

Cause: MkDocs adds the theme's own files to the same File collection that `exclude_docs`
filters (`add_files_from_theme` then `set_exclusions` in `mkdocs/commands/build.py`). The
theme's CSS and JS live at source paths like `assets/stylesheets/main.<hash>.min.css`, so a
catch-all `*` in `exclude_docs` excludes Material's stylesheet along with everything else.
The page still renders all the Material markup, which is why it looks like raw HTML with a
sidebar of plain links rather than a 404.

Confirm and fix:
```bash
curl -s https://docs.termitetowers.ca/ | grep -oE 'href="[^"]+\.css[^"]*"'
curl -sI https://docs.termitetowers.ca/assets/stylesheets/main.618322db.min.css   # expect 200
```
The `exclude_docs` block must keep the `!assets/**` negation. Do not remove it while
tightening the Markdown-only rule, and do not put `*` last in the block.

### Log shows FileNotFoundError for infra/nginx/www/tag-viewer/*
Two tracked symlinks under `infra/nginx/www/tag-viewer/` point at a sibling AnalAcres
checkout that is not present on this host. A plain `mkdocs build` survives them; the
`serve` watcher retries and logs the error on every reload. Harmless for the site, noisy
for diagnosis. Fix by pointing the symlinks at a real path or dropping them from git.

### MkDocs fails to start
- Check mkdocs.yml syntax: `docker run --rm -v /home/mpegg-adm/source/TermiteTowers:/docs squidfunk/mkdocs-material:latest build --strict`
- Verify wiki folder exists and has markdown files

### Changes not appearing
Symptom: you edit a page, reload the browser, and still see the old content. The
container keeps serving the build from before your edit.

Cause: the `serve` reload build aborts while copying a static file it cannot read:

```
File ".../mkdocs/structure/files.py", line 485, in copy_file
    utils.copy_file(self.abs_src_path, output_path)
PermissionError: [Errno 13] Permission denied: '/docs/wiki/infra/docker/env/ha-mcp.env'
```

That path is a real secret (`-rw-------`, owned by uid 1000) reachable through the
`wiki/infra` symlink. The first build after a restart succeeds; a reload build uses
`InclusionLevel.is_in_serve` (`mkdocs/commands/build.py` line 259 passes `serve_url`
on reloads), which treats `DRAFT` as included, and the copy then fails on the
unreadable file. When the reload build raises, the served site stays frozen.

Immediate workaround: `docker restart mkdocs_app-dev1` after each edit, then confirm
the change is live with `curl -s https://docs.termitetowers.ca/<page>/ | grep <marker>`.

Real fix, not yet implemented: keep source trees that contain secrets out of
`docs_dir`. Stage only `*.md` into a build directory (rsync or a small entrypoint)
and point `docs_dir` at that, then the exclusion block is defence in depth rather
than the only barrier. The alternative is `mkdocs build` plus serving the output
statically instead of `serve`.

Note: as verified, the live site does not currently publish the secret files
(`/infra/docker/env/ha-mcp.env.example` returns 404) because the reload build aborts
before it can serve them. That is luck, not a control — do not rely on it.

### Navigation not showing files
- Add the file to the correct tab in the `nav:` section of `mkdocs.yml`. Auto-discovery is
  off: a page missing from `nav:` is built but reachable only by direct URL.
- The build log lists pages that exist but are not in `nav:`.

### Port conflict
- Check if 3210 is already in use: `sudo netstat -tlnp | grep :3210`
- See wiki/ports.md for port allocation

## Related Documentation
- [How to Add Docker App](how-to-add-docker-app.md)
- [Compose Conventions](compose-conventions.md)
- [Ports Inventory](ports.md)
- [Nginx Configuration](nginx-configuration.md)
