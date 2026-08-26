# Phase 5: CI/CD, Documentation & Legal Compliance - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-26
**Phase:** 05-ci-cd-documentation-legal-compliance-github-actions-ci-tests
**Areas discussed:** Repository visibility, Deploy gating, License, VPS IP/hostname exposure, Code quality/coverage enforcement

---

## Repository visibility

| Option | Description | Selected |
|--------|-------------|----------|
| Privé | Code, deploy secrets, and install details stay invisible; GitHub Actions free tier still applies at typical solo usage | |
| Public | Visible to everyone — relevant if the user wants to show/share the project someday; raises the stakes on secrets hygiene and license choice | ✓ |

**User's choice:** Public.
**Notes:** No further rationale given — the repo has never been pushed anywhere yet, so this is a from-scratch decision.

---

## Deploy gating

| Option | Description | Selected |
|--------|-------------|----------|
| Auto on merge to main (tests required first) | Simple, fast iteration; risk: a bug that passes tests could still break the real physical display in production automatically | |
| Merge + manual GitHub approval | Tests run automatically on every push; deploy to the VPS requires a manual click (GitHub Environments required-reviewers) before it runs | ✓ |

**User's choice:** Merge + manual approval.
**Notes:** This VPS serves a real physical device on the wall — a human checkpoint before every prod push was preferred over full automation.

---

## License

| Option | Description | Selected |
|--------|-------------|----------|
| MIT | Permissive, standard for hobby/personal projects, compatible with the already-vendored SIL OFL font licenses | ✓ |
| All rights reserved | No reuse permitted without permission; more restrictive | |

**User's choice:** MIT.
**Notes:** None given beyond selecting the recommended option.

---

## VPS IP/hostname exposure (raised proactively, not a pre-planned gray area)

While confirming the public-repo decision, a live check found the real VPS IP (`<vps-ip>`) and hostname (`<public-host>`) already committed across 4 planning docs and `deploy/README.md` — and no `.gitignore` exists anywhere in the repo. No actual secrets were found committed (verified via `git log --all -p` on `deploy/inkframe.env` and `firmware/main/secrets.h` — both clean).

| Option | Description | Selected |
|--------|-------------|----------|
| Keep as-is | The IP/hostname are already technically discoverable (public DNS, OVH IP-range scanning) — redacting them in docs doesn't add real security, just friction | |
| Redact/genericize | Replace the real IP/hostname with placeholders in historical docs before the first public push — reduces direct reconnaissance surface even if not a true secret | ✓ (via free-text) |

**User's choice (free text):** "J'aimerais que ces informations sensibles ne soient pas visibles si possible" (I'd like this sensitive info to not be visible if possible).
**Notes:** Since the repo has no remote and no collaborators yet, a full history rewrite (not just a HEAD-only edit) is feasible before the first push — captured as D-05 in CONTEXT.md, exact mechanism (filter-repo vs. squash) left to planner/research.

---

## Code quality / coverage enforcement

| Option | Description | Selected |
|--------|-------------|----------|
| Reported only (recommended) | Lint + coverage shown in every CI run and a README badge, but nothing blocks the merge — lower friction for a solo project | |
| Blocking | Lint must pass and coverage must not regress below a set threshold, or CI fails and blocks the merge | ✓ |

**User's choice:** Blocking.
**Notes:** Chosen despite this being a solo project — explicitly overrode the "reported only" recommendation.

---

## Claude's Discretion

- Exact lint tool (Ruff recommended, not discussed live)
- Exact coverage tool (coverage.py/pytest-cov's engine, usable without pytest as the runner)
- Whether firmware (ESP-IDF) CI build is in scope for this phase, given the official `espressif/esp-idf-ci-action` exists (D-10)
- Exact coverage threshold percentage — planner should derive a realistic baseline from the current suite's actual measured coverage
- Git-history-scrub mechanism (filter-repo vs. fresh squashed history)

## Deferred Ideas

None — discussion stayed within phase scope.
