# Phase 3: Visual Polish on Real Glass - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-26
**Phase:** 3-Visual Polish on Real Glass
**Areas discussed:** Departure-threshold validation method, frame mount status, long-caption legibility stress test, aircraft illustration scope (emerged mid-discussion, expanded the phase)

---

## Departure-threshold validation method (A-02-02-01)

| Option | Description | Selected |
|--------|-------------|----------|
| Wait and watch naturally | Keep the frame running, check journalctl whenever a real departure eventually happens | |
| Search Phase 1 sample data for a real departure track | Replay a real captured departure like 02-02 did with the real EJU84YF arrival fixture | (initially selected, then reversed) |
| Accept the current symmetry-derived assumption as-is | Don't chase it this phase, document as still-unvalidated | |

**User's choice:** Initially "Search Phase 1 sample data." Claude verified the sample data directly (`adsb-test/samples/*.jsonl`) and found 0 climbing readings ≥ +200 ft/min across 217 real vertical-rate readings (max observed: +48 ft/min) — no real departure track exists to replay. Re-asked with corrected options.

**Follow-up options after the data check:**

| Option | Description | Selected |
|--------|-------------|----------|
| Wait and watch naturally | No forcing | |
| Force a synthetic departure render for the visual check only | Inject synthetic vertical_rate ≥ +200 through the real render pipeline, same technique as the enrichment-fallback test | ✓ |
| Accept as-is | Don't chase further | |

**Notes:** This validates the visual DEPARTING render only, not the real +200 ft/min threshold value — that stays an open item until a genuine departure is observed in production.

---

## Frame mount status

| Option | Description | Selected |
|--------|-------------|----------|
| Already mounted on the wall in its final spot | Judgments can be made at the real final viewing distance now | |
| Still on a desk / temporary location | These criteria can only be judged provisionally until mounted | ✓ |

**User's choice:** Still on a desk.
**Notes:** Two ROADMAP success criteria (silhouette recognizability at wall-viewing distance, overall composition as ambient art) can only be judged provisionally this phase; a final wall-mounted check is a legitimate open item, not a blocker.

---

## Long-caption legibility stress test

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, force a long-name render | Inject a real flight with a genuinely long city/airline name via the production render code, same technique as before | ✓ |
| No, skip it | Trust that legibility holding for a normal-length name is representative | |

**User's choice:** Force it.

---

## Aircraft illustration scope (emerged mid-discussion)

This area was not part of the original 3 presented gray areas — the user raised it unprompted when asked "anything else?", describing a much more ambitious visual redesign vision than the original ROADMAP Phase 3 text covered: a personal photo background, and airline-livery illustration.

**Claude's initial concern (before user clarification):** flagged two tensions with the locked 02-UI-SPEC.md Revision 2 contract — (1) a photo background conflicts with the deliberate full-bleed solid-color "poster" design, chosen for the flat/no-dither hardware rendering rule; (2) per-airline livery art was explicitly rejected in Phase 2 due to real trademark/licensing risk (no CC0 livery art exists).

**User's response:** photo background can wait for v2. Licensing risk is moot because the user will generate the illustrations themselves (AI image generation), not source real licensed art.

### Sub-decision: single vs. per-airline illustration

| Option | Description | Selected |
|--------|-------------|----------|
| Single improved generic illustration | Replace the CC0 silhouette with one nicer generated asset, still unique across all flights | |
| Per-airline illustration | Different illustration per airline (via existing D-02 enrichment), generic fallback for uncovered/unknown | ✓ |

### Sub-decision: color/rendering treatment

First asked with a flat-monochrome-only framing; the user pushed back, noting they'd already displayed a personal photo well via SenseCraft — this contradicted the framing and prompted a re-explanation (dithering exists specifically to make photographic/rich content work within the panel's 6-color, no-native-gradient constraint; the "flat only" framing was describing Phase 2's chosen style, not a hardware limit).

**Follow-up: bring the photo background back into Phase 3 scope, now that it's confirmed technically viable?**

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, include in Phase 3 | | |
| No, keep in v2 as decided | | ✓ |

**Follow-up: aircraft illustration rendering treatment**

| Option | Description | Selected |
|--------|-------------|----------|
| Always flat monochrome (White) | Same treatment as today, just more detailed/recognizable art in one color | |
| Dithered/photo-like rendering | Same technique SenseCraft uses — richer, more detailed, approximated colors | ✓ |

### Sub-decision: fallback illustration for uncovered airlines / enrichment failure

| Option | Description | Selected |
|--------|-------------|----------|
| Current generic flat-White CC0 silhouette | Falls back to the existing asset unchanged | |
| Single generic dithered illustration, same style as the per-airline set | Visually consistent everywhere | ✓ |

### Sub-decision: who generates the illustrations

| Option | Description | Selected |
|--------|-------------|----------|
| User generates and hands off files | Claude vendors/processes them in the plan | |
| Claude generates during the phase | Included as a plan task if a generation capability is available | ✓ |

**Notes:** This is a real, deliberate expansion of Phase 3's scope beyond the original ROADMAP text — captured back into `.planning/ROADMAP.md`'s Phase 3 section (new success criterion 5, updated goal/note-on-scope) since the phase was still unplanned (Pending status, 0 plans) when this was decided, so widening it directly was safe and consistent, not a silent scope change on committed work.

---

## Claude's Discretion

- Exact airline coverage list for the generated illustration set
- Exact image-generation tool/approach and post-processing pipeline (posterize/quantize/dither parameters)
- Whether the generic dithered fallback is airline-neutral new art or a dithered re-render of the retired CC0 shape
- Panel RGB reference values — resolve only if load-bearing for the dithering work

## Deferred Ideas

- **Personal photo as the panel's background** — technically viable (proven via SenseCraft), but explicitly deferred to v2 by the user. Tracked as `REQUIREMENTS.md` v2 requirement **VIS-01**.
