---
phase: 16
slug: calendar-linked-flight-highlighting-a-connected-calendar-sou
status: draft
nyquist_compliant: false
wave_0_complete: false  # Wave 0 items: the new harness AND the redacted fixture it depends on
created: 2026-09-07
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `16-RESEARCH.md` § Validation Architecture, including its
> two appended corrections. Written before the planner runs, so Task IDs
> below are **slots** — the planner assigns real `16-NN-MM` ids and must
> carry every row into a task's `<verify>` or `must_haves`.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Hand-rolled stdlib `check(name, fn)` harness per file, with an `EXPECTED_CHECK_COUNT` ledger that makes the file exit non-zero on a count mismatch. NOT pytest, NOT unittest. Do not introduce a framework, a `conftest.py`, or any package. |
| **Config file** | none — `scripts/run-all-tests.sh`'s `HARNESSES` array is the single source of truth for what runs |
| **Quick run command** | `server/.venv/bin/python3 server/test_calendar_rules.py` (new) — or whichever single harness the task touched |
| **Full suite command** | `scripts/run-all-tests.sh` (18 harnesses today, 19 after this phase registers the new one), under `coverage`, enforcing the `pyproject.toml` floor |
| **Estimated runtime** | ~60 seconds full suite; a single harness is sub-second |

---

## Sampling Rate

- **After every task commit:** the specific new or extended harness for the file just touched.
- **After every plan wave:** `scripts/run-all-tests.sh`, coverage floor enforced.
- **Phase gate:** full suite green, **plus a mandatory `/gsd-secure-phase 16`** — this phase introduces the project's first operator-supplied outbound fetch and its first runtime secret outside `companion/auth.py`.
- **Max feedback latency:** 60 seconds.

**Accepted pre-existing exception.** `companion/test_companion_app.py` carries a load-sensitive `/poll-now` concurrency check that flakes under suite load and is already filed as separate follow-up work. A single failure of that one check, passing on re-run, is not a Phase 16 regression. Any other failure is.

---

## Per-Task Verification Map

No REQUIREMENTS.md ID maps to this phase — unmapped, promoted from a seed, the Phase 10-15 precedent. Rows trace to `16-CONTEXT.md`'s decisions.

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| TBD | parser | 0 (W0) | Parser | T-16-INPUT | RFC 5545 line unfolding is handled: a folded `DESCRIPTION`/`SUMMARY` continuation line (leading space or tab) is joined before parsing, not treated as a new property | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | parser | 0 (W0) | Parser | T-16-INPUT | Junk is filtered, not ingested: `STATUS:CANCELLED` events and the 1899 placeholder dates are dropped; only `CATEGORIES:FLT` becomes a match candidate, never `OFFD`/`CAHC`/`CPBL` | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | parser | 0 (W0) | Parser / CORRECTION 2 | — | `DTSTART`/`DTEND` parse as bare UTC (measured: 63/63 events, zero `TZID`). An unrecognised date form is **rejected loudly**, never guessed — a future producer change must fail, not silently mis-time a match | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | parser | 0 (W0) | Parser | T-16-DOS | A malformed, truncated, or hostile feed body degrades to an empty candidate list and never raises — the poll cycle must survive a bad feed | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | fetch | 1 | Research target 3 | T-16-SSRF | A URL resolving to a private, loopback or link-local address is refused. Validation is on the **resolved IP** after `getaddrinfo()`, not the hostname, and is re-applied per redirect hop | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` (injectable transport) | ❌ W0 | ⬜ pending |
| TBD | fetch | 1 | Research target 3 | T-16-DOS | Response size is capped by streaming, never by trusting `Content-Length`; redirects are bounded; the request has a hard timeout | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | fetch | 1 | Research target 4 | T-16-SECRET | **The secret never appears in a log line.** Specifically: `requests.exceptions.*` embed the request URL in their default string form, so the codebase's existing `str(exc)` logging idiom would leak it. Assert no log path emits the URL or any substring of it | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | fetch | 1 | Research target 4 | T-16-SECRET | The secret never reaches `state_dir` and never reaches a rendered page. The persisted registry contains parsed events only; the Settings page renders configured-state text only | unit + integration | `server/.venv/bin/python3 server/test_calendar_rules.py`, `companion/test_config_page.py` | ✅ extend | ⬜ pending |
| TBD | fetch | 1 | Research target 2 | T-16-DOS | The throttle genuinely prevents a per-cycle fetch: repeated `run_once()` calls inside the throttle interval perform exactly one fetch. Uses an injected fake clock, mirroring `poll_loop.now_s()`'s existing seam | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | fetch | 1 | Research target 2 | — | Two distinct timestamps exist and mean different things: `last_attempt_at` gates the throttle and updates on every try; `last_synced_at` drives the UI copy and updates only on success. A permanently failing feed must not be retried every 30s, and must not read as fresh | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | matcher | 2 | D-04 / CORRECTION 1 | — | **Match truth table**: airline + far-end airport + time window. The airline half compares the calendar's 2-letter prefix against the leading letters of `route["callsign_iata"]` — **no static IATA↔ICAO table** (measured: the bridge already exists at runtime). Far end is destination for a departure, origin for an arrival | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | matcher | 2 | D-04 | — | A match **cannot** fire when `route_source` is `airline_only`, `manual` or `miss` — `origin_iata`/`destination_iata`/`callsign_iata` are only populated on `fresh_hit`/`cache_hit`. Assert this explicitly rather than discovering it in production | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | matcher | 2 | D-04 | — | Same-route ambiguity resolves to the candidate closest in time, never to both and never to neither (measured: the two daily NCE-ORY rotations sit ~8h apart) | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | resolver | 2 | D-02 | T-16-TAMPER | **Calendar beats a manual rule — including an exact-callsign rule**, the narrowest thing an operator can write. Order: calendar → callsign → hex → prefix → arrivals override → base theme. The developer accepted this consequence explicitly | unit | `server/.venv/bin/python3 server/test_colour_rules.py` | ✅ extend | ⬜ pending |
| TBD | resolver | 2 | D-02 | T-16-TAMPER | A `theme_id` arriving from the calendar registry is membership-tested against `device_config.THEMES` before it can reach `render.build_canvas()`, exactly as Phase 15's T-15-05 requires of rule themes | unit | `server/.venv/bin/python3 server/test_colour_rules.py` | ✅ extend | ⬜ pending |
| TBD | registry | 1 | D-01 | — | Calendar entries are **never** written into `colour_rules.json`. After a fetch, `colour_rules.load_colour_rules()` returns exactly what the operator typed, and the Settings rules list renders no calendar-sourced row | unit + integration | `server/.venv/bin/python3 server/test_calendar_rules.py`, `companion/test_config_page.py` | ✅ extend | ⬜ pending |
| TBD | registry | 1 | D-03 | T-16-DOS | The rolling window is rewritten whole: a fetch returning A+B followed by one returning only B leaves B alone on disk. Past flights expire by replacement, never by a cleanup pass. A hostile feed cannot grow the registry without bound (hard entry cap) | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ❌ W0 | ⬜ pending |
| TBD | poll-loop | 3 | D-04 / Phase 15 D-13 | T-16-TAMPER | End to end: a calendar match reaches `effective_theme_id` at **both** flight-displaying `build_canvas()` call sites, and Phase 15's both-branches invariant still holds — the same flight redrawn on a battery-icon repaint keeps the same theme | integration | `server/.venv/bin/python3 server/test_poll_loop.py` | ✅ extend | ⬜ pending |
| TBD | all plans | — | Phase 15 D-07 | — | Must-NOT-change: `server/plane/render.py` untouched, no new dependency in `server/requirements.txt`. Nothing new reaches the glass | unit | `server/.venv/bin/python3 server/test_render.py` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] **A redacted `.ics` fixture.** The real export is a named person's work schedule and is deliberately **not committed**. The fixture must preserve every structural property the parser is asserted against — folded continuation lines, the `STATUS:CANCELLED` + 1899-date junk pair, the `FLT`/`OFFD`/`CAHC`/`CPBL` category mix, an escaped `DESCRIPTION` containing `\n`, and bare-UTC `DTSTART`/`DTEND` — while carrying no real schedule, no real crew codes and no real UIDs.
- [ ] `server/test_calendar_rules.py` — new harness covering the parser, the fetch-hardening gate, the throttle, the registry contract and the pure match function. Mirror `server/test_colour_rules.py`'s structure and its `EXPECTED_CHECK_COUNT` ledger discipline.
- [ ] `scripts/run-all-tests.sh` — register the new harness in `HARNESSES`. An unregistered harness runs in no suite and is invisible to the coverage gate.
- [ ] No shared fixtures beyond the `.ics` file; `tempfile.TemporaryDirectory()` per test, matching every existing harness.
- [ ] Framework install: none.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| The Settings calendar group reads correctly with a real env var set and unset | UI-SPEC | The automated tests assert the emitted markup; a person should confirm the configured/not-configured copy reads honestly and that nothing hints the frame is watching or tracking | Load Settings with `SKYPANE_CALENDAR_ICS_URL` unset, then set. Confirm the URL appears nowhere, that the copy promises only "colours a flight that happens to be on screen", and that the theme picker behaves like the rules one |
| A real end-to-end match | D-04 | Cannot be forced: it needs the frame to be displaying a flight the calendar lists, which measured finding 3 says is rare | Opportunistic. Not a phase gate — do not block close-out on it |

**No on-glass verification is expected.** A calendar match resolves to an already-registered theme id, so nothing new reaches the panel — Phase 15's D-07 reasoning applies unchanged. Confirm at plan time once the record shape is settled.

---

## Validation Sign-Off

- [ ] All tasks have an `<automated>` verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0 covers all MISSING references (the fixture AND the harness)
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
