<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_start:  % -->
<!-- %ccm_git_repo: TermiteTowers % -->
<!-- %ccm_git_branch: dev1 % -->
<!-- %ccm_git_path: wiki/service-taxonomy.md % -->
<!-- %ccm_git_object_id: wiki/service-taxonomy.md@200 % -->
<!-- %ccm_git_commit_date: 2026-11-09 10:16:57 -0500 % -->
<!-- %ccm_git_commit_author: mpegg % -->
<!-- %ccm_git_commit_message: zoo.261109 % -->
<!-- TermiteTowers Continuous Code Management Header TEMPLATE --- %ccm_git_header_end:  % -->
# Service taxonomy — platform, tools and data

How to decide whether something is a TermiteTowers service, where its hostname
belongs, and what belongs in `/srv`. Written after the Nextcloud rebuild, when
the question "is Postgres a TT service?" turned out to be the root of several
naming and layout arguments.

---

## 1. What a "service" is

A thing earns the word only if it holds **all four**:

1. a **tenant or audience** — someone it exists for
2. a **public identity** — a URL someone types, or a stated operational contract
3. **owned data** — bytes whose loss matters, or an explicit "none"
4. an **independent lifecycle** — you can deploy, back up and restore *it* alone

Apply it and the ambiguities resolve:

| Thing | Tenant | Public identity | Owned data | Own lifecycle | Verdict |
| --- | --- | --- | --- | --- | --- |
| Nextcloud | yes | `filebank.analacres.ca` | yes (user files) | yes | **service** |
| Immich | yes | `memorylab.analacres.ca` | yes (19 G originals) | yes | **service** |
| Uptime Kuma | yes | `kuma.termitetowers.ca` | config only | yes | **service** |
| PostgreSQL | no | none | no — it holds *other* things' data | no: estate-wide, upgrades hit every tenant | **platform** |
| Kea DHCP | indirect | none | no — leases are regenerable | partly | **platform service** |
| PowerDNS | indirect | none | zones (shared) | partly | **platform service** |
| Docker networks | no | none | no | no | **platform** |
| nginx | no | none | no | no | **platform** |

The distinction that matters: **you do not use Postgres, you use a database.**
You restore a database, not "Postgres". An upgrade is not scoped to one tenant.

## 2. Three layers, and the confusion between them

| Layer | What it names | Example | Changes when |
| --- | --- | --- | --- |
| **Software** | the thing you upgrade and debug | `nextcloud`, container, ZFS dataset, DB, env file | you change software |
| **Identity** | who the URL is for and what it holds | `filebank.analacres.ca` | your intent changes |
| **Platform** | shared substrate | `ttdb_dev1`, `kea`, `powerdns` | rarely |

`filebank` is not an abstraction over Nextcloud — it is a **decision**. Nextcloud
could be replaced and `filebank` would still be the right name. That is why the
public name should never contain the product name.

**Consequence:** the internal identity keeps the software name. Container
`nextcloud-dev1`, dataset `gallery/nextcloud`, database `nextcloud`,
`nextcloud.env`. Only the URL is `filebank`.

## 3. The domain rule

> **termutetowers.ca = tools I operate. analacres.ca = data I own.
> justanotherhuman.ca = what other people see.**

Pick by the **audience of the URL**, not by where the bytes are stored. Storage
moves; audiences do not. "It is on the gallery array so it belongs on
analacres" is data gravity, and data gravity changes the day a dataset moves.

| Hostname | Family | Why |
| --- | --- | --- |
| `memorylab`, `wordbank`, `soundbank`, `filebank` | aa | a bank or lab of things I own |
| `auth.analacres.ca` | aa | gates the aa data |
| `wiki`, `docs`, `kuma`, `dozzle`, `prometheus`, `lobe`, `webai`, `mealie`, `asset` | tt | tools I operate |
| `pics.justanotherhuman.ca` | jah | public face |
| `ttdb_dev1`, `kea`, `powerdns`, `redis` | none | platform, no public hostname |

Every existing hostname lands in the right column with no exceptions, which is
why this is worth writing down: the grammar was already in use. `-bank` and
`-lab` are data words, so a hostname that wants one is almost certainly aa.

A service can legitimately appear in two families — Immich's admin UI is a tool
while its library is data. The current practice (one hostname, in the family of
its dominant audience) is the right resolution.

## 4. `/srv` layout

| Path | Holds | Ownership |
| --- | --- | --- |
| `/srv/dev1/<svc>/` | `docker/` subdir of compose and env **symlinks**; optional `scripts` symlink into the repo; runtime data | `mpegg-adm:tt-docker` |
| `/srv/dev1/tt`, `/aa`, `/jah` | **do not exist yet** — intended git-deployed dev trees | — |
| `/srv/prd/tt`, `/aa`, `/jah` | deployed trees, **rsync targets, not clones** | `tt-deploy`, `aa-deploy`, `jah-deploy` |
| `/srv/prd/*-actions-runner`, `/srv/prd/actions-runner` | self-hosted GitHub runners, one per repo | matching deploy user |
| `/srv/dev2`, `/srv/shared`, `/srv/tt.omp` | separate concerns | root |

Measured 2026-11-09: `/srv/dev1` holds 32 directories and 2 symlinks. The shape
is already "symlinks into the repo, runtime data alongside":

```
/srv/dev1/kea/scripts -> /home/mpegg-adm/source/TermiteTowers/infra/dhcp/scripts
```

That means `ExecStart=/srv/dev1/kea/scripts/monitoring/...` resolves to the repo
file. There is **no copy and no drift** — an earlier review claimed there was
and was wrong.

Known leftovers, deliberately not cleaned up yet:

- `/srv/dev1/docker`, `/srv/dev1/systemd`, `/srv/dev1/logrotate` — empty
- `/srv/dev1/kea.old.obsolete` — self-labelled obsolete
- `/srv/prd/docker`, `ollama`, `piper`, `tortoise`, `whisper` — older layout

## 5. The agreement (applies when touching something, not as a sweep)

1. **Code lives in the repo. Never copy it into `/srv`.** Symlinks are fine;
   copies are not.
2. **`/srv/dev1/<svc>/` may hold** a `docker/` subdir of compose and env
   symlinks, an optional `scripts` symlink, and runtime data. Nothing else.
3. **Units may reference the working copy or the `/srv` symlink today.** When
   `/srv/dev1/tt` exists, repoint to it. Do not introduce a third form, and do
   not create new `/srv/dev1/<svc>` trees for new services.

## 6. Open questions

- **DHCP serves `192.168.1.0/24`, while the estate is `192.168.4.0/24`.** That is
  platform for a *different network* — possibly another site or a VPN segment
  rather than another tenant. Worth naming explicitly before it is classified.
- Whether `prd` should keep `docker/`, `ollama/`, `piper/`, `tortoise/`,
  `whisper/` once `/srv/prd/<repo>` covers everything.
