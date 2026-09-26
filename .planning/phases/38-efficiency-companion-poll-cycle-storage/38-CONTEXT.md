# Phase 38: Efficiency — companion, poll cycle, storage - Context

**Gathered:** 2026-09-26
**Status:** Ready for planning
**Source:** The developer's planning brief for `/gsd-plan-phase 38`, the audit ledger (`.planning/audits/2026-09-23-code-audit.md`), `38-RESEARCH.md`, and two decisions asked in French during planning.

<domain>
## Phase Boundary

Remediate EFF-01..EFF-06 at the **behaviour level**. The phase changes when and how often work happens (static bytes, scripts per page, SQLite connections, Health markup, `poll_state` writes, provider waits). It does not change where code lives. Every item gets its before/after measurement instrument **before** its change.

Re-location on `main` f4d9709 (see `38-RESEARCH.md` §Phase Requirements): all six items are still open. Nothing is dropped.
- EFF-01 is **partly solved** by Phase 35. The comment purge cut `style.css` from 510 KB to 140 KB, so the "85 % comments" part of the finding is closed; the remaining 44 % comment share is left alone. Compression, validators and in-memory bytes are all still missing.
- EFF-05 is **partly solved** by Phase 36. Writes are atomic now, but there are still 1–2 per cycle, even when nothing changed, and they are written with `indent=1`.
- EFF-03: the ledger's "16 connections per request" is 9–12 today. It is still open.
</domain>

<decisions>
## Implementation Decisions

### Developer decisions (asked 2026-09-26, answered in French)
- **D-1: `Cache-Control` for companion CSS/JS is `no-cache`** (with a strong ETag and Last-Modified), replacing `max-age=300`. Every load revalidates and gets a bodiless 304 when unchanged, so success criterion 2 is observable and no page runs new HTML against old JS after a deploy. Content-hashed URLs are rejected: they overlap Phase 40's CMP-02.
- **D-2: freshness uses a conditional GET on the same page URL.** The server computes a token from the page's inputs (state files, history rows, config, gallery, time thresholds) **without rendering the page**, and answers 304 when the client's token matches. `freshness.js` sends the token and forces a full refresh every ~5 min to bound any input the token misses. There is **no new `/freshness` route** (that would pre-empt Phase 40's route table) and no ETag computed from the rendered body (that saves no CPU).

### Locked by the ledger, ROADMAP and brief
- EFF-01: `encode zstd gzip` goes in the **companion** site block of `deploy/Caddyfile`, never in the device (byos) block. The file is SkyPane's own site snippet imported by a shared host Caddyfile (Phase 37): site blocks only, no global options. Static bytes are cached in memory, with ETag/Last-Modified and 304 handling.
- EFF-02: only the scripts each page uses, with no build step.
- EFF-03: one SQLite connection per request and per poll cycle, the schema run once per process (per database file identity), one transaction per cycle, and no write transaction held across a network call (ntfy).
- EFF-04: lazy `page_context`, Health severity computed without building markup, and the D-2 freshness mechanism.
- EFF-05: `poll_state.json` saved at most once per cycle, only if changed, written compact.
- EFF-06: providers queried in parallel with each provider's rate limit kept, including across back-to-back cycles (a timer cycle followed by `/poll-now`). Results are collected in provider order, so the first provider still wins on agreement.
- Instruments first. Tests follow the Phase 32/33 conventions: pytest, no network (pytest-socket), behaviour not source text (`companion/test_suite_guards.py`), shared app-server fixtures. Before and after numbers go in a committed `38-EFF-BASELINE.md`, the same pattern as `37-SEC-BASELINE.md`. Timings are recorded, not asserted; counts are asserted.
- No new runtime dependency. Code, comments and docs are in English. No phase, plan or requirement IDs go in comments.

### Claude's Discretion
- Helper names, the probe module layout, and how per-page script tuples are declared.
- Letting `poll_cooldown_remaining` degrade to 0 on a database error inside the lazy loader. This is a small robustness change; it is fine to do.
- Correcting the adsb.lol rate-limit wording in `COMPLIANCE.md`.
</decisions>

<canonical_refs>
## Canonical References

- `.planning/audits/2026-09-23-code-audit.md`: ledger rows EFF-01..06, decisions D-A1..D-A6
- `.planning/phases/38-efficiency-companion-poll-cycle-storage/38-RESEARCH.md`: current locations, designs, pitfalls, baseline numbers
- `.planning/phases/37-security-and-operations-hardening/37-SEC-BASELINE.md`: the baseline-document pattern
- `.planning/phases/37-security-and-operations-hardening/37-11-PLAN.md`: touches `deploy/` and `stub-server/`, and is executing in another session
- `.planning/phases/42-*/`: OTA (later) touches `companion/app.py`, `layout.py`, `server/poll_loop.py`
- `companion/test_suite_guards.py`, `companion/conftest.py`, `test-support/companion_app_server.py`: test conventions
- `.claude/CLAUDE.md`, `scripts/check_comment_history.py`: conventions
</canonical_refs>

<specifics>
## Coordination

- Do not touch `stub-server/byos_server.py` (37-11 and 42 both touch it). Avoid `deploy/README.md` (37-11 and 42 both edit it).
- `deploy/Caddyfile` and `deploy/tests/test_caddyfile.py` are not touched by 37-11.
- Merge conflicts with 42 are expected in `companion/app.py` and `companion/layout.py`. The per-page script coverage test will catch an OTA Update page that lands without a script tuple.
- The line with Phases 39/40: no new modules beyond small helpers in existing files, no route table, no typed context, no named templates, no `state_store`, no `CycleContext`. `run_once` keeps its shape.
</specifics>

<deferred>
## Deferred Ideas

- **CFG-50** (Display page height ~3,743 px vs a 2,600 px target): not in Phase 38's scope.
- Further `style.css` reduction and CSS de-duplication: Phase 40 (CMP-08).
- Content-hashed static URLs / a static allowlist: Phase 40 (CMP-02).
</deferred>

---
*Phase: 38-efficiency-companion-poll-cycle-storage*
