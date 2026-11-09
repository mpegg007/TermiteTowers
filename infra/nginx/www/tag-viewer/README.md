<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: infra/nginx/www/tag-viewer/README.md % -->
<!-- %ccm_git_object_id: infra/nginx/www/tag-viewer/README.md@204 % -->
<!-- %ccm_git_commit_date: 2026-11-09 14:19:49 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: nginx: retire tag-viewer symlinks into AnalAcres; document the publish gap % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# tag-viewer — NOT served from this directory

These assets are **not** in this repository and must not be added here.

- **Served from:** `/var/www/tag-viewer/` — see the `location /tag-viewer/ { alias
  /var/www/tag-viewer/; }` blocks in
  [`immich.conf`](../../sites-available/immich.conf). Nothing in this repo's nginx
  configuration reads `infra/nginx/www/tag-viewer/`, and a search for that path
  returns no hits.
- **Owned by:** the `AnalAcres` repository, directory `tag-viewer/`
  (`inject.js`, `tag-viewer.html`, plus `inject.user.js` which is not published).
- **Published by:** nothing, currently. `/var/www/tag-viewer/` was populated by hand
  and has drifted — as of 2026-11-09 the served `inject.js` is 8132 bytes while the
  source is 9258. AnalAcres's `deploy-prd.yml` only rsyncs to `/srv/prd/aa`, so its
  deploys never reach the serve path.

## Why the symlinks were removed

Until 2026-11-09 this directory held two absolute symlinks into
`/home/mpegg-adm/source/AnalAcres/tag-viewer/`. They made a TermiteTowers checkout
appear to depend on another checkout, pointed at one workstation's absolute path, and
were read by nothing. A sync of this tree would have carried them to a host where the
target does not exist, so they would arrive dangling.

## Intended end state

1. AnalAcres publishes `tag-viewer/` as part of its own deploy.
2. The serve path becomes `/srv/<tier>/www/tag-viewer`, so `uat1` and `prd` cannot
   collide and the deploy record can observe it.
3. `immich.conf` aliases that path. This file goes away, or shrinks to one line
   pointing at the new location.

TermiteTowers owns the vhost. AnalAcres owns the bytes. Neither promotes the other's
files.
