# Phase 4: CI/CD, Documentation & Legal Compliance - Pattern Map

**Mapped:** 2026-08-26
**Files analyzed:** 10 (new files/dirs this phase creates or modifies)
**Analogs found:** 4 with genuine structural matches / 10; remainder are new-file-type cases with no close analog (documented plainly below, per phase brief)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|--------------------|------|-----------|-----------------|----------------|
| `.github/workflows/ci.yml` | config (CI pipeline) | batch (sequential script invocation) | `deploy/deploy.sh` (only existing "orchestrates multiple ordered shell steps against this project's own scripts" file) | weak / no true analog — different execution engine (GitHub Actions YAML vs bash), but same *sequencing convention* (fail-fast, ordered steps, working-directory-from-repo-root) |
| `.github/workflows/deploy.yml` | config (CD pipeline, gated) | request-response (triggered by merge event) → batch | `deploy/deploy.sh` + `deploy/provision.sh` (the exact script this workflow wraps, per D-12) | role-match — deploy.yml is a thin orchestration wrapper; deploy.sh is the thing being wrapped, so its argument/flow conventions dictate the workflow's `run:` step |
| `scripts/run-all-tests.sh` (new aggregate local+CI test runner) | utility (test runner) | batch | `deploy/deploy.sh` (closest existing "ordered shell script with `set -euo pipefail`, one echo per stage, operates from repo root" convention) | role-match |
| `.gitignore` (repo root) | config | — | `server/.gitignore`, `deploy/.gitignore`, `firmware/.gitignore`, `stub-server/.gitignore`, `adsb-test/.gitignore` (5 existing per-subdir gitignores) | exact — same project already has 5 working `.gitignore` files with an established comment style; root one is the same pattern scoped wider |
| `LICENSE` | config (legal) | — | none | no analog — first license file in repo |
| `README.md` (repo root) | component (documentation) | — | `deploy/README.md`, `server/README.md` (closest "operational/setup documentation for a newcomer" analogs) | role-match — same doc structure conventions (numbered setup steps, fenced bash blocks, "what each file does" tables), different scope (repo-wide vs subdir-scoped) |
| `COMPLIANCE.md` (or README section, D-14) | component (documentation, legal) | — | `server/assets/fonts/VENDOR.md`, `server/assets/icons/VENDOR.md` (closest "verify/document third-party provenance and license terms" analogs) | role-match — same "source, terms, verification date, verdict" documentation shape |
| `server/assets/icons/illustrations/VENDOR.md` (flagged gap, D-14 scope item 3) | component (documentation, legal) | — | `server/assets/icons/VENDOR.md` (sibling file, same directory tree, same subject matter) | exact — this is filling a gap in an existing, already-patterned file family |
| `server/requirements-dev.txt` (new, optional per RESEARCH.md structure) | config | — | `server/requirements.txt` | exact — same pinned-version, flat-list format, just a second file for CI-only tooling |
| Git history scrub (one-time operation, not a tracked file) | utility (data migration / history rewrite) | batch | none | no analog — first history-rewrite operation in this repo; RESEARCH.md's Pattern 3 (`git filter-repo --replace-text`) is the authoritative source, not a codebase file |

## Pattern Assignments

### `.github/workflows/ci.yml` (config, batch)

**Analog:** `deploy/deploy.sh` (weak match — borrow the *sequencing discipline*, not literal syntax)

**Ordered-steps-with-fail-fast pattern** (`deploy/deploy.sh` lines 28, 35, 57-60):
```bash
set -euo pipefail
...
echo "==> Syncing server/ to ${SSH_TARGET}:${APP_ROOT}/server/"
rsync -az --delete ...
...
echo "==> Checking whether requirements.txt changed"
LOCAL_HASH="$(sha256sum "${REPO_ROOT}/server/requirements.txt" | awk '{print $1}')"
```
Translate this into CI as: every `run:` block starts with `set -e` (or relies on Actions' default fail-fast per-step behavior), each logical stage gets its own labeled step (mirroring the `echo "==> ..."` stage markers), and paths are always resolved from repo root — matching this project's existing "run from the repository root" convention stated verbatim in `server/README.md` line 31 ("Run each from the repository root so relative fixture/geofence paths resolve").

**Test invocation convention to preserve** (`server/README.md` lines 27-40, `server/test_render.py` lines 1-26 docstring):
```
Every server/test_*.py is a stdlib-only, directly-executable harness (no
pytest ...). Run each from the repository root ...
server/.venv/bin/python3 server/test_plane_detection.py
```
Each `check()`/`EXPECTED_CHECK_COUNT` harness exits 0/1 on its own (`server/test_render.py` closing lines):
```python
total = len(results)
passed = sum(1 for _, ok in results if ok)
print("render: %d/%d checks pass" % (passed, total))
return 0 if (passed == total and total == EXPECTED_CHECK_COUNT) else 1

if __name__ == "__main__":
    sys.exit(main())
```
CI's test step(s) must treat each file's own process exit code as the pass/fail signal — one `run:` step per file, or a `set -e` loop over all 9 files (8 under `server/`, 1 under `stub-server/`), exactly as RESEARCH.md's Pattern 1 shows. Do not attempt to collect these via pytest.

**Dependency install pattern** (`server/README.md` lines 13-18):
```bash
python3 -m venv server/.venv
server/.venv/bin/pip install -r server/requirements.txt
```
CI's setup step should mirror this exactly (create venv, install from `server/requirements.txt`, then separately install `coverage`/`ruff` — keep those out of the production `requirements.txt` per RESEARCH.md's `requirements-dev.txt` recommendation).

---

### `.github/workflows/deploy.yml` (config, gated CD)

**Analog:** `deploy/deploy.sh` (the file being wrapped — D-12 requires this workflow never reimplement its logic)

**Invocation contract to preserve** (`deploy/deploy.sh` lines 6-9, 31):
```bash
# Usage:
#   deploy/deploy.sh <ssh-target>
#   deploy/deploy.sh root@203.0.113.10
#   deploy/deploy.sh ubuntu@203.0.113.10
SSH_TARGET="${1:?usage: deploy/deploy.sh <ssh-target>, e.g. deploy/deploy.sh root@203.0.113.10}"
```
The deploy job's only script-invoking line should be `deploy/deploy.sh "${{ secrets.VPS_SSH_TARGET }}"` — a single positional argument, nothing more. Do not pass extra flags or duplicate the rsync/systemctl steps that already live inside deploy.sh (lines 41-49 rsync `server/` and `stub-server/`; further down it restarts `inkframe-byos.service` and the poll timer — none of this belongs in workflow YAML).

**Secrets-never-committed convention to extend to CI** (`deploy/README.md` lines 18-22, `deploy/.gitignore`):
```
inkframe.env
```
with the comment:
```
# The real production env file - contains INK_BYOS_SECRET. Created by hand
# on the VPS only (deploy/README.md), never on a laptop, never committed.
```
Apply the same "external, never-in-git" pattern to the VPS SSH key: it lives only as `secrets.VPS_SSH_KEY` in GitHub, loaded via `webfactory/ssh-agent`, never written to a workspace file or echoed — same spirit as `deploy/inkframe.env` being hand-created only on the VPS itself.

---

### `.gitignore` (repo root)

**Analog:** `server/.gitignore`, `deploy/.gitignore` (exact structural match, 5 existing sibling files)

**Comment + entry style** (`server/.gitignore`, full file):
```
# Local virtualenv - recreate from requirements.txt.
.venv/

# Generated/runtime panel + poll state - never enter git.
state/panel.bin
state/panel.bin.tmp
state/poll_state.json
state/poll_state.json.tmp

# Python bytecode caches.
__pycache__/
*.pyc

# Optional developer preview PNGs (render.py --preview).
*.preview.png
```

**Secrets-focused entry style** (`deploy/.gitignore`, full file):
```
# The real production env file - contains INK_BYOS_SECRET. Created by hand
# on the VPS only (deploy/README.md), never on a laptop, never committed.
# Mirrors firmware/.gitignore's `main/secrets.h` rule - the ignore entry
# exists before the file ever does, so there is no window in which a
# credential could land in git history.
inkframe.env
```

The new root `.gitignore` should follow this exact convention: grouped entries under short `#`-comment headers explaining *why*, not just *what* — e.g. a "Belt-and-suspenders — subdir .gitignore files already cover these, but the repo root's own untracked files need this too" comment above `.DS_Store`, `**/__pycache__/`, `firmware/build*/`, `deploy/inkframe.env`, `firmware/main/secrets.h`, per D-06/Pitfall 5. Note the existing per-subdir files (`server/.gitignore`, `deploy/.gitignore`, `firmware/.gitignore`, `stub-server/.gitignore`, `adsb-test/.gitignore`, `server/state/.gitignore`) remain in place and are NOT superseded — the root file is additive, catching untracked files at repo-root scope (`.DS_Store`, `.planning/research/.cache/`) that no subdir file covers.

---

### `README.md` (repo root, new)

**Analog:** `deploy/README.md`, `server/README.md`

**Section-header + "what each file does" table pattern** (`deploy/README.md` lines 1-33):
```markdown
# deploy — Ink Frame Phase 2 VPS deployment

Turns the render pipeline built in 02-01 through 02-04 into an always-on,
internet-reachable server: ...

**Provider note:** ...
**SSH login note:** ...

## What each file does

| File | Purpose |
|------|---------|
| `inkframe.env.example` | Template for the real, gitignored `inkframe.env` ... |
| `inkframe-byos.service` | Runs `stub-server/byos_server.py` as the `inkframe` user ... |
```

**Setup-steps-with-fenced-bash pattern** (`server/README.md` lines 11-18):
```markdown
## Setup

Create the virtualenv and install the two pinned dependencies:

\`\`\`bash
python3 -m venv server/.venv
server/.venv/bin/pip install -r server/requirements.txt
\`\`\`
```

The repo-root README should follow this exact voice/structure — numbered or clearly-labeled sections (hardware BOM, firmware flash, server setup, pointer to `deploy/README.md`), fenced bash blocks for every command a newcomer runs, and a "what each top-level directory contains" table analogous to `deploy/README.md`'s "what each file does" table. Per D-15, this file should point to `deploy/README.md` for VPS provisioning rather than duplicating it — same non-duplication discipline `server/README.md` line 60 ("This directory ... runs on a real always-on OVH VPS-1 in production ...") already uses when referencing deploy/ instead of re-explaining it.

**Placeholder-not-literal convention (ties to D-05):** Any VPS reference in the new README must use a placeholder (e.g. `<vps-host>`) exactly as `deploy/deploy.sh`'s own usage comment already does — line 8: `deploy/deploy.sh root@203.0.113.10` uses an RFC 5737 example IP, never a real one. Follow that existing convention rather than inventing a new placeholder style.

---

### `COMPLIANCE.md` (new, D-14)

**Analog:** `server/assets/fonts/VENDOR.md`, `server/assets/icons/VENDOR.md`

**Provenance/terms-documentation pattern** (`server/assets/fonts/VENDOR.md` lines 1-17):
```markdown
# server/assets/fonts — Vendor Provenance

## `Inter-Regular.ttf` / `Inter-Bold.ttf`

- **Upstream repository/source:** https://github.com/rsms/inter
- **Pinned commit / retrieval date:** release tag `v4.1`, retrieved 2026-08-09 via ...
- **Upstream path:** ...
- **Licence:** SIL OFL 1.1 — Copyright (c) 2016 The Inter Project Authors ...
  The licence requires the copyright and licence notice to travel with the
  font files; the full OFL 1.1 text is vendored ...
```

**Verification-date + verdict pattern** (`server/assets/icons/VENDOR.md` lines 1-14, 30-40):
```markdown
## `illustrations/*.png`

- **Generation date:** 2026-08-26 (visual-style revision on the same date).
- **Tool:** OpenAI built-in image generation (`gpt-image`), generated as
  transparent PNG cutouts and visually inspected after generation.
...
## `plane-takeoff.svg` / ...
- **Upstream repository/source:** https://github.com/lucide-icons/lucide
- **Pinned release tag / retrieval date:** release tag `1.31.0`, retrieved
  2026-08-10 via ...
- **Licence:** ISC License — Copyright (c) 2026 Lucide Icons and Contributors ...
```

`COMPLIANCE.md` should use this exact per-source subsection shape (source name → upstream link → pinned retrieval date → license/terms text → verdict/action) for each of the three named APIs (AeroDataBox: unused, verify and state so; PRIM/IDFM: unused in shipped v1, verify and state so; adsb.fi + airplanes.live: used, document the attribution requirement RESEARCH.md's Pitfall 4 confirms is real and currently unmet — add the citation + link to README's "Data sources" section, mirroring how VENDOR.md's font/icon entries embed the required notice directly rather than just referencing it).

---

### `server/assets/icons/illustrations/VENDOR.md` (new, fills documented gap)

**Analog:** `server/assets/icons/VENDOR.md` (sibling in the same directory tree — literally the parent-level file whose `illustrations/*.png` section, lines 3-28, should be lifted/expanded into this new child file)

Use the exact same field set already established for the `illustrations/*.png` entry in the parent VENDOR.md (Generation date, Tool, Prompt recipe, Selected aircraft types, Local modifications/validation) — this is a split/promotion of existing content per `server/assets/icons/illustrations/HANDOFF.md`'s referenced gap, not a new documentation format.

---

### `server/requirements-dev.txt` (new)

**Analog:** `server/requirements.txt` (exact — same flat pinned-version list format)

Follow the same one-package-per-line, pinned-`==`-version style already used in `server/requirements.txt` (`Pillow==12.3.0`, `requests==2.34.2`), for `coverage==7.15.4` and `ruff==0.16.4` (versions verified live against PyPI per RESEARCH.md's Package Legitimacy Audit).

---

## Shared Patterns

### "Real secrets never in git" discipline (applies to `.gitignore`, `deploy.yml`, README)
**Source:** `deploy/.gitignore`, `firmware/.gitignore` (referenced), `deploy/README.md` lines 18-22
**Apply to:** `.gitignore` (repo root), `.github/workflows/deploy.yml`, `README.md`
The project already has a proven, working "credentials live outside git, referenced by placeholder/env-file/GitHub-secret" pattern (`deploy/inkframe.env` created by hand on the VPS, never committed; `firmware/main/secrets.h` same treatment). Phase 4's new files must extend this exact pattern to the VPS SSH key (GitHub Actions secret, never a file) and to the VPS IP/hostname (placeholder in all live docs, per D-05) — not invent a new convention.

### Documentation table + fenced-bash structure
**Source:** `deploy/README.md`, `server/README.md`
**Apply to:** `README.md` (repo root), `COMPLIANCE.md`
Both existing READMEs use the same shape: a short scope paragraph, a "what each file/directory does" markdown table, then numbered setup/operational sections with fenced ` ```bash ` command blocks. New docs this phase produces should match this voice rather than introducing a different documentation style.

### Ordered-shell-script-with-stage-echoes convention
**Source:** `deploy/deploy.sh`
**Apply to:** `.github/workflows/ci.yml`'s `run:` blocks, `scripts/run-all-tests.sh`
`set -euo pipefail` (or CI's per-step fail-fast default) plus one `echo "==> stage description"` per logical stage — this is the existing convention for any multi-step operational script in this repo and should carry into the new CI-invoked scripts for consistency and debuggability in Action logs.

## No Analog Found

Files with no close match in the codebase — planner should rely on RESEARCH.md's Code Examples / Patterns 1-3 instead:

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `.github/workflows/ci.yml` | config | batch | First GitHub Actions workflow in this repo — no prior CI existed. Use RESEARCH.md's "Full CI workflow skeleton" verbatim as the structural starting point, adapted with `deploy/deploy.sh`'s stage-echo/fail-fast conventions as noted above. |
| `.github/workflows/deploy.yml` | config | request-response/batch | Same — first gated-deploy workflow; RESEARCH.md's Pattern 2 (GitHub Environment manual-approval gate) is the authoritative source, since GitHub Environments have no in-repo precedent to mirror. |
| `LICENSE` | config | — | First license file in the repo. Use the MIT license's standard boilerplate text (per D-13) — no in-repo pattern applies to a legal boilerplate file. |
| Git history scrub operation | utility | batch | One-time, not a tracked source file — RESEARCH.md's Pattern 3 (`git filter-repo --replace-text`) and Pitfall 2 are the authoritative reference; there is no prior history-rewrite in this repo to pattern-match against. |

## Metadata

**Analog search scope:** repo root, `deploy/`, `server/` (incl. `server/assets/fonts/`, `server/assets/icons/`), `stub-server/`, `.planning/` (context/research only, not source)
**Files scanned:** `deploy/deploy.sh`, `deploy/README.md`, `deploy/.gitignore`, `server/.gitignore`, `server/README.md`, `server/requirements.txt`, `server/test_render.py`, `server/assets/fonts/VENDOR.md`, `server/assets/icons/VENDOR.md`, plus a directory listing across `firmware/`, `stub-server/`, `adsb-test/` for sibling `.gitignore` files
**Pattern extraction date:** 2026-08-26
