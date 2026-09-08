---
status: complete
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
source: [16-VERIFICATION.md, 16-SECURITY.md]
started: 2026-09-08T00:00:00Z
updated: 2026-09-08T09:00:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Read the Calendar settings group and judge whether it promises only what the frame can deliver
expected: The Calendar group's heading, caption, status line and theme-picker hint together describe a feature that colours a flight when it happens to be displayed, and claim nothing more. The calendar URL is never rendered. The group reads comfortably at the bottom of an already-long Settings page.
result: pass
source: human
verified: |
  2026-09-08, by the developer, reading the actually-rendered Calendar group
  in their own Chrome against a local instance of the phase's code (port 8656,
  isolated state dir, started with a fake calendar URL so the connected state
  was the one on screen). Approved with no changes requested.

  Mechanically confirmed alongside it, so the human judgement was only about
  the writing: the configured URL appears nowhere in the rendered HTML (probed
  for the token, the domain, and even the bare `.ics` fragment); the only
  surveillance verb present is "track", negated in its own sentence, with
  watch/follow/monitor/notify/alert all absent; no upcoming-flight count or
  preview is rendered; and the group sits seventh, between Display and the
  per-flight rules.
why_human: |
  The automated tests assert the emitted markup and pin the locked copy
  constants, and a word-boundary check rejects affirmative tracking language.
  What they cannot judge is whether the writing, read as a whole by a person
  who knows what the frame actually does, sounds honest. This phase's entire
  copy discipline exists because an overpromising caption would make a working
  feature look broken, and that is a judgement call.

### 2. Security pass over the new outbound fetch, the secret and the registry
expected: `/gsd-secure-phase 16` verifies the twelve-threat register against the shipped code.
result: pass
source: automated
evidence: |
  11/12 threats closed, `threats_open: 0` at the `high` blocking threshold.
  See 16-SECURITY.md. The auditor went beyond reading the plans: it ran a
  15-URL adversarial sweep against the SSRF gate (decimal-int, hex-octet,
  trailing-dot, userinfo, IPv4-mapped IPv6, cloud metadata address, ULA and
  link-local v6, file://, scheme-relative) and found no bypass; it proved the
  secret reaches neither state_dir nor any rendered page through a real
  authenticated HTTP round trip; and it confirmed the clock-dependency test
  genuinely discriminates by driving the shipped matcher at first-display time
  and again past the tolerance.

  One threat remains open below the blocking threshold, T-16-PRIV: the
  retention window is not re-applied on the fetch-failure path, so a stale
  entry survives on disk if the feed breaks. Privacy-at-rest only — a stale
  entry cannot match, and the entry cap still bounds growth. Filed as separate
  follow-up work rather than fixed here.

## Summary

total: 2
passed: 2
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
