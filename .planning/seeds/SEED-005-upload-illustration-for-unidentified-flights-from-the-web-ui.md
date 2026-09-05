---
id: SEED-005
status: dormant
planted: 2026-09-05
planted_during: "Post-Phase-11 (roadmap complete except DEVICE-05); quick task 260905-bba"
trigger_when: "When the companion's coverage-gap surfaces (Health's unresolved-prefix registry, the Airlines gallery) are next opened for work — this seed's whole point is to make those two pages actionable rather than informational. Also revisit if the developer finds themselves repeatedly resolving coverage gaps by hand through the runbook, since that manual loop is exactly what this replaces. No hardware or battery-verdict dependency."
scope: medium
---

# SEED-005: Add an illustration for a not-yet-identified flight directly from the web interface

## Why This Matters

The frame currently degrades gracefully when it meets a flight it cannot dress: `select_illustration()`'s four-tier fallback drops to a neutral shape, then to the universal fallback. That is correct behaviour, but it is also a dead end — the operator can *see* the gap (Health lists the unresolved callsign prefix; the Airlines gallery shows what art exists) and can do nothing about it from the interface. Closing the gap means leaving the web UI entirely and following a manual runbook.

The idea: from the pages that already surface the gap — Health and Airlines — let the operator add the missing image for that specific flight, with enough of the flight's own information visible to know what they are looking at while they do it.

What makes this attractive is that the hard, security-sensitive half already shipped. Quick task `260902-v26` built a hardened upload path, and `260903-df3` gave it a real control surface. The missing piece is not "how do we accept a file safely" — that is solved — but "how does a flight nobody has identified yet acquire a key to upload against".

## When to Surface

**Trigger:** when Health's unresolved-prefix registry or the Airlines gallery is next worked on. Both pages are the natural host, and both would need to change for this to be worth doing.

This seed will also surface during `/gsd-new-milestone` when the milestone scope matches.

## Scope Estimate

**Medium.** The upload machinery is done; the work is a namespace bridge plus reopening one deliberate decision.

**What already exists (verified 2026-09-05, do not rebuild):**

- A complete hardened upload path — `_handle_illustration_replace()` (`companion/app.py:1082`), bounded by `MAX_ILLUSTRATION_UPLOAD_BYTES` (4 MB, `app.py:83`), with a strict single-part stdlib multipart parse (`parse_single_uploaded_file()`, `app.py:464`), a write-to-temp-then-`validate_illustration_file()` gate holding uploads to the same standard as every vendored illustration, and a destination filename taken **only** from the validated URL key, never from the request.
- A real UI for it — the Airlines lightbox replace form (`_lightbox_replace_form_html()`, `airlines_page.py:270`), a native multipart POST with no JS dependency.
- The gap data itself — Health's unresolved-prefix registry (`unresolved_rows()`, `health_page.py:1843`) with its filter bar and CFG-08 resolution statistics.

**Gap 1 — the upload is membership-gated, by design.** `_handle_illustration_replace()` performs a membership test on `key` **first**, before a path is constructed or a single byte of the body is read (validate-then-join, threat `T-v26-02-01`). That means it can only ever *replace* art for a key the registry already knows. A flight nobody has identified has no such key, so today the endpoint structurally cannot serve this use case. **This is the crux: lifting the gate means a new key would originate in user input, which is precisely what the current design forbids.** Any design here has to re-establish that safety a different way — most likely by having the server mint the key from already-validated server-side state (the detected flight's own resolved fields) and never accepting a key from the form at all.

**Gap 2 — the unresolved list is read-only on purpose.** `health_page.py:352`'s `_READ_ONLY_NOTE` says so verbatim to the operator: *"This list is read-only by design — resolving a prefix is a manual step done elsewhere, following the existing coverage-gap runbook."* That is decision D-11/D-12 from `06.6.4.1-04`. This seed **reopens that decision** rather than working around it — worth naming explicitly at planning time, and worth deciding whether the note's promise to the operator changes or the affordance lands on Airlines only.

**The real design question — two namespaces that do not line up.** The unresolved registry keys on **callsign prefix**. Illustrations key on **resolved airline name + aircraft-type shape bucket** (`select_illustration()` at `illustrations.py:683`, `classify_aircraft_type()` at `:556`). A prefix nobody has resolved has no airline name, so there is no illustration key to mint from it. Which forces a choice:

- **(a) Adding an image also resolves the airline** — the operator names the airline while uploading, and the entry joins `enrich.py`'s existing `_AIRLINE_NAME_CORRECTIONS` table (`enrich.py:272`, applied via `apply_airline_name_correction()` at `:313`). This is the more useful outcome, since a resolved name fixes the *caption* too, not just the picture — but it turns the feature into an airline-resolution editor, which is materially bigger and touches the render path's data, not just its assets.
- **(b) Image only, keyed on the prefix itself** — a narrower fifth fallback tier consulted before the neutral shape. Much smaller, but leaves the flight still captioned as unidentified, which may make the upload feel half-done to the operator.

Settling (a) vs (b) is the first thing to do; everything else follows from it.

**Also to decide:** what "see the information if needed" means concretely — the unresolved registry already records first-seen/last-seen per prefix, and History holds the real flight rows. Whether the upload affordance shows a recent-flights excerpt inline, or simply deep-links into History's existing filter, is a UI question worth sketching before planning.

## Breadcrumbs

- `companion/app.py:1082` — `_handle_illustration_replace()`, the membership gate that Gap 1 is about; read its docstring's numbered threat list before touching it
- `companion/app.py:464` — `parse_single_uploaded_file()`, the strict multipart parse to reuse as-is
- `companion/pages/airlines_page.py:270` — `_lightbox_replace_form_html()`, the existing upload control to extend
- `companion/pages/health_page.py:1843` — `unresolved_rows()`, the coverage-gap data
- `companion/pages/health_page.py:352` — `_READ_ONLY_NOTE`, the decision this seed reopens (06.6.4.1-04, D-11/D-12)
- `server/plane/illustrations.py:683` / `:556` — `select_illustration()`'s four-tier fallback and `classify_aircraft_type()`, the key namespace a new entry must fit into
- `server/plane/enrich.py:272` / `:313` — `_AIRLINE_NAME_CORRECTIONS` and `apply_airline_name_correction()`, the existing resolution-correction mechanism option (a) would extend
- `.planning/quick/260902-v26-*` and `.planning/quick/260903-df3-*` — the two quick tasks that built and then restyled the upload path

## Notes

Captured 2026-09-05 from the user's own description: being able to add, easily and from the web interface, the photo for flights that are not yet identified and have no image associated — for example from the Airlines and Health panels. No design conversation behind it yet. The scope breakdown above was derived by reading the shipped code, not from a discussed design; the (a)/(b) fork in particular is this file's own framing of the choice and has not been put to the user.
