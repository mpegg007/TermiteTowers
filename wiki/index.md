<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/index.md % -->
<!-- %ccm_git_object_id: wiki/index.md@195 % -->
<!-- %ccm_git_commit_date: 2026-10-29 21:42:03 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: mkdocs updates % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
<!-- %git_commit_history: Rebuild MkDocs site as a navigable, themed documentation hub -->

# TermiteTowers Operations Documentation

Operational documentation for the TermiteTowers host: how each service is deployed,
which port and subdomain it owns, and what to do when it breaks.

Everything here is Markdown in the repository under `wiki/`. Edit the file, save it,
and the page refreshes — there is no CMS and no database.

## Start here

<div class="grid cards" markdown>

- __Infrastructure__

    ---

    Ports, IP allocation, storage model, backups, TLS and the reverse proxy.

    [Open Infrastructure](tech-context.md)

- __Services__

    ---

    One runbook per container: how to start it, stop it, and diagnose it.

    [Browse runbooks](runbook-mkdocs.md)

- __Home Assistant__

    ---

    House layout, routines, sensors, dashboards and the ESPHome node fleet.

    [Open Home Assistant](hams/docs/house-layout.md)

- __AI and Voice__

    ---

    Ollama, Whisper, Piper, Tortoise, model bases and MCP integrations.

    [Open AI and Voice](voice-assistant-architecture.md)

- __Docker and Dev__

    ---

    Adding an app, compose conventions, logging, git automation and hooks.

    [Open Docker and Dev](how-to-add-docker-app.md)

- __Infra Source__

    ---

    Per-directory notes that live next to the code they describe.

    [Open Infra Source](infra/README.md)

</div>

## Conventions used here

| Thing | Where it is decided |
|---|---|
| Port and subdomain | [Ports](ports.md) is the authoritative inventory |
| Host naming | [Device Naming Standard](Device-Naming-Standard.md) |
| Service unit names | [Systemd Naming Standard](systemd-naming-standard.md) |
| Compose layout | [Compose Conventions](compose-conventions.md) |
| Where data lives | [Paths and Symlinks](paths-and-symlinks.md) |

## About this site

The site is MkDocs with the Material theme, served from a container on host port
**3210** and published at `docs.termitetowers.ca`. The configuration lives in
[`mkdocs.yml`](https://github.com/mpegg/TermiteTowers/blob/dev1/mkdocs.yml) at the
repository root, and the sources are the `wiki/` tree.

Deployment, troubleshooting and the reason the theme assets once failed to load are
documented in the [MkDocs runbook](runbook-mkdocs.md).
