---
phase: 54
slug: auth0-sign-in-local-roles-and-default-deny-access
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-10-30
---

# Phase 54 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution. The requirement-to-test map lives in `54-RESEARCH.md` § Validation Architecture; the per-task map below is filled by the plans.

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9 + xdist + cov + pytest-socket (loopback only) + pytest-playwright |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `server/.venv/bin/python -m pytest companion/test_oidc.py companion/test_access.py server/test_fleet_sessions.py -x -q -p no:cacheprovider` |
| **Full suite command** | `./scripts/run-all-tests.sh` |
| **Other gates** | ruff, mypy, `scripts/check_function_size.py check --max 80 server stub-server`, `scripts/check_comment_history.py check` |
| **Estimated runtime** | ~300 seconds full, ~15 seconds quick |

## Sampling Rate

- **After every task commit:** quick command for the touched module plus ruff and mypy
- **After every plan wave:** full suite
- **Before verify-work:** full suite green, Phase 48 freeze test green
- **Max feedback latency:** 30 seconds (quick)

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------------|-----------|-------------------|-------------|--------|
| (filled by planner) | | | AUTH-01..03, AUTH-06 | | | | ❌ W0 | ⬜ pending |

## Wave 0 Requirements

- [ ] `test-support/fake_auth0.py` + `test-support/test_fake_auth0.py`
- [ ] `companion/test_oidc.py`, `test_auth0_login.py`, `test_auth0_cookies.py`, `test_browser_auth0.py`, `test_legacy_admin.py`, `test_sessions_http.py`, `test_access_matrix.py`, `test_account_page.py`; `server/test_fleet_sessions.py`
- [ ] Rewrite Section 1 of `companion/test_companion_app_01.py`; update `test_route_table.py`

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real-tenant smoke test: login works, wrong `code_verifier` rejected, sign-out returns to the allowed URL | AUTH-01 | Needs the owner's real Auth0 tenant; tests never leave loopback | Owner step after merge, documented in `deploy/README.md` |
| Caddy `/callback` query redaction | AUTH-01 | Caddy is not installed in CI | Validate `caddy validate` on the VPS |

## Validation Sign-Off

- [ ] All tasks have automated verify or Wave 0 dependencies
- [ ] No 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
