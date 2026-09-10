---
status: complete
phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh
source: [17-VALIDATION.md, 17-REVIEW.md, 17-SECURITY.md]
started: 2026-09-10T00:00:00Z
updated: 2026-09-10T00:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Connect a real calendar from the Settings page and judge whether the group promises only what the frame can deliver
expected: The operator pastes their own calendar feed URL into Settings, saves, and the frame starts using it — no SSH, no service restart, no file edit. The Calendar group's copy claims nothing the frame cannot do, and the URL is never rendered back in any state.
result: pass, after two blockers found and fixed
source: human
verified: |
  2026-09-10, by the developer, against a local instance of the phase's code
  (port 8717, isolated state dir) using their own real Apple Calendar
  subscription — the first time this feature has ever run against a live feed
  rather than a downloaded .ics fixture.

  The first attempt failed. The two defects it exposed are recorded as UAT-01
  and UAT-02 in 17-REVIEW.md; both are described under Gaps below because
  neither was findable by any automated means available before this run.
  After both fixes, the developer confirmed: "ça fonctionne".

  Mechanically confirmed alongside the human judgement, so the human call was
  only about the writing: an authenticated HTTP round trip with a
  distinctive-token URL leaks the token, host, path and query name in no
  header and no body, in all four Calendar states; the field carries no
  `value=` attribute; and the disconnect checkbox renders unchecked.
why_human: |
  The automated suite pins the emitted markup and the locked copy constants.
  What it cannot do is paste a real subscription URL from a real calendar
  provider and see what happens — and that is precisely where both blockers
  lived. Neither was a coding error the tests were too weak to catch; both
  were assumptions about the shape of real-world input that no fixture
  encoded.

### 2. Security pass over the write-path secret, the SSRF gate and the cross-process lock
expected: `/gsd-secure-phase 17` verifies the ten-threat register against the shipped code.
result: pass
source: automated
evidence: |
  10/10 threats closed, `threats_open: 0` at the `high` blocking threshold.
  See 17-SECURITY.md. The auditor verified by execution rather than by
  reading: it spied on `os.open()` mid-write to prove the mode is 0600 at
  creation under umask 022 and 027 and over a pre-existing 0644 destination;
  it proved a drifted-mode file is never opened at all, not merely refused;
  it swept 20+ adversarial URL shapes through the new `webcal://`
  normalisation plus the SSRF gate together, finding no bypass and no
  `webcal → http` downgrade; and it independently reproduced the CR-01
  cross-process race and confirmed the `fcntl.flock` fix closes it.

  One sub-blocking flag, UF-17-01: the registry lock is a bounded poll-wait
  (15s ceiling) rather than a single non-blocking acquire. Verified by the
  orchestrator to be `LOCK_NB` in a bounded retry loop that raises
  `TimeoutError` rather than ever writing unlocked, and releases in a
  `finally`. It cannot wedge the poll loop or write unprotected; the only
  consequence is that a Settings save can wait up to 15s under contention.
  Recorded, not blocking.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

Both gaps below were **closed during UAT**, but they are recorded here rather
than only in the review report, because what they say about this project's
testing is more important than the fixes themselves.

**UAT-01 — the feature rejected the only URL format its intended source
emits.** Apple Calendar publishes subscription links as `webcal://`; the
Phase 16 SSRF gate accepted `https://` only. Fixed by normalising `webcal` to
`https` upstream of the gate, leaving the gate itself unweakened.

**UAT-02 — the feature was structurally incapable of ever colouring a
flight.** `parse_ics_events()` capped at `CALENDAR_MAX_ENTRIES` (200) in
**feed order** and applied the retention window afterwards. Real feeds serve
history first: measured on the developer's own calendar, all 1074 flight
events parsed, and every one of the 8 future flights sat at feed position
1066-1073 — beyond a cap that keeps 0-199. Not "sometimes misses": never. The
window is now applied before the cap; all 8 future flights survive.

**Why neither was findable earlier.** Phase 16 passed research, planning, a
plan-check, execution with mutation-verified tests, a security audit and a
code review — and shipped both defects. Every one of those steps worked from
a downloaded `.ics` fixture holding a handful of events. The fixture was
redacted from the developer's own calendar, which made it feel like real
data; it was not, in the two dimensions that mattered — it had no
subscription URL, and it was small enough that the cap never engaged.

The lesson for future phases that consume an external feed: a fixture derived
from real data still encodes the assumptions of whoever exported it. At least
one end-to-end run against the live source, by its actual owner, belongs in
the plan — not in UAT, where it costs two emergency fixes at the close.
