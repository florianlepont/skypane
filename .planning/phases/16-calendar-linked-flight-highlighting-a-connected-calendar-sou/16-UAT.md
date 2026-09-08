---
status: testing
phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou
source: [16-VERIFICATION.md, 16-SECURITY.md]
started: 2026-09-08T00:00:00Z
updated: 2026-09-08T00:00:00Z
---

## Current Test

number: 1
name: Read the Calendar settings group and judge whether it promises only what the frame can deliver
expected: |
  Open the companion Settings page and read the new Calendar group. Two things
  to judge, neither of which a test can settle:

  1. **Does the copy overpromise?** Measured on your own production data: the
     frame shows one aircraft at a time and missed all three of the calendar
     owner's flights among 201 detections on her one recorded duty day. This
     feature colours a flight only when that flight happens to be the one on
     screen. The copy must not suggest the frame tracks, watches, follows or
     notifies, and must not imply you will know when someone is flying.
  2. **Does the group read well where it sits?** It is the last section inside
     the settings form, after Display. The page is long now.

  Also confirm the URL appears nowhere on the page — only a configured or
  not-configured state and a last-synced time.
awaiting: user response

## Tests

### 1. Read the Calendar settings group and judge whether it promises only what the frame can deliver
expected: The Calendar group's heading, caption, status line and theme-picker hint together describe a feature that colours a flight when it happens to be displayed, and claim nothing more. The calendar URL is never rendered. The group reads comfortably at the bottom of an already-long Settings page.
result: [pending]
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
passed: 1
issues: 0
pending: 1
skipped: 0
blocked: 0

## Gaps
