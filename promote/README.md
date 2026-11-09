# promote/

The promotion artifacts for this repository. The model is specified in
[`docs/design/promotion-model.md`](../docs/design/promotion-model.md); this file is the
operating instruction.

## Three artifacts, three jobs

| | authored by | may contain a ref? | changes |
|---|---|---|---|
| `inventory/` — what an app owns | generated | no | rarely |
| `packages/` — what you chose for one promotion | **you, by hand** | **yes** | every promotion |
| `records/` — what resolved | generated from a package | **never** | every promotion |

`latest` exists only in a package. `build` resolves it once, and the record carries the
commit. A record that resolved at apply time would make the dry run meaningless and
rollback impossible.

## Authoring a package

```
package:  2026-11-09-docs
app:      termitetowers-core
from:     dev1
to:       uat1
reason:   why this package exists, for whoever reads the record later

+ docs/design/promotion-model.md              # identity mapping
+ wiki/ports.md -> docs/ports.md              # remapped destination
+ infra/docker/x.yml@7c77ce9                  # pinned to its own commit
- memory-bank/host-deploy-runbook.md          # tombstone, file only
```

`from:` accepts a branch, a tag, a SHA, or `latest`. Deliberately absent: globs,
directories and exclude patterns — any of them makes the promoted set unbounded, which
destroys reproducibility and review.

## Building

```bash
python3 scripts/promote/tt-promote.py build \
  --repo-root . \
  --package promote/packages/2026-11-09-docs.pkg \
  --out promote/records/2026-11-09-docs.yaml
```

`--target-ref` overrides the package's `to:` — use it to rehearse against an existing
branch before the real one exists. `--require-change` makes an empty result an error
rather than a warning.

## What build refuses

All structural refusals are reported **together, before any ref is resolved**, so a bad
package is not unmasked one error at a time.

- a glob, a directory, an absolute path, or `..`
- two entries with the same destination
- a source absent at the pinned commit
- a symlink source
- a path on `policy/deny.txt`
- a privileged path without `!`, and `!` on a path that is not privileged

That last pair is bidirectional on purpose. The tool knows which prefixes are
privileged and the human must type `!`; a missing marker fails, and a stray marker also
fails. Typed approval cannot drift out of sync with the classification in either
direction, which a tool-computed flag cannot guarantee.

```
+ ! .github/workflows/deploy-uat1.yml
```

## policy/

| file | job |
|---|---|
| `privileged.txt` | prefixes whose **presence** is behaviour: workflows, units, vhosts, logrotate |
| `deny.txt` | paths a package may never name: env files, keys, encrypted material |
| `ignore.txt` | paths excluded from the residual report |

They are files rather than constants so that adding a forbidden path or a new privileged
class is a diff someone can review.

`deny.txt` stops a package from *naming* a secret. It does not stop a secret from
living inside a legitimately promoted file — that is the secret scanner's job, and the
reason `.gitignore` keeps `infra/docker/env/*.env` out of every checkout.

## Regenerating the inventory

```bash
python3 scripts/promote/tt-promote.py inventory \
  --repo-root . --ref dev1 --seed-ref origin/prd \
  --app termitetowers-core --out promote/inventory/termitetowers-core.txt
```

`--seed-ref` is not optional in practice. Ownership is a **persistent record**, not a
snapshot of one branch: a path that exists on `prd` but has been deleted from `dev1` is
still owned, and is exactly what becomes a `-` entry. Regenerating without the seed
silently drops ownership of every source-deleted path, and those files then stay on the
target forever.

The file carries `# tt-hooks.skip-post-commit` because a CCM header would rewrite
branch and blob fields on every commit, making a 516-line file look changed when nothing
of consequence changed.
