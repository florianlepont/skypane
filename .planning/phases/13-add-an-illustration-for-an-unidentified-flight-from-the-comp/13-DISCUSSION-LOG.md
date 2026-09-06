# Phase 13: Add an illustration for an unidentified flight from the companion web interface - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-05
**Phase:** 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
**Areas discussed:** What the upload resolves, Where the entry lives, Placement of the fifth fallback tier (dissolved), Affordance and the read-only promise

---

## Pre-discussion findings

Two claims in SEED-005 did not survive verification and were put to the developer before any area was selected, because both change the shape of the decision:

1. The seed's option (a) names `_AIRLINE_NAME_CORRECTIONS` (`enrich.py:272`). That table is keyed `(prefix, existing_name)` and can never fire for a prefix with no name. The real table is `_ICAO_AIRLINE_PREFIXES` (`enrich.py:461`), under a drift guard coupling it to `illustrations.target_airline_names()`.
2. The seed's Gap 1 (the membership gate) has a clean answer it did not see: the unresolved-prefix registry is already server-side validated state, written by `note_unresolved_prefix()` from genuinely detected traffic.

---

## What the upload resolves

| Option | Description | Selected |
|--------|-------------|----------|
| Image + name, runtime registry | One new concept: a "manual resolution" keyed on the prefix carrying name AND image, in `state_dir`, consulted by `airline_from_callsign()` after the static table. Fixes the caption too. Static tables and their drift guard untouched. | ✓ |
| Image only | A pixel registry keyed on the prefix, nothing else. Touches neither `enrich.py` nor the static tables — but the flight stays captioned as unidentified. | |
| Image + name, in the code | The UI prepares the entry, but it lives in the git-tracked tables. Faithful to the current design — but nothing reaches the frame before a commit and a redeploy. | |

**User's choice:** Image + name, runtime registry.

| Option | Description | Selected |
|--------|-------------|----------|
| Fifth source `manual` | Health distinguishes what the static table resolved from what the operator resolved by hand. Costs one more `_SOURCE_ROWS` category and history/test updates. | ✓ |
| Folded into `airline_only` | No schema or history change — but CFG-08's gloss ("from the static prefix table") becomes false and must be rewritten. | |
| You decide | Settled at plan time against the real migration cost. | |

**User's choice:** Fifth source `manual`.

| Option | Description | Selected |
|--------|-------------|----------|
| Name first, image if needed | The operator names the airline; the server checks whether art already exists under that name and asks for a file only if not. | ✓ |
| Always both together | One gesture, one form, one code path — but uploads an image the fallback ladder would have supplied for free. | |
| Name only, image later | Much smaller — but does not deliver what the phase promises for a carrier with no art. | |

**User's choice:** Name first, image if needed.
**Notes:** This option only became visible once D-01 was chosen — a runtime name means the existing ladder can find existing art with no upload at all.

| Option | Description | Selected |
|--------|-------------|----------|
| Airline default (Tier 2) | One image keyed on the name alone, serving every aircraft type — the existing Tier 2 semantics, whose comment records that brand identity beats type precision on a glanceable frame. | ✓ |
| Operator picks the shape | A bucket selector reaching Tier 1. More precise, but requires knowing the observed type and multiplies uploads per carrier. | |
| You decide | Settled at plan time against the existing form pattern. | |

**User's choice:** Airline default (Tier 2).

---

## Where the entry lives

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated file in `state_dir` | A new JSON beside `device_config.json`, same contract exactly: tmp + `os.replace`, never-raising `normalise_*`, companion writes / server reads. Survives redeploy. | ✓ |
| Inside `device_config.json` | Zero new files, all-or-nothing rejection for free — but mixes an unbounded dictionary into seven bounded scalars. | |
| Inside `poll_state.json` | Beside the gap data it relates to — but that file is owned and rewritten wholesale by `poll_loop.py`; the companion writing there would be a cross-process race. | |

**User's choice:** Dedicated file in `state_dir`.
**Notes:** Verified before offering the options that `save_poll_state()` has no caller in `companion/` outside tests.

| Option | Description | Selected |
|--------|-------------|----------|
| Manual wins | What the operator set by hand holds, and the art never disappears on its own — but an upstream correction can never reach that prefix. | |
| Static wins, entry flagged | The curated, drift-guarded source is authoritative, but the UI marks the manual entry superseded so the operator sees why their image went away and can re-place it. | ✓ |
| Static wins, silently | Simplest — but the art vanishes from the frame with nothing to explain it. | |

**User's choice:** Static wins, entry flagged.
**Notes:** adsbdb needs no rule — `resolve_route()` calls `lookup_route()` first, so it wins by construction.

| Option | Description | Selected |
|--------|-------------|----------|
| List + delete | The minimum that makes the superseded flag mean something: see manual entries with their state, delete one. No in-place edit — correcting means delete then re-add. | ✓ |
| List only | Smallest — but repair falls back to hand-editing JSON, i.e. back to the runbook this phase replaces. | |
| Full editing | Rename, replace image, delete in place — a complete CRUD over a brand-new namespace, well beyond "add an illustration". | |

**User's choice:** List + delete.

| Option | Description | Selected |
|--------|-------------|----------|
| Entry only, image stays | Never delete a file from a path that does not own it: the override is keyed on the name, shareable, and the Airlines flow may have written it. Orphaned PNGs accepted. | ✓ |
| Also the image, if unreferenced | Tidier, no orphans — but introduces reference counting and an irreversible deletion over a one-phase-old namespace. | |
| You decide | Settled at plan time once the registry shape is known. | |

**User's choice:** Entry only, image stays.

---

## Placement of the fifth fallback tier

**Dissolved mid-discussion — no options were put to the developer.**

Verification of `resolved_illustration_path()` (`illustrations.py:668`) showed it consults the override before the vendored file at *every* tier and does not require the key to be a known target. Once the prefix is translated into a name, the existing Tier 2 finds the uploaded override on its own. `select_illustration()` needs no change and no fifth tier. The only remaining lock is `_ILLUSTRATION_FILENAMES` in `companion/app.py`, frozen at import from `target_filenames()`.

The developer was shown this and chose to move on rather than discuss a tier that no longer needed to exist.

---

## Affordance and the read-only promise

| Option | Description | Selected |
|--------|-------------|----------|
| On Health, promise rewritten | The form sits on the registry, row by row, where the gap and the flight's context already are — but reopens D-11/D-12 head-on and gives Health its first form/button. | |
| On Airlines, link from Health | Health stays read-only; its sentence is re-worded ("resolved from Airlines") rather than broken, and each row deep-links to the form. One code path for the action. | ✓ |
| On Airlines only | No change to Health at all — but the operator must hand-copy a prefix read on another page, the round trip the seed exists to remove. | |

**User's choice:** On Airlines, link from Health.

| Option | Description | Selected |
|--------|-------------|----------|
| Registry context, re-read server-side | Prefix, first/last seen, count, example callsign — all re-read from the registry using the validated prefix, never from the URL. No new data source. | ✓ |
| Context + link to filtered History | The same block plus a deep link to History for the real flights. Richest — but depends on History's filter and adds a round trip. | |
| Prefix alone | Smallest — but the operator names the carrier blind. | |

**User's choice:** Registry context, re-read server-side.

| Option | Description | Selected |
|--------|-------------|----------|
| Free text + native suggestions | A `<datalist>` offers the 27 airlines that already have art; choosing one guarantees attachment, typing something else stays possible. Native, no JavaScript. | ✓ |
| Free text alone | Simplest — but silently misses existing art on any name variant, which is exactly what "name first, image if needed" was meant to exploit. | |
| Two explicit paths | Dropdown for known carriers vs free field for new ones. Clearest — but two forms and two code paths on a page that has one. | |

**User's choice:** Free text + native suggestions.

| Option | Description | Selected |
|--------|-------------|----------|
| Poll loop cleans up next cycle | The server owns `poll_state.json` and already rewrites it; it drops the entry once covered. Gap disappears at the next wake — no cross-process write. | ✓ |
| Health filters at render time | Immediate, no server change — but stored and displayed data diverge and `coverage_status()` must be patched separately to stop misreporting. | |
| Both | Best experience — two mechanisms to keep consistent for a discrepancy lasting at most one wake. | |

**User's choice:** Poll loop cleans up next cycle.

---

## Claude's Discretion

- All copy: the re-worded `_READ_ONLY_NOTE`, form labels and hints, success/rejection flashes, the superseded marker. Constrained by the Phase 12 precedent — the confirmation must not imply the frame changes instantly.
- The registry's on-disk shape, its entry cap, and how `airline_from_callsign()` is threaded to consult it without breaking its purity/never-raises contract.
- Whether the new POST route reuses `_handle_illustration_replace()` or sits alongside it.

## Deferred Ideas

- **Retroactivity over History** — raised during the closing gate and deliberately left open rather than decided quietly. Rewriting rows already classified `miss` would compromise a resolution-rate measurement the project has cited since Phase 2.
- **Garbage collection for orphaned overrides** — the accepted cost of the delete decision.
- **In-place editing of manual resolutions** — rejected as full CRUD beyond the phase boundary.
- **A shape-specific (Tier 1) upload** — rejected; interesting only if a carrier's fleet mix made one silhouette visibly wrong on glass.
