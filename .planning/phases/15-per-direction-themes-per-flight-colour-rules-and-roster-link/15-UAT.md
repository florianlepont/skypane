---
status: complete
phase: 15-per-direction-themes-per-flight-colour-rules-and-roster-link
source: [15-VERIFICATION.md]
started: 2026-09-06T16:35:00Z
updated: 2026-09-06T17:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Arrivals theme grid: presence, CSS-only reveal, and the clearable contract
expected: The second grid ships in the HTML rather than being injected by script; ticking the checkbox reveals it and unticking hides it, with no JavaScript involved; a chosen arrivals theme saves; and unticking genuinely clears a previously-saved override rather than carrying it forward.
result: pass
source: automated
evidence: |
  Verified against a real companion server started on port 8655 with an isolated
  state directory, driven through a real browser and raw HTTP.
  - Both grids are in the served markup: 18 radios named `theme` and 18 named
    `theme_arriving`. Nothing is script-injected.
  - Reveal is CSS-only. The stylesheet carries `:has()` rules behind `@supports`
    guards; the page's single `addEventListener` is an unrelated submit-button
    disabler on another form. In the browser, ticking the checkbox made
    "Arrivals theme" and its 18 chips appear in the visible text, and unticking
    removed them again.
  - Clearable contract confirmed end to end through the real form: saving with
    the checkbox on wrote `theme_arriving='blue'` to `device_config.json`;
    saving again with the checkbox absent cleared it to `None` — even though the
    request body still carried `theme_arriving=blue`. Absence of the checkbox is
    what clears, which is exactly the sentinel's purpose.

### 2. Per-flight rules editor: add, replace, delete, rejection, and dirty-bar isolation
expected: A rule can be added, an existing key re-added reporting "replaced" rather than "added", and a rule deleted; malformed input is refused; and none of these actions can be captured by the main form's unsaved-changes bar.
result: pass
source: automated
evidence: |
  All flows exercised as raw HTTP POSTs, which is the no-JavaScript path.
  - Add `callsign AFR1234 -> black` returned `flash=rule_added`.
  - Re-adding the same key with a different theme returned
    `flash=rule_replaced&rule=AFR1234`, and the registry on disk showed the
    theme changed to `red` with the entry still unique.
  - Delete returned `flash=rule_deleted` and the entry left the registry.
  - Rejections: a path-traversal hex value and an over-length prefix both
    returned `rule_key_invalid`; a theme id outside the registry returned
    `rule_save_failed`. A delete on an unknown kind and on a malformed value
    both returned 404 rather than looking up a request-supplied string.
  - Dirty-bar isolation is structural: the rules section renders after
    `</form>` of `id="settings-form"`, and that form contains zero nested
    `<form>` elements. A rule action cannot reach the dirty bar.
  - The rendered list showed the saved rule correctly: kind "ICAO24 hex",
    key 3944F2, theme Green, with a human-readable relative timestamp.

### 3. Visual and keyboard sign-off with JavaScript genuinely disabled
expected: Loaded in your own browser with JavaScript actually disabled, the Settings page reads well: the arrivals reveal and the rules section are comfortable at your window size, tab order through both grids and the rules form is sensible, and the focus ring is clearly visible throughout.
result: pass
source: human
verified: 2026-09-06 by the developer, in their own Chrome against a local instance of the phase's code (port 8655, isolated state dir, pre-seeded with one hex rule so the list rendered populated). Confirmed with no qualifications.
why_human: |
  Tests 1 and 2 ran with JavaScript enabled, and prove the mechanism is CSS-only
  rather than proving the page under a browser with scripting switched off.
  Beyond that, this project has a standing lesson that computed-style checks
  alone once missed a real mobile navigation defect, so density, focus
  visibility and tab-order feel are signed off by a person here, not asserted.

### 4. Security pass over the two new rules routes and the rules registry
expected: `/gsd-secure-phase 15` confirms the STRIDE threat registers recorded across the five plans are honestly mitigated in the shipped code — the two new POST routes, the `colour_rules.json` registry, the per-kind allowlists applied at write and on read, the theme-id membership test, and the entry cap.
result: pass
source: automated
evidence: 15/15 threats closed, threats_open 0 at the `high` blocking threshold. See 15-SECURITY.md. The auditor went deeper than ASVS L1 on all five high-severity rows and on both non-mitigate dispositions: it confirmed the CSRF `transfer` genuinely covers both new routes by emitting the cookie header at runtime rather than reading a literal, and re-verified both `accept` rationales against shipped code. It also judged the code review's two concurrency warnings and found neither reopens a threat, recording one as an unregistered flag rather than silently absorbing it.

## Summary

total: 4
passed: 4
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps
