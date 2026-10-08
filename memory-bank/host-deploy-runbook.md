<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_object_id: memory-bank/host-deploy-runbook.md:171 % -->
<!-- %ccm_git_author: mpegg % -->
<!-- %ccm_git_author_email: mpegg@hotmail.com % -->
<!-- %ccm_git_blob_sha: 387354368bd57be9da363d312103820a14bfc8e0 % -->
<!-- %ccm_git_commit_id: ee3eae8346d8982d0467de7e5b42579865765a24 % -->
<!-- %ccm_git_commit_count: 171 % -->
<!-- %ccm_git_commit_date: 2026-10-04 16:25:37 -0400 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_email: mpegg@hotmail.com % -->
<!-- %ccm_git_commit_message: cleanup % -->
<!-- %ccm_git_modify_date: 2026-10-04 16:25:37 % -->
<!-- %ccm_git_file_last_modified: 2026-10-04 12:36:40 % -->
<!-- %ccm_git_file_name: host-deploy-runbook.md % -->
<!-- %ccm_git_path: memory-bank/host-deploy-runbook.md % -->
<!-- %ccm_git_language_mode: markdown % -->
<!-- %ccm_git_file_type: text/plain % -->
<!-- %ccm_git_file_encoding: utf-8 % -->
<!-- %ccm_git_file_eol: CRLF % -->
<!-- %ccm_git_exec: no % -->
<!-- %ccm_git_size: 19598 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Host deploy runbook — bootstrapping a `<svc>-deploy` runner + `/srv/<env>/<svc>` prod dir

> How to stand up a **new** GitHub Actions self-hosted runner and its production
> directory on `monolith` for a fresh repo — generalized from the three already
> live (`jah`, `tt`, `aa`). Also the reference for replicating the pattern to a
> second environment (`/srv/dev2`, `/srv/uat1`).
>
> Everything below was re-verified live on `monolith` on 2026-10-04. Where a fact
> is an *assumption* rather than a verified one, it is called out inline.
> **No credentials in this file** — the runner registration token is single-use
> and expires in ~1 hour; mint a fresh one each time (§4).

## 1. Naming contract

Pick the placeholders once, then every path/unit/label in this doc is mechanical.

| Placeholder | Meaning | Live values on `monolith` |
| ----------- | ------- | ------------------------- |
| `<svc>`     | short service key; also the prod dir name | `jah`, `tt`, `aa` |
| `<USER>`    | per-service deploy user | `jah-deploy` (uid 2005), `tt-deploy` (2006), `aa-deploy` (2007) → next free **2008** |
| `<owner>`   | GitHub user/org | `mpegg007` |
| `<REPO>`    | GitHub repo name (case matters for the unit) | `JustAnotherHuman`, `TermiteTowers`, `AnalAcres` |
| `<X>`       | runner label prefix, used in `runs-on` | `jah-prd`, `tt-prd`, `aa-prd` |
| `<br>`      | trigger branch | `prd` (all three) |
| `<env>`     | environment tier in the path | `prd` (today); `dev2`/`uat1` when replicated |

### Resulting paths

| Thing | Path |
| ----- | ---- |
| Prod directory (deploy target) | `/srv/prd/<svc>` |
| Runner install dir | `/srv/prd/<svc>-actions-runner` |
| systemd unit | `/etc/systemd/system/actions.runner.<owner>-<REPO>.monolith.service` |
| Runner metadata | `<runnerdir>/.runner`, `.credentials`, `.path`, `.env`, `.service` |
| Checkout work tree | `<runnerdir>/_work/<REPO>/<REPO>` |
| Runner diagnostics | `<runnerdir>/_diag/Worker_*.log`, `Runner_*.log` |
| Prod venv (hand-made, reused) | `/srv/prd/<svc>/.venv` |
| Shared runner tarball | `/srv/prd/actions-runner-linux-x64-2.337.0.tar.gz` |

> **Naming drift to be aware of:** JAH predates the `<svc>-actions-runner`
> convention — its runner dir is `/srv/prd/actions-runner` (no prefix). TT and AA
> follow the convention. New runners should use `/srv/prd/<svc>-actions-runner`.
> The unit hardcodes the absolute path (captured at `svc.sh install` time), so the
> mismatch is invisible until you go looking. See §8.3.

## 2. The two deploy models

### Model A — rsync-of-checkout (**this is what all three repos use today**)

The workflow checks the repo out into the runner's own work tree, then rsyncs it
onto the prod dir. Prod stays a *mirror of the approved commit*, not a git repo.

```yaml
- uses: actions/checkout@v4                     # -> <runnerdir>/_work/<REPO>/<REPO>
- name: Synchronize approved revision
  run: >-
    rsync -a --delete --exclude=.env --exclude=.venv --exclude=.git
    "$GITHUB_WORKSPACE/" /srv/prd/<svc>/
```

Consequences to keep in mind:

- `--delete` **mirrors deletions** into prod. Anything not in the repo and not
  excluded gets removed from `/srv/prd/<svc>`.
- The three excludes are load-bearing: `.env` (prod secrets), `.venv` (the
  hand-made virtualenv), `.git` (prod is not a checkout).
- The **runner user must own** `/srv/prd/<svc>` — rsync runs as `<USER>`.

### Model B — clone-into-place (documented alternative, *not in use*)

Prod *is* a git checkout; the workflow fast-forwards it:

```yaml
- run: |
    git -C /srv/prd/<svc> fetch --prune origin
    git -C /srv/prd/<svc> reset --hard "origin/<br>"
```

Advantages: no `--delete` blast radius, prod can be inspected with plain git.
Cost: you must keep `.env`/`.venv` untracked and `.gitignore`d, and the deploy
user owns the checkout. **Not currently used by any repo** — listed only because
it is the natural choice when a service needs git metadata at runtime.

## 3. One-time host bootstrap

All commands are `sudo` from an admin shell (`mpegg-adm`). Set the variables
first, then run top to bottom. This is the sequence recovered from
`~/.bash_history` (lines ~14820–14908) and re-verified against the live state.

```bash
# --- set these once ---------------------------------------------------------
SVC=xx                       # jah | tt | aa | <new>
USER=xx-deploy               # jah-deploy | tt-deploy | aa-deploy | <new>
REPO=RepoName                # JustAnotherHuman | TermiteTowers | AnalAcres
OWNER=mpegg007
XPRD=xx-prd                  # runner label used in runs-on
TARBALL=/srv/prd/actions-runner-linux-x64-2.337.0.tar.gz
```

```bash
# 1. Create the deploy user (skip if it already exists).
#    Observed uids: 2005 / 2006 / 2007 -> next free is 2008. Any normal uid works.
sudo adduser --disabled-password --gecos "" "$USER"

# 2. Create the prod dir and the runner dir, owned by the deploy user.
sudo mkdir -p /srv/prd/"$SVC"
sudo mkdir -p /srv/prd/"$SVC"-actions-runner
sudo chown "$USER":"$USER" /srv/prd/"$SVC" /srv/prd/"$SVC"-actions-runner

# 3. Unpack the shared runner tarball into the runner dir (as the deploy user).
cd /srv/prd/"$SVC"-actions-runner
sudo -u "$USER" tar xzf "$TARBALL"

# 4. Register the runner. See §4 for minting <TOKEN>.
#    Non-interactive (label supplied on the command line - JAH/AA style):
sudo -u "$USER" ./config.sh --url "https://github.com/$OWNER/$REPO" \
    --token "$TOKEN" --unattended --labels "$XPRD"
#    Interactive (TT style) - just omit --labels and answer the prompts.
#    *** The custom label goes at the "additional labels" prompt, NOT the
#        "runner group" prompt. Getting this wrong errors confusingly - §8.1. ***
# sudo -u "$USER" ./config.sh --url "https://github.com/$OWNER/$REPO" --token "$TOKEN"

# 5. Install + start the systemd service. run-as user is an argument to install.
sudo ./svc.sh install "$USER"          # writes the unit, enables it, makes runsvc.sh
sudo ./svc.sh start
sudo ./svc.sh status                   # must show active (running)

# 6. Create the prod virtualenv ONCE. The workflow reuses it; it is NOT created
#    by the deploy. rsync --exclude=.venv protects it on every future deploy.
sudo -u "$USER" /usr/bin/python3 -m venv /srv/prd/"$SVC"/.venv
```

Notes verified on the live host:

- Python is `3.12.11` (`/usr/bin/python3`); the prod venv symlinks to it.
- `JAVA_HOME=/usr/lib/jvm/java-21-openjdk-amd64/` — the runner's own `.env`
  file sets this (the runner is a Node host process and does not need Java for
  shell-only workflows, but the value is present and harmless).
- `svc.sh install` derives the unit from `RUNNER_ROOT=$(pwd)`, so **cd into the
  runner dir first**; the path is baked in at that moment.
- If a plain `sudo -u` prompts for a password in a non-TTY context, the history
  shows `sudo -A -u` (askpass) used as a fallback. See §8.6.

## 4. GitHub side

1. **Branch** — the trigger branch must exist on the repo. Workflows that run
   `on: push: branches: [prd]` are read **from the pushed ref**, so
   `.github/workflows/deploy-prd.yml` must be committed on `prd` too:

   ```bash
   git checkout -b prd            # or reuse an existing prd
   git push -u origin prd
   ```

2. **Mint a runner registration token** (needs repo admin):
   `https://github.com/<owner>/<REPO>/settings/actions/runners/new`
   Copy the `--token ...` value. It is **single-use and expires in ~1 hour**.
   Never commit it or paste it into this memory-bank.

3. **Repository host-level runners vs. group** — leave the *runner group* as
   `Default`. `<X>-prd` is a **label**, not a group (§8.1).

4. **(Optional) `workflow_dispatch`** — all three workflows include it so a
   deploy can be triggered by hand from the Actions tab without a push.

## 5. Deployment workflow template

`.github/workflows/deploy-prd.yml` on the `<br>` branch. This is the shape all
three repos share today (TT/AA are exactly this; JAH adds a `test` job + a sudo
step). Fill the placeholders and commit it **on `prd`**.

```yaml
name: Deploy Production

on:
  push:
    branches: [prd]
  workflow_dispatch:

permissions:
  contents: read

concurrency:
  group: <svc>-prd-deploy        # NOT jah-prd-deploy - see §8.9
  cancel-in-progress: false

jobs:
  deploy:
    runs-on:
      - self-hosted
      - linux
      - <X>-prd                  # must match the runner's additional label
    steps:
      - uses: actions/checkout@v4

      - name: Synchronize approved revision
        run: >-
          rsync -a --delete --exclude=.env --exclude=.venv --exclude=.git
          "$GITHUB_WORKSPACE/" /srv/prd/<svc>/

      - name: Install production dependencies
        run: /srv/prd/<svc>/.venv/bin/python -m pip install -e /srv/prd/<svc>
```

**That last step is a trap.** `pip install -e <dir>` requires packaging metadata
(`pyproject.toml` / `setup.py` / `setup.cfg`) *at that directory*. If the repo's
packaging lives in a subdirectory, point pip at the subdirectory — and if it has
no installable package at all, replace the step with a `requirements.txt`
install or drop it. See §8.8 for the live example.

If the service needs a systemd unit or `sudo` at deploy time, add a step and a
matching sudoers grant (§6). JAH's is the worked example:

```yaml
      - name: Install, reload, and restart collector
        run: |
          sudo /usr/bin/ln -sfn /srv/prd/jah/systemd/jah-librelink.service \
              /etc/systemd/system/jah-librelink.service
          sudo /usr/bin/systemctl daemon-reload
          sudo /usr/bin/systemctl enable jah-librelink.service
          sudo /usr/bin/systemctl restart jah-librelink.service
          sudo /usr/bin/systemctl is-active --quiet jah-librelink.service
```

## 6. sudoers grant — only if the workflow calls `sudo`

**TT and AA need no sudoers file** — their workflows never call `sudo`.
Only JAH has one: `/etc/sudoers.d/jah-deploy`.

Rules that bite (all verified against the live `/etc/sudoers.d/`):

- **Filename must have no dot.** sudo silently ignores any file in
  `/etc/sudoers.d/` whose name contains a `.`. Use `/etc/sudoers.d/<USER>`
  (e.g. `jah-deploy`), **not** `jah-deploy.conf`.
- **Mode `0440`, owner `root:root`** — same as the existing entries
  (`-r--r----- root root`).
- **The rule must match the exact argv**, including flags. Too narrow and the
  runner gets `sudo: a password is required` in a context with no TTY (which
  reads like a broken password, not a missing grant).
- Validate before you trust it: `sudo visudo -c -f /etc/sudoers.d/<USER>`.

Shape of a grant covering the JAH step above (one line per allowed binary; the
argument list must include every flag the workflow passes — note `--quiet`):

```
<USER> ALL=(root) NOPASSWD: /usr/bin/ln
<USER> ALL=(root) NOPASSWD: /usr/bin/systemctl daemon-reload
<USER> ALL=(root) NOPASSWD: /usr/bin/systemctl enable *
<USER> ALL=(root) NOPASSWD: /usr/bin/systemctl restart *
<USER> ALL=(root) NOPASSWD: /usr/bin/systemctl is-active --quiet *
```

> **Known latent mismatch:** JAH's installed `/etc/sudoers.d/jah-deploy` is not
> readable without an interactive password (that is the point of sudoers), so it
> could not be diffed non-interactively for this doc — **check it by hand** with
> `sudo cat /etc/sudoers.d/jah-deploy`. The workflow passes `is-active --quiet`;
> if the installed rule omits `--quiet`, the grant does not cover that call.
> Whenever the workflow's `sudo` lines change, re-audit the rule to match.

## 7. Verification

Run this after bootstrap, and again any time a deploy "doesn't run".

```bash
SVC=xx; USER=xx-deploy; REPO=RepoName; OWNER=mpegg007

# Service is up and enabled
systemctl status "actions.runner.$OWNER-$REPO.monolith.service" --no-pager | head -12
systemctl is-enabled "actions.runner.$OWNER-$REPO.monolith.service"

# Unit points where you think it does (path + user)
systemctl cat "actions.runner.$OWNER-$REPO.monolith.service"

# Runner registered to the right repo
cat /srv/prd/"$SVC"-actions-runner/.runner    # expect gitHubUrl = your repo

# Prod dir owned by the deploy user; .env/.venv survive a deploy
ls -la /srv/prd/"$SVC"/ | head

# Runner is actually listening (and shows the label it announced)
tail -n 20 /srv/prd/"$SVC"-actions-runner/_diag/Runner_*.log
```

Then, on GitHub: **Settings → Actions → Runners** should list `monolith` as
`Idle` with labels `self-hosted`, `Linux`, `X64`, `<X>-prd`.

End-to-end smoke test: push a no-op commit to `<br>` (or use
`workflow_dispatch`), then confirm the run was picked up by *your* runner:

```bash
ls -t /srv/prd/"$SVC"-actions-runner/_diag/Worker_*.log | head -1   # newest job log
grep -aE 'Job result|Step result: Failed' /srv/prd/"$SVC"-actions-runner/_diag/Worker_*.log | tail
```

A job that never appears in `_diag/Worker_*.log` was never routed to this
runner — that is a **label** problem (§8.1), not a deploy-script problem.

## 8. Pitfalls (read this before debugging anything)

### 8.1 `config.sh`'s first prompt is the runner *group*, not a label

The interactive `config.sh` prompts in this order, verified from the runner's
own diag log (`Runner_20261004-004855-utc.log` line 134):

1. `Enter the name of the runner group to add this runner to:` — a **group**.
   Answering with the label here fails with:

   ```
   TaskAgentPoolNotFoundException: Could not find any self-hosted runner group named "tt-prd".
   ```

2. `Enter the name of runner:` — blank accepts the hostname (`monolith`).
3. `This runner will have the following labels: 'self-hosted', 'Linux', 'X64'`
   → `Enter any additional labels (ex. label-1,label-2):` — **this** is where
   `<X>-prd` goes. (`Runner_20261004-005041-utc.log` lines 133–138.)
4. `Enter name of work folder:` — blank accepts `_work`.

Non-interactive alternative: `config.sh ... --unattended --labels <X>-prd`.

### 8.2 Don't hand-add the built-in labels

The runner advertises `self-hosted`, `Linux`, `X64` automatically. Workflows say
`linux` (lowercase); GitHub matches those case-insensitively — so **do not** add
`Linux` yourself and do not "fix" the workflow to `Linux`.

### 8.3 Runner directory naming drift

JAH → `/srv/prd/actions-runner`; TT → `/srv/prd/tt-actions-runner`;
AA → `/srv/prd/aa-actions-runner`. The unit's `ExecStart`/`WorkingDirectory`
hardcode whichever path `svc.sh install` saw. New runners: use
`/srv/prd/<svc>-actions-runner`.

### 8.4 sudoers filename with a dot is silently ignored

`/etc/sudoers.d/<USER>.conf` is **not loaded**. Use a dot-free name. Confirm with
`sudo visudo -c` (it lists what it parsed).

### 8.5 The sudoers rule must match the exact argv

`systemctl is-active --quiet <x>` and `systemctl is-active <x>` are different
commands to sudo. A rule missing `--quiet` does not cover the workflow's call.
Symptom in the runner log: `sudo: a password is required`.

### 8.6 `sudo -u` vs `sudo -A -u` (no TTY)

`~/.bash_history` shows `sudo -A -u <USER> ...` used whenever plain `sudo -u`
prompted. `-A` routes the password through an askpass helper; the host installs
`/etc/sudoers.d/90-askpass-every-time` for exactly this. If a bootstrap command
hangs on a password prompt, retry with `-A` (or set a valid askpass).

### 8.7 The prod `.venv` is hand-made and the workflow *reuses* it

Nothing creates `/srv/prd/<svc>/.venv` in CI. It is made once (§3 step 6) and
protected from rsync by `--exclude=.venv`. Delete it and the
`Install production dependencies` step fails with "no such file or directory"
for `.venv/bin/python`.

### 8.8 `pip install -e <dir>` needs packaging *at that dir* — the live TT breakage

TT's deploy runs `pip install -e /srv/prd/tt`, but TT has **no** root-level
`pyproject.toml` / `setup.py` / `setup.cfg` / `requirements.txt`; its packaging
is at `/srv/prd/tt/water-meter/pyproject.toml`. So the step fails. Fix is one
line — point pip at the sub-package (or add root packaging):

```yaml
- name: Install production dependencies
  run: /srv/prd/tt/.venv/bin/python -m pip install -e /srv/prd/tt/water-meter
```

### 8.9 `concurrency.group` is copy-pasted from JAH

TT's and AA's deploy workflows both still say `group: jah-prd-deploy`. Concurrency
groups are repository-scoped, so there is no cross-repo collision today — it is
cosmetic, but tidy it up (`<svc>-prd-deploy`) so logs read honestly.

### 8.10 rsync `--exclude=.env` means prod `.env` is never managed by CI

Prod secrets are placed by hand and persist. On the current TT host
`/srv/prd/tt/.env` is `0` bytes and owned by `mpegg-adm`, **not** `tt-deploy` —
so the deploy user cannot write it. If a service needs to write its own `.env`,
fix the ownership; don't un-exclude it in rsync.

## 9. Current state on `monolith` (snapshot 2026-10-04)

| Service | Repo (owner `mpegg007`) | Runner dir | User (uid) | Unit | Status |
| ------- | ----------------------- | ---------- | ---------- | ---- | ------ |
| `jah` | `JustAnotherHuman` | `/srv/prd/actions-runner` | `jah-deploy` (2005) | `actions.runner.mpegg007-JustAnotherHuman.monolith.service` | active |
| `tt`  | `TermiteTowers`    | `/srv/prd/tt-actions-runner` | `tt-deploy` (2006) | `actions.runner.mpegg007-TermiteTowers.monolith.service` | active |
| `aa`  | `AnalAcres`        | `/srv/prd/aa-actions-runner` | `aa-deploy` (2007) | `actions.runner.mpegg007-AnalAcres.monolith.service` | active |

Host: `monolith`, Ubuntu 24.04.5 LTS (kernel 7.0.0-34-generic), Python 3.12.11,
runner tarball `actions-runner-linux-x64-2.337.0.tar.gz` in `/srv/prd/`.
Runner labels: `jah-prd`, `tt-prd`, `aa-prd` (each + the built-in three).
`/etc/sudoers.d/` contains only `jah-deploy`, `90-askpass-every-time`, `README`,
`zfs` — no sudoers entry for `tt` or `aa`, and neither needs one (§6).

### TT deploy is currently RED — one cause

- `origin/prd` exists; `/srv/prd/tt` is populated (the rsync step succeeds).
- The **only** failing step is `Install production dependencies`, which runs
  `pip install -e /srv/prd/tt` against a repo with no root packaging (§8.8).
- Last run `2026-10-04T16:18:47Z` →
  `Job result after all job steps finish: Failed`
  (`/srv/prd/tt-actions-runner/_diag/Worker_20261004-161845-utc.log`, line 2711
  `Step result: Failed` for the third step).
- Commit `40282aa` ("deploy-prd fix") did **not** touch the pip line — it only
  **removed the `test` job** from the workflow. The pip line is unchanged on both
  `dev1` and `origin/prd`.
- Fix: repoint pip at `/srv/prd/tt/water-meter` (§8.8).

## 10. Re-verify this snapshot

These commands regenerate every fact above. Run them before trusting this doc
after any host change.

```bash
# Users + uids
getent passwd | grep -i deploy

# Runner dirs, prod dirs, tarball
ls -la /srv/prd/

# All runner units: path, user, status
for f in /etc/systemd/system/actions.runner.*.service; do
  echo "== $f"; sed -n '1,10p' "$f"; done
systemctl list-units --type=service --all --no-pager | grep actions.runner

# Labels each runner announced (grep the diag logs)
grep -rao 'jah-prd\|tt-prd\|aa-prd' /srv/prd/*-actions-runner/_diag/Runner_*.log /srv/prd/actions-runner/_diag/Runner_*.log

# Runner -> repo binding
for d in /srv/prd/actions-runner /srv/prd/tt-actions-runner /srv/prd/aa-actions-runner; do
  echo "== $d"; grep -a gitHubUrl "$d/.runner"; done

# Python + Java + sudoers inventory
python3 --version; ls /usr/lib/jvm/; ls -la /etc/sudoers.d/

# TT prod packaging reality (the live blocker)
ls -la /srv/prd/tt/pyproject.toml /srv/prd/tt/water-meter/pyproject.toml 2>&1

# Latest TT job outcome
tail -n 5 "$(ls -t /srv/prd/tt-actions-runner/_diag/Worker_*.log | head -1)"
```

