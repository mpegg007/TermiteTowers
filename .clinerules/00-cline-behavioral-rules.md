<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: .clinerules/00-cline-behavioral-rules.md:171 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: a5e4d824fd38360b015308bda60f85591d6d4700 % -->
<!-- %ccm_git_commit_id: ee3eae8346d8982d0467de7e5b42579865765a24 % -->
<!-- %ccm_git_commit_count: 171 % -->
<!-- %ccm_git_commit_date: 2026-10-04 16:25:37 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: cleanup % -->
<!-- %ccm_git_modify_date: 2026-10-04 16:25:37 % -->
<!-- %ccm_git_file_last_modified: 2026-10-04 12:24:12 % -->
<!-- %ccm_git_file_name: 00-cline-behavioral-rules.md % -->
<!-- %ccm_git_path: .clinerules/00-cline-behavioral-rules.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 938 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Cline Behavioral Rules - DO NOT EDIT WITHOUT REVIEW

## Home Assistant (HAL)

- When the user mentions HAL, Home Assistant, TermiteTowers, or the `hal-mcp` tools, read `hams/docs/hal-context.md` first (instance snapshot: topology, sensor naming, add-on/integration stack, automation inventory, gotchas).
- `hams/docs/SKILL.md` is the HA development skill — use it for how-to guidance on sensors, dashboards, and integrations.
- Never trust cached states from docs — always query live entity/device/add-on state via the `hal-mcp` tools before acting.

## Data sources (MCP → databases)

- `pg-query-ttdb__*` = main Postgres DB (network/home): `dhcp_history`, `kea`, `watchyourlan`, `water_meter`, `powerdns`, `nextcloud`, `snipeit`.
- `pg-query-ttphoto__*` = photo-library DB: `images`, `image_tags`, `tag_history`, `stacks`.
- Join HAL ↔ DB on `mac_address` / `ip_address` / `hostname` (full map in `hams/docs/hal-context.md`).
