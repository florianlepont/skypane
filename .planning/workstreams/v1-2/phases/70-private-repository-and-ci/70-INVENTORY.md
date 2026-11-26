# Phase 70 Inventory: what has been public

Status: complete. The full-history scan was run by the owner on 2026-11-26 and every row has a decision (plan 70-08 Task 3).
No matched text, key material, e-mail address or IP address appears in this document.
Rows carry only class, file, commit (short) and counts.

## Method

Tool: `scripts/exposure_scan.py` (stdlib only). Two modes:

- `tree`: tracked files at HEAD.
- `history`: every line ever added on any ref (`git log --all -p --text`).

Classes: `pem-private-key`, `aws-access-key`, `github-token`, `slack-token`, `api-key-sk`, `bearer-literal`, `assigned-secret`, `email-non-noreply`, `ipv4-public`. Private, loopback, link-local, reserved and documentation IPv4 ranges, `users.noreply.github.com`, `example.com|org|net` addresses and `noreply` local parts are not reported. The scan script and its test file are excluded from their own results.

Scan limits of the run recorded below: **the working-tree and history scans in this document were run on a shallow sandbox clone only** (the tool printed `warning=shallow-clone history-incomplete`; 101 commits visible, all added lines of the shallow boundary commit show as one commit, `7611000`). Everything about deleted branches, pull request heads and older history is unknown until the owner runs the mirror scan below. Numbers in this document are therefore a lower bound for history and exact for the tree at the time of the run.

Full mirror scan (owner, on the Mac, full clone, not the sandbox):

```
git clone --mirror <repository url> skypane-mirror.git
cd skypane-mirror.git
git fetch origin '+refs/pull/*:refs/pull/*'
python3 <checkout>/scripts/exposure_scan.py history --repo . --format tsv > ~/skypane-scan.tsv
```

The TSV carries type, file, commit and count only. Optional second opinion: gitleaks with `--redact`, installed by the owner after checking the formula source and the installed version's flags (`gitleaks --help`). Send the session only counts per type and the file path and short commit of any row in a secret class, never a value.

## Findings

Sandbox run, shallow clone (tree identical to `main` at the time of the run).

| Type | Tree: rows (files) | History (shallow): rows | Files / commits | Disposition | Owner decision |
|------|--------------------|-------------------------|-----------------|-------------|----------------|
| pem-private-key | 0 | 0 | none | none found here | none found in the full history; no action; decided by the owner (delegated to the session, 2026-11-26) |
| aws-access-key | 0 | 0 | none | none found here | none found; no action; decided by the owner (delegated to the session, 2026-11-26) |
| github-token | 0 | 0 | none | none found here | none found; no action; decided by the owner (delegated to the session, 2026-11-26) |
| slack-token | 0 | 0 | none | none found here | none found; no action; decided by the owner (delegated to the session, 2026-11-26) |
| api-key-sk | 0 | 0 | none | none found here | none found; no action; decided by the owner (delegated to the session, 2026-11-26) |
| bearer-literal | 1 | 1 | `.planning/STATE.md`, commit `7611000` | to eyeball: likely documentation of a header shape, not a credential | false positive (documentation text, no value) checked by the session with values masked; leave; decided by the owner (delegated to the session, 2026-11-26) |
| assigned-secret | 15 (15) | 15 | 13 test files and fixtures plus 2 non-test files (`companion/export_api.py`, `companion/static/freshness.js`), all at commit `7611000` (list below) | likely test fixtures and UI string defaults; owner confirms by eye, file and line only | false positives: test fixtures, variable names and documentation (checked with values masked); leave, no rotation; decided by the owner (delegated to the session, 2026-11-26) |
| email-non-noreply | 105 (105) | 189 rows in 149 files | tree areas: `.planning` 20, `companion` 59, `server` 8, `test-support` 8, `deploy` 5, `hardware` 2, `COMPLIANCE.md` 1, `scripts` 1, `stub-server` 1 | likely test fixtures and documentation addresses; per-file owner check | fictitious test addresses and one personal address in a phase 64 note; leave in the private repository; decided by the owner (delegated to the session, 2026-11-26) |
| ipv4-public | 24 (24) | 25 rows in 24 files | tree areas: `.planning` 15, `companion` 3, `hardware` 3, `server` 3 | VPS address is public through DNS; SSH exposure details in `.planning` are not meant to be public | version numbers, reserved test addresses, and the server address (public through DNS) in two notes; leave in the private repository; decided by the owner (delegated to the session, 2026-11-26) |

Files in the `assigned-secret` class (tree and history agree; to check by eye, no values here):

- `companion/export_api.py`
- `companion/static/freshness.js`
- `companion/test_co_managers_page.py`
- `companion/test_companion_app_05.py`
- `companion/test_config_page_04.py`
- `companion/test_export_battery_helpers.py`
- `companion/test_export_battery_history.py`
- `companion/test_export_debug_routes.py`
- `companion/test_nav_personal_console.py`
- `companion/test_server_error_page.py`
- `companion/test_sessions_http.py`
- `server/test_calendar_rules.py`
- `server/test_fleet_db.py`
- `stub-server/test_fleet_cli.py`
- `test-support/companion_render_snapshot.py`

Tracked files whose names look sensitive but are not secrets (from the research, to be confirmed by the owner's scan): `deploy/skypane.env.example`, `firmware/main/enrol_secret.c` and `.h` (code that reads the per-device enrolment secret from NVS; values live in device flash and on the VPS, not in git), the ISRG root certificates, `firmware/signing/skypane-signing-pubkey.pem` (public key).

## Personal data surfaces

- The owner's full name in `firmware/SIGNING.md` (decision record) and `README.md`.
- The owner's GitHub login.
- Location and home runway data in `adsb-test/runway3.json` and in hardware logs.
- Git author e-mail addresses in commit metadata (cannot be rewritten for copies already taken).
- Public-facing text in `SECURITY.md` and `CONTRIBUTING.md` that assumes public reporting and public contributions.

## Commercial planning notes in .planning

Areas only, no content quoted (1,508 tracked files, 71 MB at the time of the research):

- `.planning/seeds/SEED-015-business-plan-and-go-to-market-feasibility.md` and 6 further seed files with commercial keyword matches.
- `.planning/research/` and `.planning/workstreams/v1-2/research/` (summary, features, pitfalls, stack, architecture).
- `.planning/notes/` (35 files, including an operations board and a design brief).
- Phase directories with commercial keyword matches, clustered in phases 68, 61, 62, 56, 64 and 69.

## Other public surfaces

Counts taken from the anonymous API during the research session (anonymous reads work while the repository is public; they stop working after the switch to private):

- Stars 1, forks 0, watchers 1.
- 8 releases with assets (signed images, manifests, bootloader and partition binaries). Signing public key and release images are public by design.
- 451 Actions artifacts and 1,769 workflow runs with public logs. Hostnames and paths in logs stay in anyone's cache.
- 544 pull requests and one further issue thread; pull request and issue text is public and is reviewed by the owner.
- Pages, wiki and discussions are off.
- The MIT licence history before the licence change (last MIT commit `efafc89`, 2026-09-23): that history stays usable under MIT.

## Copies already taken stay public

copies already taken stay public. That covers any clone (including the one stargazer's possible copy), archive and search caches (Wayback, Software Heritage, search engines), and the MIT-licensed history before the licence change. Making the repository private does not revoke any of it.

History is not rewritten. `git filter-repo` would change only the live repository, would break every SHA that the deploy, the tags and the `fw-v*` releases rely on, and would not touch copies already taken. The rule is therefore: anything sensitive is rotated by the owner on the provider side rather than hidden. A session never prints, uses, rotates or deletes a secret. The signing key was never in git and does not need rotation unless the owner chooses a transition release (see `firmware/SIGNING.md`, "Rotation").

## Repeat command

Tree, any checkout:

```
python3 scripts/exposure_scan.py tree --repo . --fail-on-find
```

Full history, on a mirror (see Method):

```
python3 scripts/exposure_scan.py history --repo skypane-mirror.git --format tsv
```

## Decisions needed from the owner

Options per row: leave, remove from the tree going forward, rotate. Decision column left blank on purpose; filled with "decided by the owner" and the date after the checkpoint.

| Item | Options | Decision |
|------|---------|----------|
| Full mirror scan result (counts per type, any secret-class file/commit not in the sandbox run) | report to session | done: full mirror scan (history and pull request refs) run on the owner's machine on 2026-11-26: 821 rows, 695 e-mail-shaped, 77 public IPv4, 48 assigned-secret, 1 bearer-literal; no private key, AWS, GitHub, Slack or sk- token; decided by the owner (delegated to the session, 2026-11-26) |
| bearer-literal (1 row, `.planning/STATE.md`) | leave / remove going forward / rotate | leave; decided by the owner (delegated to the session, 2026-11-26) |
| assigned-secret (15 files listed above) | leave (fixture) / remove going forward / rotate | leave (fixtures and variable names, no real value); decided by the owner (delegated to the session, 2026-11-26) |
| email-non-noreply (105 tree files) | leave / remove going forward | leave (fictitious addresses; one personal address in a phase 64 note stays in the private repository); decided by the owner (delegated to the session, 2026-11-26) |
| ipv4-public (24 tree files, VPS address and SSH details in `.planning`) | leave / remove going forward | leave (version numbers, test addresses and the server address, public through DNS); decided by the owner (delegated to the session, 2026-11-26) |
| Auth0 tenant and client identifiers, if the mirror scan shows any | leave / rotate | not covered by the scan classes; leave (identifiers are not secrets); decided by the owner (delegated to the session, 2026-11-26) |
| Signing key (never in git; was held as a GitHub environment secret) | leave / rotate through a transition release | leave (key kept by the owner, held only in his encrypted vault); decided by the owner (delegated to the session, 2026-11-26) |
| Commercial notes: seed files | leave / remove going forward | leave in the private repository; decided by the owner (delegated to the session, 2026-11-26) |
| Commercial notes: research directories | leave / remove going forward | leave in the private repository; decided by the owner (delegated to the session, 2026-11-26) |
| Commercial notes: `.planning/notes/` | leave / remove going forward | leave in the private repository; decided by the owner (delegated to the session, 2026-11-26) |
| Commercial notes: phase directories 68, 61, 62, 56, 64, 69 | leave / remove going forward | leave in the private repository; decided by the owner (delegated to the session, 2026-11-26) |
| Personal data surfaces (name, runway and location data, `SECURITY.md`, `CONTRIBUTING.md`) | leave / remove going forward / reword | leave (private repository); decided by the owner (delegated to the session, 2026-11-26) |
| Other public surfaces (releases, artifacts, PR and issue text, workflow logs) | leave / delete artifacts and logs | leave (the repository becomes private, which hides existing logs and artifacts; copies already taken stay public); decided by the owner (delegated to the session, 2026-11-26) |

## Follow-ups

None. Every decision is "leave": no secret needed rotation, and nothing is removed from the tree. Optional, if the owner changes his mind later: reword the personal address and the server address in the notes of the hardware bring-up log and the phase 64 walkthrough (a removal never erases copies already taken).
