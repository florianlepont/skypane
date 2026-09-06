---
status: complete
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
source: [13-01-SUMMARY.md, 13-02-SUMMARY.md, 13-03-SUMMARY.md, 13-04-SUMMARY.md, 13-05-SUMMARY.md, 13-06-SUMMARY.md]
started: 2026-09-06T05:52:00Z
updated: 2026-09-06T06:05:00Z
---

## Current Test

[testing complete]

## How this session was run

Nothing is deployed, so the companion was run locally against a **throwaway state dir**
(`scratchpad/uat13-state`) seeded with two synthetic unresolved prefixes — `XQZ` (7 sightings,
example callsign `XQZ411`) and `KLM` (2 sightings, `KLM77A`) — on port 8699, with a
single-use password generated for this instance. No production data, no deployed instance,
no developer credential was involved.

The browser pane could not dispatch interactions to the local page (three attempts, no
`POST /login` ever reached the server), so the flow was exercised at the HTTP level with
`curl` against the real running service, plus direct calls into the real modules for the
enrichment/illustration chain. That is stronger evidence than a screenshot for everything
except the `<datalist>` popup itself, which remains the one genuinely browser-owned behaviour
(see gap G-02).

## Tests

### 1. Health surfaces the gap and links out (D-10)
expected: reworded read-only note; a `Resolve` deep link per registry row; no state-changing control on Health
result: pass
note: note renders as "read-only here — each row's Resolve link opens the Airlines page to name that prefix's airline (and add artwork, if it needs one)"; `resolve=XQZ` and `resolve=KLM` links both present

### 2. Deep link renders the flight's context, re-read server-side (D-12)
expected: prefix, first seen, last seen, example callsign shown from the registry, not from the query string
result: pass
note: `XQZ411` and both 2026-09-01 / 2026-09-05 dates render on `/airlines?resolve=XQZ`

### 3. Native datalist offers exactly the airlines that already have artwork (D-13)
expected: a real `<datalist>`, bound by `list=`, carrying `target_airline_names()`
result: pass
note: `<datalist id="known-airlines">` with **27** options, input bound via `list="known-airlines"`; first entries Air France, Iberia Airlines, TAP Portugal, Air Algerie, Air Corsica

### 4. Reserved-key name is rejected (D-13 / T-13-03)
expected: a name slugging into the `generic-*` namespace is refused and nothing is persisted
result: pass
note: "Generic Fallback" → `303 … flash=manual_name_reserved`; no registry file created

### 5. Traversal-shaped name is rejected (T-13-02)
expected: `../../etc/passwd` refused before slugging, nothing persisted
result: pass
note: refused; nothing written. **The rejection is correct but the message is wrong — see gap G-01.**

### 6. A prefix absent from the gap registry is refused (T-13-08)
expected: a prefix the server has never observed cannot be resolved
result: pass
note: `prefix=ZZZ` → `303 … flash=manual_prefix_stale`; no registry file created

### 7. Naming an airline that already has artwork skips the upload (D-03)
expected: Step A alone finishes the job; no Step B offered
result: pass
note: `XQZ` → "Air France" redirects to `/airlines?flash=manual_resolved` **without** `?resolve=`; the page carries only the pre-existing gallery lightbox form

### 8. Naming an airline with no artwork asks for the upload (D-03)
expected: Step B offered, and only then
result: pass
note: `KLM` → "Skytest Air" redirects **keeping** `?resolve=KLM`; the page gains a second multipart form

### 9. Upload membership gate holds (T-13-01 / reopened T-v26-02-01)
expected: a never-registered key 404s and leaves the override directory empty
result: pass
note: `bogus-airline.png` → 404; `..%2f..%2fetc%2fpasswd.png` → 404; the override directory **was never even created**

### 10. Upload is held to the vendored-illustration standard
expected: a non-conforming image is rejected, with the reason logged server-side only
result: pass
note: a fully-opaque PNG → `flash=illustration_rejected`; the real reason ("alpha channel is fully opaque everywhere — transparency requirement not met") went to the service log, never to the response (T-v26-02-08)

### 11. A conforming upload lands and closes Step B
expected: the override is written under the minted key and the page stops asking
result: pass
note: transparent 1400×700 PNG accepted → `flash=illustration_replaced`, `skytest-air.png` written; the KLM page drops back to one multipart form

### 12. The whole loop reaches the frame — the phase goal
expected: a manually resolved callsign produces the right airline, the `manual` source, and real artwork
result: pass
note: verified by direct calls into the real modules —

| Callsign | source | airline | illustration |
|---|---|---|---|
| `KLM77A` | `manual` | Skytest Air | `skytest-air.png` (the upload) |
| `XQZ411` | `manual` | Air France | `air-france.png` (**vendored — named, therefore free**) |
| `AFR1234` | `airline_only` | Air France | `air-france.png` (static table, unchanged) |
| `QQQ999` | `miss` | — | `generic-fallback.png` (unchanged) |

### 13. The poll loop stops reporting a resolved gap (D-14)
expected: `clear_resolved_unresolved_prefix()` removes both now-covered prefixes
result: pass
note: `['KLM','XQZ']` → `[]`

### 14. The entry stays reachable after the gap is cleaned (CR-02 regression)
expected: with the gap gone, the management list still lists the entry, and offers "Add artwork" when artwork is missing
result: pass
note: both entries still listed with Delete; removing `skytest-air.png` makes **"Add artwork"** appear (twice — desktop table and mobile cards). This is exactly the dead end the code review caught; the fix holds.

### 15. Deleting an entry never deletes the image (D-08)
expected: the registry entry goes, the shared override file stays
result: pass
note: `POST /airlines/manual-resolutions/KLM/delete` → registry `['KLM','XQZ']` → `['XQZ']`, `skytest-air.png` still on disk

## Summary

total: 15
passed: 15
issues: 0
pending: 0
skipped: 0

## Gaps

### G-01 — a rejected name is reported as an empty one (cosmetic, not security)

`illustration_key_for_name()` returns `None` for three different reasons, and the caller
collapses all of them onto `FLASH_KEY_MANUAL_NAME_EMPTY` — *"Enter an airline name before
saving."*

| Input | slug | key | flash shown |
|---|---|---|---|
| `../../etc/passwd` | `etc-passwd` | `None` (hostile raw name) | name_empty |
| `a/b` | `a-b` | `None` (hostile raw name) | name_empty |
| `!!!` | `None` | `None` (genuinely unusable) | name_empty |
| `   ` | `None` | `None` (genuinely unusable) | name_empty |

For the first two the operator *did* type a name, so the message is simply false. The rejection
itself is correct and the security property is untouched — only the explanation is wrong.

It matters because `13-CONTEXT.md` names "the operator is never silently misled" as this phase's
governing constraint, and because the same collapse would hide a future rejection cause. The fix
is a distinct flash key for a name that was supplied but unusable, leaving `name_empty` for a
genuinely empty field.

**Severity:** low. Not a blocker; no locked decision is violated.

### G-02 — the `<datalist>` popup itself is still unverified in a browser

Test 3 proves the markup is correct and that 27 options are bound. What no HTTP check can prove
is the browser-owned behaviour: that the suggestion list actually drops down while typing, is
dismissible, and does not obstruct the form on a narrow viewport. `VALIDATION.md`'s single
manual-only row remains open. The browser pane could not drive the local instance this session;
this is worth one real look once the branch is deployed.

**Severity:** low. The element is native HTML with no scripting; the risk is presentational.
