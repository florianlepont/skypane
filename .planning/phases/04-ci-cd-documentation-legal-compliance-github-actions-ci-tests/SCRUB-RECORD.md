# Git History Scrub Record

**Date:** 2026-08-26
**Plan:** 04-01 (Task 2 decision, Task 3 execution)
**Tool:** `git-filter-repo` 2.47.0 (installed via Homebrew for this operation)

This record documents that a pre-publish git history scrub ran and was verified. It intentionally contains **no scrubbed literal values** — only categories, counts, and verification results. Anyone auditing this repo can confirm the scrub happened without this file re-leaking what it removed.

## Decision (Task 2)

The developer selected **option `a-b-c`: scrub Categories A + B + C in full**, out of the three options presented (`a-only`, `a-b-c`, `a-b`). No additional literals beyond these three categories were requested.

- **Category A** (D-05, locked): the VPS public IPv4 and the VPS DNS hostname.
- **Category B**: the home Wi-Fi network name (plaintext SSID), the router BSSID, and the device's own MAC address, both found in `hardware/logs/first-light.log` and `hardware/logs/backoff-run.log`.
- **Category C**: the home street address, found in 4 tracked planning documents (`.planning/PROJECT.md`, `.planning/ROADMAP.md`, `01-CONTEXT.md`, `01-RESEARCH.md`).

## Scope executed

| Category | Literal count (distinct replacement-file entries) |
|----------|-----------------------------------------------------|
| A (VPS IP + hostname) | 2 |
| B (Wi-Fi SSID, BSSID, device MAC) | 3 |
| C (full address in two punctuation variants + bare city name, to catch the standalone city-only mention) | 3 |
| **Total** | **8** |

## Replacement-token style

Angle-bracket placeholder tokens, matching the convention `deploy/README.md` already used pre-scrub (`<vps-ip>`, `<public-host>`). New tokens introduced for Category B/C follow the same style: `<wifi-ssid>`, `<wifi-bssid>`, `<device-mac>`, `<street-address>`, `<home-city>`. No sentinel/all-caps `REDACTED`-style tokens were used — `deploy/README.md` and the affected `.planning/` prose read as coherent English after the rewrite.

## Backup

A `git bundle create --all` of the full pre-rewrite history was taken before `filter-repo` ran, stored **outside** the repository tree:

- **Path:** `/Users/florian/ink-frame-backups/ink-frame-pre-scrub-20260826T185603Z.bundle`
- **Verification:** `git bundle verify` on that path reported the bundle correct and confirmed it records the complete history (all 4 refs present at backup time: `main`, the by-then-already-redundant `claude/faience-blanche-mate-434eeb` worktree branch, a `refs/codex/turn-diffs/checkpoints/...` automation tree ref, and `HEAD`).

## Commit range affected

- Pre-rewrite commit count (`git rev-list --all --count`): **154**
- Post-rewrite commit count (`git rev-list --all --count`): **154**
- No commits were dropped — every commit's tree/message content was rewritten in place; hashes changed but the count, authorship, and dates did not.
- Pre-rewrite `main` HEAD: `2d34c22a4e2c0a79ec44214325e2860e9bc07436`
- Post-rewrite `main` HEAD: `8c89617e0b8c1730414af51d814be4b1100a6fe1`

## Execution notes / deviations from the literal plan steps

1. **`--replace-text` alone was insufficient — a literal survived in a commit message, not file content.** The first scratch-clone pass (using only `--replace-text`) left the device MAC present in one commit's message body (`feat(01-06): flash EE02 image...`, describing a successful flash verification). `git filter-repo --replace-text` only rewrites blob (file) content by design; commit/tag message text requires the separate `--replace-message` flag. Diagnosed per Task 3 Step 6's instruction, fixed by re-running the scratch-clone rewrite from a fresh clone with **both** `--replace-text` and `--replace-message` pointed at the same expressions file. Re-verification after the second pass returned zero matches. *(Rule 1 — bug in the execution approach, fixed before proceeding, no scope change.)*
2. **A stale, fully-redundant branch ref was deleted before the final prune.** `refs/heads/claude/faience-blanche-mate-434eeb` — the branch the worktree removed in Task 1 (F4) had been checked out to — remained in the real repo after Task 1, pointing at the old pre-rewrite history. Confirmed via `git log main..claude/faience-blanche-mate-434eeb` (0 unique commits) that it carried no content not already in `main`, and confirmed it was fully captured in the pre-rewrite backup bundle before deletion. Left in place, it would have (a) kept old unscrubbed objects reachable and defeated `git gc --prune` exactly as F4 describes for the worktree pin, and (b) caused the post-rewrite `git log --all -p` re-verification to still show pre-rewrite content via that ref. Deleted with `git branch -D` after the history re-home (Step 7) and before the reflog expire / gc (Step 8). *(Rule 3 — blocking issue for this plan's own verification gate, same category as the already-planned worktree removal.)* A `refs/codex/turn-diffs/checkpoints/...` ref (an automation checkpoint pointing directly at a tree object, not a commit) was left untouched — confirmed it contains none of the scrubbed literals and, being a non-commit ref, is never traversed by `git log --all`, so it does not affect the scrub invariant.
3. **The plan's own Task 3 automated verify string needs `grep -a` to be reliable on this machine's grep.** `git log --all -p | grep -c -F -f .git/inkframe-scrub-literals.txt` (exactly as written in the plan and in this plan's top-level `<verification>` section) intermittently prints **nothing** instead of `0` on a fully-clean history, because this repo's history includes binary diffs (vendored font blobs) that make GNU/BSD `grep` treat the whole piped stream as binary and suppress its count line once it hits them — not because a match exists. Confirmed by running the identical command with `-a` (treat input as text) immediately after, which reliably prints `0`. This is a verify-script portability note, not a defect in the scrub itself — recorded here in the same spirit as Task 1's already-documented `git check-ignore -q` multi-path portability note. All verification below was run with `-a` to get a trustworthy result.

## Verification (post-rewrite, real repo)

All commands read only from the untracked `.git/inkframe-scrub-literals.txt` derived file — no literal value appears in any command below, in this file, or in any commit.

| Check | Command | Result |
|-------|---------|--------|
| History content, all refs | `git log --all -p \| grep -a -c -F -f .git/inkframe-scrub-literals.txt` | `0` |
| Working tree at HEAD | `git grep -c -F -f .git/inkframe-scrub-literals.txt HEAD -- .` | no output (zero matches) |
| Worktree count | `git worktree list \| wc -l` | `1` |
| Backup bundle integrity | `git bundle verify <backup path above>` | passed ("bundle records a complete history") |
| Commit count preserved | `git rev-list --all --count` (before vs. after) | `154` → `154` |
| Old objects purged | `git reflog expire --expire=now --all && git gc --prune=now --aggressive`, then `git cat-file -t <pre-rewrite HEAD hash>` | fails with "could not get object info" — old objects are gone from the local store |
| Placeholder prose readability | manual read of `deploy/README.md` and affected `.planning/` prose post-rewrite | reads as coherent English, using the pre-existing angle-bracket convention |
| Test suite unaffected | all 9 harnesses (`server/test_dither.py`, `server/test_enrich.py`, `server/test_illustrations.py`, `server/test_pipeline_e2e.py`, `server/test_plane_detection.py`, `server/test_poll_loop.py`, `server/test_render.py`, `server/test_runway_config.py`, `stub-server/test_poll_cycle.py`) under `server/.venv/bin/python3` | all exit `0` |

## Rollback path (first pass)

If the first rewrite is ever found to be incomplete or wrong, the pre-rewrite history is fully recoverable from the verified bundle at the path recorded above (`git clone <bundle-path> <restore-dir>`), which predates any object pruning.

---

# Second pass (Category D)

**Date:** 2026-08-26
**Plan:** 04-06 (Task 1 pre-flight finding, executed as a standalone pass before Task 1's own gate could pass)
**Tool:** `git-filter-repo` (same install as the first pass)

Plan 04-06's Task 1 pre-flight publication-surface review found two real issues. This pass addresses the one the developer approved for scrubbing; the other was explicitly declined and is recorded below as a deliberate non-scrub decision.

## Findings reviewed with the developer

- **Finding A — scrubbed (this pass):** real supplier order numbers and a payment note in plain text, in `hardware/BOM.md` and `hardware/BRINGUP-LOG.md` (and, as discovered during this pass's own occurrence scan, also present in `.planning/STATE.md`, `.planning/phases/01-foundation-hardware-bring-up-ads-b-validation/01-01-SUMMARY.md`, and `.planning/phases/01-foundation-hardware-bring-up-ads-b-validation/01-VERIFICATION.md`, which the Task 1 pre-flight review had not itemized by filename). The developer approved scrubbing this category in full.
- **Finding B — explicitly declined, not touched:** the real commit-author email present in all commits' author metadata. The developer was asked whether to replace it with a GitHub noreply address and said to leave it as-is; no `--mailmap` or author-rewriting operation was run in this pass or any other. This is a deliberate, recorded decision, not an oversight.

## Scope executed

| Category | Literal count (distinct replacement-file entries) |
|----------|-----------------------------------------------------|
| D (two supplier order numbers + one payment-note phrase) | 3 |

## Replacement-token style

Same angle-bracket placeholder convention as the first pass, appended to the same untracked expressions/literals files (`.git/inkframe-scrub-expressions.txt`, `.git/inkframe-scrub-literals.txt` — reconstructed for pass one's 8 entries plus these 3, since the files are untracked and had survived on this machine since pass one). New tokens: `<seeed-order-ref>`, `<kubii-order-ref>`, and a placeholder that replaces the whole payment-note phrase (order total + payment method + accepted-status) with a single redaction token, since that phrase reads as one disclosure rather than several independent facts.

## Backup

A fresh `git bundle create --all` was taken before this rewrite — the first pass's bundle predates plans 04-02 through 04-05 and does not cover this history:

- **Path:** `/Users/florian/ink-frame-backups/ink-frame-pre-scrub2-20260826T195853Z.bundle`
- **Verification:** `git bundle verify` on that path reports the bundle correct, recording the complete history at 3 refs (`main`, `HEAD`, and the `refs/codex/turn-diffs/checkpoints/...` automation tree ref — see the finding on that ref below; this bundle is also its only remaining record now that the ref has been deleted from the live repo).

## Commit range affected

- Pre-rewrite commit count (`git rev-list --all --count`): **172**
- Post-rewrite commit count: **172**
- No commits were dropped; hashes changed, count/authorship/dates did not.
- Pre-rewrite `main` HEAD: `156d583c55e379b856bcf02d6dfbe24e8dfc96ae`
- Post-rewrite `main` HEAD (also the head this pass's rewrite produced): `696f7035dd5518e0ac13d4c52c0d496c1228b92d`

## Execution notes / deviations from the literal plan steps

1. **Both `--replace-text` and `--replace-message` were run from the start**, pointed at the same combined (8 old + 3 new) expressions file, in a fresh scratch mirror clone — applying the lesson the first pass's Execution note #1 already recorded, rather than repeating that gap. Commit-message occurrence check (`git log --all --format="%H %s%n%b" | grep -c`) found 1 occurrence of each order number in a commit message and 0 of the payment-note phrase; both are covered by `--replace-message`.
2. **A stray non-commit ref was found to leak content the first pass had certified clean — corrected here (Rule 1).** `refs/codex/turn-diffs/checkpoints/...` — a Codex CLI automation checkpoint pointing directly at a tree object, not a commit, first noted (and left in place) in the first pass's Execution note #2 — was re-checked in this pass because this plan's own gate requires zero occurrences "across all refs," not only the refs `git log --all` walks. It failed that check: `git grep -c -F -f <literals-file> <tree-hash> -- .` returned matches for **all 8** of the first pass's Category A/B/C literals, plus the 3 new Category D literals, across 16 files in that tree snapshot — i.e. the first pass's SCRUB-RECORD statement that this ref "contains none of the scrubbed literals" was incorrect. `git-filter-repo` cannot rewrite this ref (it only walks commit history; it printed `avertissement : ... objet de type tree inattendu, ignoré` and skipped it, in both passes), so rewriting it in place was not an option. Confirmed it is not reachable from `main` (`git merge-base --is-ancestor` errors because it isn't a commit) and is not walked by `git log --all -p` (matching the first pass's traversal claim, which was accurate — only its content-cleanliness claim was wrong). Since it carries no project value (a Codex automation artifact, analogous in kind to the stale worktree branch ref the first pass deleted) and its content is fully preserved in this pass's pre-rewrite backup bundle, it was deleted with `git update-ref -d` before the final reflog-expire/gc. *(Rule 1 — correcting an inaccurate prior verification result that this pass's own "across all refs" gate surfaced; the fix is a ref deletion already precedented by the first pass's own established handling of non-essential refs, not a new architectural decision.)*

## Verification (post-rewrite, real repo)

All commands read only from the untracked `.git/inkframe-scrub-literals.txt` derived file (now 11 entries: the first pass's 8 plus this pass's 3) — no literal value appears in any command below, in this file, or in any commit.

| Check | Command | Result |
|-------|---------|--------|
| History content, all refs (combined 11-entry literal set, so both passes re-verified together) | `git log --all -p \| grep -a -c -F -f .git/inkframe-scrub-literals.txt` | `0` |
| Working tree at HEAD | `git grep -c -F -f .git/inkframe-scrub-literals.txt HEAD -- .` | no output (zero matches) |
| Refs present after cleanup | `git for-each-ref` | only `refs/heads/main` |
| Worktree count | `git worktree list \| wc -l` | `1` |
| New backup bundle integrity | `git bundle verify <second-pass bundle path above>` | passed ("bundle records a complete history") |
| First-pass backup bundle still present and verifying | `git bundle verify <first-pass bundle path>` | passed |
| Commit count preserved | `git rev-list --all --count` (before vs. after) | `172` → `172` |
| Old objects purged | `git reflog expire --expire=now --all && git gc --prune=now --aggressive`, then `git cat-file -t <pre-rewrite HEAD hash>` and `git cat-file -t <deleted checkpoint tree hash>` | both fail with "could not get object info" — old objects and the deleted ref's tree are gone from the local store |
| Placeholder prose readability | manual read of `hardware/BOM.md` and `hardware/BRINGUP-LOG.md` post-rewrite | reads as coherent English, using the same angle-bracket convention |
| Working tree clean | `git status --porcelain` | empty |
| Lint unaffected | `server/.venv/bin/ruff check .` | `All checks passed!` |
| Test suite unaffected | `./scripts/run-all-tests.sh` (all 9 harnesses) | `Result: PASS` |
| Attribution check unaffected | `./scripts/check-attribution.sh` | `PASS` |

The rewrite touched only documentation content (`hardware/BOM.md`, `hardware/BRINGUP-LOG.md`, `.planning/STATE.md`, and two `.planning/phases/01-.../` files); no executable code path changed, which the unaffected test/lint/attribution results above confirm.

## Rollback path (second pass)

If this second rewrite is ever found to be incomplete or wrong, the state immediately before it (including the now-deleted `refs/codex/...` checkpoint ref) is fully recoverable from the verified bundle at the path recorded above (`git clone <bundle-path> <restore-dir>`), which predates both this rewrite and the ref deletion.
