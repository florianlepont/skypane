# Phase 11: Web-configurable wake interval - Research

**Researched:** 2026-09-04
**Domain:** Internal codebase pattern-extension (no new external libraries) — Python stdlib config registry, a stdlib-only HTTP poll handler, and a hand-rolled companion web form
**Confidence:** HIGH

## Summary

This phase adds one new integer field, `wake_interval_s`, to the existing `server/device_config.py` registry, exposes it as a plain `<input type="number">` on the companion Settings page, and threads it into `stub-server/byos_server.py`'s `/device/v1/display` handler as the new *base* value `quiet_hours_sleep_s()` extends — replacing the current hardcoded `self.args.sleep` reference at that one call site. All five of 11-CONTEXT.md's specific research questions were confirmed directly against the live code (read below, not the pre-Phase-10 shape): D-01/D-03's delivery mechanism is a one-line change plus one new ~15-line best-effort read function; D-02's 60s/3600s bounds are sane and are the **first bounded-integer field** this registry has ever needed (every existing field is a string-membership check, a bool, or an HH:MM regex — there is no precedent to copy, only precedents to generalize from); a new `read_wake_interval_s()`-style function is needed in `byos_server.py`, structurally closer to `read_led_enabled()`'s single-value shape than `read_quiet_hours()`'s tuple shape; and zero firmware changes are required, confirmed again at `firmware/main/state_machine.c:51` and `firmware/main/app_main.c:172` — `sleep_s` is consumed as an opaque `uint32_t`, no different from Phase 10's own finding.

One thing 11-CONTEXT.md's Claude's Discretion section states as "the obvious, only sane choice" is **not actually straightforward** and needs an explicit planning decision (see Open Questions #1): pre-filling the Settings page with "the current effective interval, defaulting to the CLI `--sleep` value" is impossible for `companion/app.py` to compute directly, because the CLI `--sleep` value lives in a completely separate OS process's `argparse` namespace (`stub-server/byos_server.py`, launched by `deploy/skypane-byos.service` with `--sleep ${SKYPANE_SLEEP_S}`) that the companion process has no access to and does not read `skypane.env` today. This research recommends resolving that gap by having `load_device_config()`'s `wake_interval_s` key return `None` when unset (a deliberate, single-field exception to this module's otherwise-universal "always return a concrete value" contract) and having the companion page render an empty/placeholder input rather than guess a number — see Architecture Patterns, Pattern 3.

Also load-bearing and not explicit in 11-CONTEXT.md: because HTML form submissions are always strings, `handle_post()` must explicitly `int()`-convert the submitted `wake_interval_s` value before calling `save_device_config()` — unlike `quiet_hours_start`/`quiet_hours_end`, which pass straight through as strings unconverted. Getting this wrong (passing the raw string straight through, mirroring the quiet-hours pattern by habit) would make `save_device_config()`'s own `isinstance(value, int)` check reject every legitimate submission. See Common Pitfalls #1.

**Primary recommendation:** Add `wake_interval_s` to `device_config.py`'s registry as the one field whose "unset" state is `None` rather than a hardcoded default constant; thread that value through a new `read_wake_interval_s(state_dir, default)` function in `byos_server.py` that falls back to `self.args.sleep`; add a fourth-or-fifth `.theme-status` group to `config_page.py` with a plain `<input type="number" min="60" max="3600">`; and update every one of the 11 dict-equality assertions in `server/test_config_history.py` plus the `theme-status` group-count assertion in `companion/test_config_page.py` — both are exact-match tests that WILL fail the moment this field exists, independent of any bug in the new code.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** Delivery mechanism — Poll-response delivery via the existing `/device/v1/display` `sleep_s` field, no service restart, no new protocol field.
- **D-02:** Validation bounds — min 60s (matches `firmware/main/Kconfig.projbuild`'s `FP_MIN_REFRESH_SPACING_S` default, itself this project's own engineering margin, not a vendor-mandated threshold — the GDEP133C02 datasheet documents no such minimum), max 3600s (1 hour). This value was corrected live by the developer from an ungrounded "min 10s" auto-selection.
- **D-03:** Base-value layering — The new `wake_interval_s` config field becomes the base value passed into `quiet_hours_sleep_s()`; the CLI `--sleep` argument becomes the bootstrap/fallback default when the config field is unset. Only what's passed as `base_sleep_s` changes; `quiet_hours_sleep_s(base_sleep_s, state_dir, now=None)`'s own signature and body are untouched.
- **D-04:** Field name — `wake_interval_s` (SEED-002's own suggested name; matches the `_s` suffix convention for a plain duration field).
- **D-05:** Companion UI presentation — A plain numeric `<input type="number">` labeled "Wake interval (seconds)", with a caption naming the battery-vs-freshness trade-off. Confirmed live (see Architecture Patterns, Pattern 2): this genuinely is the first `type="number"` input anywhere in `companion/`.
- **D-06:** Apply-timing convention — Same "applies on the device's next scheduled poll" convention every other Settings field uses (06-CONTEXT.md D-06/D-07). No new mechanism.

### Claude's Discretion

- Exact validation error copy for an out-of-bounds or non-numeric submitted value (mirror the existing generic save-failed flash).
- Exact companion-page form layout/spacing for the new field (mirror the existing Settings page's fieldset pattern; validate against a real preview, per D-05's "new UI pattern" flag).
- Whether the field pre-fills with the *current effective* interval, defaulting to the CLI `--sleep` value on first load — CONTEXT.md calls this "the obvious, only sane choice" but this research found it is **not mechanically obvious to implement** (see Summary and Open Questions #1); a concrete recommendation is proposed below.
- Exact wording of the trade-off caption text under the field.

### Deferred Ideas (OUT OF SCOPE)

- A per-time-of-day variable wake interval (e.g., faster polling during daytime, slower overnight) — out of this phase's scope; Phase 10's quiet-hours window already covers "pause entirely overnight," and a general variable-cadence schedule would be its own future phase if ever wanted.

<phase_requirements>
## Phase Requirements

No requirement ID mapping — this is an unmapped backlog phase promoted from `.planning/seeds/SEED-002-web-configurable-wake-interval.md`, matching Phase 10's own precedent (confirmed against `.planning/REQUIREMENTS.md`: v1 requirements are fully mapped/covered at 17/17, and no CFG-* or DEVICE-* requirement mentions the wake interval — this phase is pure backlog/seed work, not requirement-driven).
</phase_requirements>

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Store the user-set wake interval | API / Backend (`server/device_config.py`) | — | Single source of truth for every user-settable device setting, per its own module docstring; companion and byos_server both read/write through (or around) this file |
| Validate submitted wake interval (bounds, type) | API / Backend (`server/device_config.py::save_device_config()`) | Frontend Server (companion `handle_post()`'s int-conversion gate) | `save_device_config()` is the strict write-path gate (raises `ValueError`); `handle_post()` must convert the HTML form string to `int` *before* that gate can even run its type check |
| Render the Settings form control | Frontend Server (companion `config_page.py`) | — | Companion is a server-rendered HTML app; no client-side framework exists in this codebase |
| Deliver the effective interval to the device | API / Backend (`stub-server/byos_server.py`'s `/device/v1/display` handler) | — | This stdlib-only handler is the sole writer of the wire-protocol `sleep_s` field; it deliberately never imports `server.device_config` (vendor-boundary discipline), so it re-reads the same JSON file with its own best-effort, never-raise function |
| Honor the delivered interval | Device / Firmware (`firmware/main/app_main.c`) | — | Already treats `sleep_s` as an opaque value from the server response; needs no change |

## Standard Stack

No new external packages. This phase extends four existing, already-vendored/first-party files using only the Python stdlib (`json`, `os`, `re` — none of them new imports) and plain HTML. There is nothing to install and no `Package Legitimacy Audit` is applicable — skipping that section entirely per its own "only when this phase installs external packages" gate.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| A plain `<input type="number">` | A `<select>` of preset intervals (e.g., 5/15/30/60 min) | Simpler validation (membership test, matching the existing theme/runway pattern) but less flexible; D-05 already locked the free-numeric-entry UX, so this is documented only as a rejected alternative, not a live option |
| `None`-sentinel for "unset" (this research's recommendation) | A hardcoded `DEFAULT_WAKE_INTERVAL_S` constant in `device_config.py` | Simpler (matches every other field's contract exactly) but risks silently disagreeing with the real deployed `SKYPANE_SLEEP_S` (see Open Questions #1) — rejected as misleading UI |

## Architecture Patterns

### System Architecture Diagram

```
Companion web browser
        │  GET /settings
        ▼
companion/app.py ── ctx["device_config"] = device_config.load_device_config(state_dir)
        │
        ▼
companion/pages/config_page.py::render(ctx)
        │  renders wake_interval_group() — <input type="number" name="wake_interval_s"
        │  value="{current or empty}" min="60" max="3600">
        ▼
Browser (user edits, submits)
        │  POST /settings  {wake_interval_s: "120", ...}
        ▼
companion/app.py::do_POST → config_page.handle_post(form, ctx)
        │  1. int(form.get("wake_interval_s"))  ← NEW: str→int conversion gate
        │  2. device_config.save_device_config(state_dir, wake_interval_s=...)
        │       → normalise/validate against [60, 3600], raise ValueError if not
        ▼
server/device_config.json  (shared file, single source of truth)
        ▲  read (raw JSON, no import of server.device_config — vendor boundary)
        │
stub-server/byos_server.py  (separate OS process, launched by
deploy/skypane-byos.service with --sleep ${SKYPANE_SLEEP_S})
        │  GET /device/v1/display  (device polls)
        │  read_wake_interval_s(state_dir, default=self.args.sleep)
        │     → base_sleep_s (config value if valid, else CLI --sleep)
        │  quiet_hours_sleep_s(base_sleep_s, state_dir)
        │     → sleep_s  (base, or extended through an active quiet-hours window)
        ▼
Device firmware (app_main.c) — enter_deep_sleep(sleep_s), opaque value, no interpretation
```

### Recommended Project Structure

No new files or directories. Every change lands inside four existing files:
```
server/device_config.py          # registry: constants, normalise_wake_interval_s(), load/save
stub-server/byos_server.py       # read_wake_interval_s(), one changed line in the /display handler
companion/pages/config_page.py   # wake_interval_group(), render()/handle_post() wiring
.claude/skills/sketch-findings-skypane/SKILL.md  # new numeric-input touch-target register entry (see Pattern 2)
```

### Pattern 1: The registry field with a `None` "unset" sentinel

**What:** Every existing `device_config.py` field (`theme`, `tracked_runway`, `led_enabled`, `quiet_hours_enabled/start/end`) is normalised to *always* return a concrete, valid value — `load_device_config()`'s documented contract is "Always returns all six keys with valid values." `wake_interval_s` breaks that pattern on purpose: its "unset" state must be distinguishable from "set to a specific number," because the true fallback (the CLI `--sleep` value) is not known to `device_config.py` or to the companion process at all — it lives in `stub-server/byos_server.py`'s own `argparse` namespace in a separate process.

**When to use:** Only for this one field. Do not generalize this exception to any future field without the same cross-process-default problem.

**Example (device_config.py additions):**
```python
# Source: pattern derived from this file's own normalise_quiet_hours_time()/
# normalise_led_enabled() shape, adapted for the None-sentinel exception.
WAKE_INTERVAL_MIN_S = 60   # D-02: matches firmware/main/Kconfig.projbuild's
                           # FP_MIN_REFRESH_SPACING_S default (60), itself this
                           # project's own conservative margin, not a vendor spec.
WAKE_INTERVAL_MAX_S = 3600  # D-02: 1 hour, developer-confirmed.


def normalise_wake_interval_s(value):
    """Return `value` unchanged only when it is an int (explicitly NOT a
    bool - `isinstance(True, int)` is `True` in Python, so a bare
    `isinstance(value, int)` check alone would silently accept a boolean),
    AND within [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] inclusive.
    Otherwise return `None` - the deliberate exception to every other
    field's "always a concrete default" contract in this module, because
    the true fallback (the deployed SKYPANE_SLEEP_S / --sleep CLI value)
    is not known to this process. Never raises.
    """
    if (isinstance(value, int) and not isinstance(value, bool)
            and WAKE_INTERVAL_MIN_S <= value <= WAKE_INTERVAL_MAX_S):
        return value
    return None
```
`load_device_config()`'s returned dict gains `"wake_interval_s": normalise_wake_interval_s(data.get("wake_interval_s"))`. `save_device_config()` gains a `wake_interval_s=None` parameter and this validation:
```python
if wake_interval_s is not None and not (
        isinstance(wake_interval_s, int) and not isinstance(wake_interval_s, bool)
        and WAKE_INTERVAL_MIN_S <= wake_interval_s <= WAKE_INTERVAL_MAX_S):
    raise ValueError(
        "wake_interval_s must be an int in [%d, %d], got %r"
        % (WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S, wake_interval_s))
```
and the `new_config` dict gains `"wake_interval_s": wake_interval_s if wake_interval_s is not None else current["wake_interval_s"]` — same "carry forward unchanged when not supplied" idiom every other field uses.

### Pattern 2: The read function in `byos_server.py`

**What:** A new best-effort, never-raising function, structurally closer to `read_led_enabled()` (single scalar value) than `read_quiet_hours()` (returns a 2-tuple, has an enabled-gate). Confirms Research Question 3.

**Example:**
```python
# Source: pattern copied from read_led_enabled() (stub-server/byos_server.py
# lines 105-127), adapted for a bounded int instead of a bool.
WAKE_INTERVAL_MIN_S = 60
WAKE_INTERVAL_MAX_S = 3600


def read_wake_interval_s(state_dir, default):
    """Best-effort read of the shared device_config.json's wake_interval_s
    field. Never raises. Every failure mode - missing file, unreadable
    file, malformed JSON, non-dict document, missing key, wrong type
    (including bool, which `isinstance(x, int)` alone would wrongly
    accept), or out-of-[60,3600]-range value - degrades to `default`
    (the caller's --sleep CLI value), matching read_led_enabled()'s
    fail-open shape. This is the only place in this file that reads
    wake_interval_s.
    """
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return default
    if not isinstance(data, dict):
        return default
    value = data.get("wake_interval_s")
    if (isinstance(value, int) and not isinstance(value, bool)
            and WAKE_INTERVAL_MIN_S <= value <= WAKE_INTERVAL_MAX_S):
        return value
    return default
```
Note the `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` constants are **independently defined** in this file, not imported — matching this file's stdlib-only, no-cross-import discipline (same reason `_HHMM_RE` and `QUIET_HOURS_TZ` are duplicated here rather than imported from `server.device_config`). Unlike `seconds_until_quiet_hours_end()`/`_HHMM_RE`, **this new function needs no byte-for-byte drift guard** — confirmed by reading `stub-server/test_poll_cycle.py`'s existing drift-guard test (`_quiet_hours_drift_guard`, lines 305-345): it only pins the *arithmetic core* (`seconds_until_quiet_hours_end`) and the shared regex, never `read_led_enabled()`/`read_quiet_hours()` themselves. `read_wake_interval_s()` follows that same "independently written, behaviorally compatible" precedent, not the drift-guarded one.

### Pattern 3: The single call-site change in the `/display` handler

**What:** Confirms Research Question 1. The current line (verified live, `stub-server/byos_server.py:415`):
```python
"sleep_s": quiet_hours_sleep_s(self.args.sleep, self.args.state_dir),
```
becomes:
```python
"sleep_s": quiet_hours_sleep_s(
    read_wake_interval_s(self.args.state_dir, self.args.sleep),
    self.args.state_dir),
```
`quiet_hours_sleep_s(base_sleep_s, state_dir, now=None)`'s own signature and body (lines 234-261) are **completely unchanged** — this confirms D-03's own framing that "only what gets passed as `base_sleep_s` changes." Update the module docstring's local-modifications list (lines 26-45) and the inline comment at the `sleep_s` key (lines 408-414) to describe this new layer, following the exact pattern Phase 10 used when it added the quiet-hours layer on top of the pre-existing raw `self.args.sleep` behavior.

### Pattern 4: The companion Settings group and its unconverted-string pitfall

**What:** A new `wake_interval_group()` function in `config_page.py`, structurally modeled on `led_group()` (a `.theme-status`-wrapped div, `<h2>` heading, one caption `<p>`, no `<fieldset>`/`<legend>`) rather than `quiet_hours_group()` (which has a checkbox gate this field doesn't need).

**Example:**
```python
# Source: pattern derived from led_group() (companion/pages/config_page.py
# lines 365-420), adapted for a numeric input instead of a checkbox.
WAKE_INTERVAL_SECTION_HEADING = "Wake interval"
WAKE_INTERVAL_SECTION_CAPTION = (
    "How often the frame wakes to poll for updates. Shorter means "
    "fresher info and more battery drain; longer means more battery "
    "life and staler info at a glance. Applies on the device's next "
    "scheduled poll.")


def wake_interval_group(current_wake_interval_s):
    """`current_wake_interval_s` is None when never explicitly set - the
    <input> then renders with no `value` attribute at all (an empty
    field, not a guessed number), and a placeholder names the fallback
    behavior instead of a fabricated default.
    """
    value_attr = (
        ' value="%d"' % current_wake_interval_s
        if current_wake_interval_s is not None else "")
    return (
        '<div class="theme-status" %s="%s">'
        '<h2 class="text-heading">%s</h2>'
        '<p class="text-label section-caption">%s</p>'
        '<label>Wake interval (seconds) '
        '<input type="number" name="wake_interval_s" min="%d" max="%d"'
        ' placeholder="Uses server default"%s></label>'
        "</div>"
    ) % (
        DIRTY_SECTION_ATTR, escape_html(WAKE_INTERVAL_SECTION_HEADING),
        escape_html(WAKE_INTERVAL_SECTION_HEADING),
        escape_html(WAKE_INTERVAL_SECTION_CAPTION),
        device_config.WAKE_INTERVAL_MIN_S, device_config.WAKE_INTERVAL_MAX_S,
        value_attr,
    )
```
`handle_post()` needs the explicit string-to-int conversion this pattern requires (see Common Pitfalls #1 for the full rationale):
```python
submitted_wake_interval = form.get("wake_interval_s")
if submitted_wake_interval is None or submitted_wake_interval == "":
    wake_interval_s = None  # leave unchanged / stays unset
else:
    try:
        wake_interval_s = int(submitted_wake_interval)
    except ValueError:
        return FLASH_SAVE_FAILED
```
then pass `wake_interval_s=wake_interval_s` into the single `save_device_config()` call, whose own range check raises `ValueError` for an out-of-bounds int, already caught by the handler's existing `except (ValueError, OSError): return FLASH_SAVE_FAILED`.

### Anti-Patterns to Avoid

- **Passing the raw form string straight through, matching the `quiet_hours_start`/`quiet_hours_end` pattern:** those two fields are strings end-to-end (HH:MM), so passing them unconverted is correct there. `wake_interval_s` is an int end-to-end in `device_config.py`, so the *same* pass-through habit here would make every legitimate submission fail `isinstance(value, int)` inside `save_device_config()`. This is the single highest-risk copy-paste mistake in this phase.
- **Giving `wake_interval_s` a hardcoded `DEFAULT_WAKE_INTERVAL_S` constant "to match the other fields":** this would silently disagree with the real per-deployment `SKYPANE_SLEEP_S` value (see Open Questions #1) and mislead the Settings page's pre-fill.
- **Reusing a bare `isinstance(value, int)` check with no bool exclusion:** `isinstance(True, int)` is `True` in Python. Every bounded-int check in this phase (`normalise_wake_interval_s()`, `save_device_config()`'s validation, `read_wake_interval_s()`) must explicitly exclude `bool`, the same defensive pattern this codebase already uses the *other* direction (`normalise_led_enabled()` accepts only `isinstance(value, bool)`, deliberately rejecting `0`/`1`).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Bounded-integer validation | A custom parsing/clamping helper | Python's own `isinstance()` + inclusive range comparison (the pattern shown in Pattern 1/2 above) | This is genuinely simple enough that stdlib comparisons are correct and sufficient — no library needed, and none of this codebase's existing dependencies offer anything narrower |
| HTML number-input min/max enforcement | Custom JS validation | The native `<input type="number" min="60" max="3600">` HTML5 attributes, PLUS the mandatory server-side re-check in `save_device_config()` | Matches this codebase's existing double-gate discipline (e.g., the theme radio buttons are also membership-checked server-side even though only registry values are ever rendered as options) — client-side constraints are UX sugar, never the security boundary |

**Key insight:** This phase needs no new abstraction. The entire implementation is "add one more field to an existing, well-established registry pattern" — the risk here is not technical complexity, it's fidelity to the existing pattern's edge cases (the bool-vs-int gotcha, the string-vs-int form-data gotcha, and the unusual `None`-sentinel exception this one field needs).

## Common Pitfalls

### Pitfall 1: Form-string vs. registry-int type mismatch
**What goes wrong:** `handle_post()` passes `form.get("wake_interval_s")` (always a `str`, e.g. `"120"`) straight to `save_device_config(wake_interval_s=...)`, which rejects it with `ValueError` because it isn't an `int` — every single legitimate save fails, even with an in-range value.
**Why it happens:** The two most recently added fields in this exact file (`quiet_hours_start`/`quiet_hours_end`) are strings end-to-end, so the "pass form values straight through unvalidated, let `save_device_config()` validate" habit is fresh and easy to over-generalize.
**How to avoid:** Explicitly `int()`-convert in `handle_post()` before the `save_device_config()` call (Pattern 4 above), with a `try/except ValueError: return FLASH_SAVE_FAILED` guard for non-numeric input (e.g., `"abc"`, `""`, a submitted float string like `"1.5"`).
**Warning signs:** A test that submits `{"wake_interval_s": "120"}` and expects success will fail with a `ValueError` inside `save_device_config()` instead — reproduces cleanly and immediately in any test harness once written.

### Pitfall 2: Breaking every exact dict-equality test in `server/test_config_history.py`
**What goes wrong:** Adding a 7th key to `load_device_config()`'s returned dict changes its shape. `server/test_config_history.py` contains **11 separate occurrences** of an exact dict-literal equality check (e.g. `if config != {"theme": "white", "tracked_runway": "3", ..., "quiet_hours_end": "07:00"}:`) — every one of them will now fail even if the new code is completely correct, because Python dict `!=` comparison requires identical key sets.
**Why it happens:** This test file's own style favors exact-shape assertions over partial/subset checks — a deliberate strictness choice (it catches accidental extra/missing keys), but it means every registry-widening phase (Phase 10 clearly hit this too, since all 11 existing literals already include `quiet_hours_enabled/start/end`) must touch every one of these literals in the same commit.
**How to avoid:** `grep -n '"quiet_hours_end":' server/test_config_history.py` to find and update all 11 occurrences to add `"wake_interval_s": None` (or the specific saved value the test scenario sets up), mirroring exactly what Phase 10 must have done for its own three new keys.
**Warning signs:** A wall of failing dict-inequality assertions with no other code defect — this is purely a test-fixture-shape update, not a logic bug, and should be triaged as such immediately (do not go looking for a bug in `normalise_wake_interval_s()` if all 11 fail identically).

### Pitfall 3: Breaking the `theme-status` group-count assertion in `companion/test_config_page.py`
**What goes wrong:** `companion/test_config_page.py` line 319-320 asserts `rendered.count('class="theme-status"') != 3` (i.e., expects exactly 3: Runway/Diagnostic LED/Quiet hours). Adding a fourth `.theme-status`-wrapped group (Wake interval) makes this assertion fail by construction, independent of any bug.
**Why it happens:** Same "exact count, not `>=`" strictness discipline as Pitfall 2, in a sibling test file for the sibling page module.
**How to avoid:** Update the assertion to `!= 4` and its error message, as part of the same task that adds `wake_interval_group()` — do not treat the resulting test failure as a signal to debug the new group's markup.
**Warning signs:** A single, isolated failure naming the theme-status count, with the new group's own dedicated tests all passing.

### Pitfall 4: Confusing "wake interval" with "quiet-hours window" semantically
**What goes wrong:** A future edit conflates the two into one field, or has the wake-interval bounds check reject a value that a quiet-hours *extension* legitimately needs to exceed (e.g., a computed `remaining` of 6+ hours during an overnight window).
**Why it happens:** Both fields flow into the same `quiet_hours_sleep_s()` call and both ultimately set the same wire-protocol `sleep_s` key, so it's easy to blur "the configured base cadence" with "the final delivered value."
**How to avoid:** `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` (60-3600s) bound only the *stored config field* — the *value returned by `quiet_hours_sleep_s()`* is explicitly allowed to exceed 3600s when a quiet-hours window is active and its `remaining` seconds is larger (the existing `max(base_sleep_s, remaining)` in `quiet_hours_sleep_s()`, lines 246-261, is untouched by this phase and must stay untouched). Do not add a second bounds check after `quiet_hours_sleep_s()` returns.
**Warning signs:** A device stuck waking every hour during an 8-hour quiet-hours window because something re-clamped the extended `sleep_s` back down to 3600.

## Code Examples

Verified patterns from the live codebase (all file/line references confirmed 2026-09-04, post-Phase-10):

### Current `/display` handler `sleep_s` line (the exact target of D-03)
```python
# Source: stub-server/byos_server.py, line 415 (read live this session)
"sleep_s": quiet_hours_sleep_s(self.args.sleep, self.args.state_dir),
```

### `read_led_enabled()` — the closest existing structural template
```python
# Source: stub-server/byos_server.py, lines 105-127 (read live this session)
def read_led_enabled(state_dir):
    try:
        with open(device_config_path(state_dir)) as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return True
    if not isinstance(data, dict):
        return True
    value = data.get("led_enabled")
    if isinstance(value, bool):
        return value
    return True
```

### `save_device_config()`'s existing validation shape — the template for the new bounds check
```python
# Source: server/device_config.py, lines 452-459 (read live this session)
if led_enabled is not None and not isinstance(led_enabled, bool):
    raise ValueError("led_enabled must be a bool, got %r" % (led_enabled,))
if quiet_hours_enabled is not None and not isinstance(quiet_hours_enabled, bool):
    raise ValueError("quiet_hours_enabled must be a bool, got %r" % (quiet_hours_enabled,))
if quiet_hours_start is not None and not (isinstance(quiet_hours_start, str) and _HHMM_RE.match(quiet_hours_start)):
    raise ValueError("quiet_hours_start must be a 24-hour zero-padded HH:MM string, got %r" % (quiet_hours_start,))
```

### `firmware/main/Kconfig.projbuild`'s `FP_MIN_REFRESH_SPACING_S` — the D-02 grounding source
```
# Source: firmware/main/Kconfig.projbuild, lines 122-125 (read live this session)
config FP_MIN_REFRESH_SPACING_S
    int "Minimum seconds between panel refreshes"
    range 30 86400
    default 60
```
Note this is a *different* knob (panel-redraw spacing, not wake/poll cadence) governing the same battery-vs-freshness tradeoff on the same device — 11-CONTEXT.md's own D-02 rationale already states this precisely; confirmed here that the Kconfig text explicitly frames 60 as "this project's own conservative engineering margin... not a vendor-mandated threshold," matching the CONTEXT.md summary word-for-word.

## Runtime State Inventory

Not applicable — this is a greenfield-within-an-existing-file feature addition (a new field to an existing store), not a rename/refactor/migration phase. No stored data, live service config, OS-registered state, or build artifacts carry the string `wake_interval_s` anywhere yet for this phase to migrate.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pre-fill via a `None`-sentinel + empty/placeholder `<input>` is the right resolution to the "companion process can't see the CLI `--sleep` value" gap, rather than reading `skypane.env` directly or hardcoding a matching constant | Architecture Patterns, Pattern 1 / 3; Summary | If wrong, the planner may instead want `companion/app.py` to read `SKYPANE_SLEEP_S` from the environment/`skypane.env` directly for pre-fill accuracy — a larger, cross-cutting change this research recommends against but did not get developer confirmation on (11-CONTEXT.md was a fully autonomous `--auto` pass with no developer interaction on this specific point) |
| A2 | The exact HTML markup shape proposed for `wake_interval_group()` (a `.theme-status` div, no `<fieldset>`) is correct without a live-preview check | Architecture Patterns, Pattern 4 | Low risk — this literally mirrors `led_group()`'s already-shipped, already-verified markup shape; D-05 itself already flags this control type (not the wrapper) as needing a real-preview check |
| A3 | Test-count deltas (companion/test_config_page.py's 73, stub-server/test_poll_cycle.py's 29, server/test_config_history.py's 39) will each need incrementing by an unspecified number of new checks, mirroring Phase 10's own "+5"-per-task pattern | Common Pitfalls #2/#3; Validation Architecture | Low risk if wrong — this is a process note (update `EXPECTED_CHECK_COUNT` alongside new checks), not a functional claim; the exact new count is an implementation detail for the planner/executor to compute, not predict here |

**If this table is empty:** N/A — see rows above.

## Open Questions

1. **How should the companion Settings page pre-fill this field when it has never been explicitly set?**
   - What we know: 11-CONTEXT.md's Claude's Discretion section states pre-filling with "the CLI `--sleep` value on first load" is expected and "the obvious, only sane choice." `companion/app.py` and `stub-server/byos_server.py` are separate OS processes; the companion process has no code path today that reads `SKYPANE_SLEEP_S` or `skypane.env` (confirmed by grep — `SKYPANE_SLEEP_S` appears only in `deploy/skypane-byos.service`, `deploy/skypane.env.example`, `hardware/BATTERY-RUN.md`, and `stub-server/byos_server.py` itself).
   - What's unclear: whether the planner wants to (a) accept this research's recommendation (empty/placeholder input, `None` sentinel, documented as "uses the server's own default"), (b) add a new companion-side read of `skypane.env`/the environment (bigger, cross-cutting change, arguably out of this phase's stated scope), or (c) pick an arbitrary hardcoded pre-fill constant and accept it may occasionally show a number that doesn't match the real deployed cadence.
   - Recommendation: option (a) — it's the smallest change, it's honest about what the UI does and doesn't know, and it matches this project's existing "never guess, degrade safely" discipline (e.g., `read_led_enabled()`'s fail-open behavior). Flag this explicitly to the developer during plan review since it's a real deviation from CONTEXT.md's stated "obvious" expectation, even though CONTEXT.md's own decisions section never actually locked a specific mechanism for it.

2. **Should an unchecked/cleared numeric field (empty string submission) mean "reject the whole save" or "leave unchanged"?**
   - What we know: `theme`/`tracked_runway`/`quiet_hours_start`/`quiet_hours_end` treat *absence from the form* as "leave unchanged" (`None` passed through). A number input that's always rendered (not conditionally omitted) will always be present in the POST body, but its *value* could be an empty string if the user manually clears it.
   - What's unclear: whether an empty string should behave like "field absent" (leave unchanged) or be treated as an explicit-but-invalid submission (reject the whole save, matching the crafted-value rejection pattern for checkboxes).
   - Recommendation: treat empty string the same as absent (`None`, leave unchanged) — this is the least surprising behavior for a numeric input a user might clear by accident while editing, and keeps the "all-or-nothing" contract about **invalid** values, not about **incomplete edits**. This is squarely within 11-CONTEXT.md's Claude's Discretion bucket ("exact validation error copy...") and does not need a fresh discuss-phase pass.

## Environment Availability

Skipped — this phase has no external tool/service/runtime dependencies beyond the Python stdlib already used by every file it touches. No new package, database, or CLI tool is introduced.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | Hand-rolled `check()`/`EXPECTED_CHECK_COUNT` harness (stdlib-only, no pytest) — this project's own convention across every `test_*.py` file |
| Config file | none — each test file is directly executable |
| Quick run command | `server/.venv/bin/python3 companion/test_config_page.py` (fastest relevant harness; touches the changed page module directly) |
| Full suite command | `server/.venv/bin/python3 server/test_config_history.py && server/.venv/bin/python3 companion/test_config_page.py && python3 stub-server/test_poll_cycle.py` |

### Phase Requirements → Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| (unmapped) | `normalise_wake_interval_s()` accepts in-range ints, rejects out-of-range/bool/non-int, returns `None` on failure | unit | `server/.venv/bin/python3 server/test_config_history.py` | ✅ (extend existing file) |
| (unmapped) | `save_device_config(wake_interval_s=...)` raises `ValueError` for out-of-bounds/wrong-type, round-trips valid values via `load_device_config()` | unit | `server/.venv/bin/python3 server/test_config_history.py` | ✅ (extend existing file) |
| (unmapped) | All 11 existing dict-equality checks updated for the new 7th key | unit (regression) | `server/.venv/bin/python3 server/test_config_history.py` | ✅ (extend existing file) |
| (unmapped) | `wake_interval_group()` renders correct markup, escapes current value, omits `value=` attr when `None` | unit | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ (extend existing file) |
| (unmapped) | `theme-status` group count assertion updated 3→4 | unit (regression) | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ (extend existing file) |
| (unmapped) | `handle_post()` int-converts, rejects non-numeric, rejects out-of-bounds, persists valid values, leaves file byte-identical on rejection | unit | `server/.venv/bin/python3 companion/test_config_page.py` | ✅ (extend existing file) |
| (unmapped) | `read_wake_interval_s()` degrades to `default` on missing/malformed/out-of-range/bool/absent-key, returns config value when valid | unit | `python3 stub-server/test_poll_cycle.py` | ✅ (extend existing file) |
| (unmapped) | `/display` handler's `sleep_s` reflects the configured `wake_interval_s` (and still correctly extends through an active quiet-hours window, unaffected) | integration | `python3 stub-server/test_poll_cycle.py` | ✅ (extend existing file) |

### Sampling Rate
- **Per task commit:** `server/.venv/bin/python3 companion/test_config_page.py` (or `server/test_config_history.py`, whichever file the task touched)
- **Per wave merge:** the full three-command sequence above
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
None — existing test infrastructure (`server/test_config_history.py`, `companion/test_config_page.py`, `stub-server/test_poll_cycle.py`) already covers every touched module with an established harness; no new test file or fixture is needed, only extensions to the three existing ones.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | no | Unaffected — this phase adds a settings field behind the companion app's existing session auth, already covered by prior phases |
| V3 Session Management | no | Unaffected |
| V4 Access Control | no | Unaffected — same POST /settings route, same session gate as every other settings field |
| V5 Input Validation | yes | Explicit `isinstance()` + inclusive-range check on both the read path (`read_wake_interval_s()`, fail-open to a safe default) and the write path (`save_device_config()`, fail-closed with `ValueError`) — matches this codebase's existing asymmetric-validation convention (06-RESEARCH.md's V5 row, reused verbatim by Phase 10) |
| V6 Cryptography | no | Unaffected |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| A hostile/corrupted `device_config.json` (hand-edited or written by a bug) carrying a boolean, a string, or an out-of-range int for `wake_interval_s` | Tampering | `read_wake_interval_s()`'s explicit `isinstance(value, int) and not isinstance(value, bool)` + range check degrades to the safe CLI default rather than propagating a bad value into `quiet_hours_sleep_s()`'s arithmetic — never let an untrusted on-disk value reach a numeric computation unchecked (T-06-01-01 precedent, reused) |
| A crafted POST body submitting a non-numeric or out-of-range `wake_interval_s` (e.g., `"9999999"`, `"-1"`, `"1e10"`) | Tampering | `handle_post()`'s `int()` conversion (rejecting non-numeric with `ValueError`) followed by `save_device_config()`'s strict range check (rejecting out-of-bounds with `ValueError`) — both before any write touches the file, preserving the existing all-or-nothing rejection contract |
| A denial-of-battery attack via an extremely short wake interval (e.g., every 60s indefinitely, if an attacker could reach the settings form) | Denial of Service (against the device's own battery, DEVICE-05) | The 60s floor (D-02) is itself the mitigation — already the minimum this project considers acceptable; no additional rate-limiting needed since the settings form is already behind session auth (out of this phase's scope to re-verify) |

## Sources

### Primary (HIGH confidence — direct codebase reads this session)
- `stub-server/byos_server.py` (full read, lines 1-270 and 380-488) — `/display` handler, `read_led_enabled()`, `read_quiet_hours()`, `quiet_hours_sleep_s()`, `seconds_until_quiet_hours_end()`, argparse `--sleep` default, drift-guard test location
- `server/device_config.py` (full read, 669 lines) — complete registry pattern: `THEMES`/`RUNWAYS`, every `normalise_*()` function, `load_device_config()`/`save_device_config()`, `quiet_hours_status()`
- `companion/pages/config_page.py` (full read, 871 lines) — `led_group()`, `quiet_hours_group()`, `render()`, `handle_post()`, confirmed zero existing `type="number"` inputs anywhere in `companion/`
- `firmware/main/Kconfig.projbuild` (targeted read, lines 120-170) — `FP_MIN_REFRESH_SPACING_S`'s `range 30 86400` / `default 60`, full rationale text matching 11-CONTEXT.md's D-02 quote
- `firmware/main/state_machine.c` / `firmware/main/app_main.c` (grep + targeted read) — confirmed `sleep_s` flows as an opaque `uint32_t` from `fp_poll_once()` to `enter_deep_sleep()`, no firmware interpretation
- `.claude/skills/sketch-findings-skypane/SKILL.md` — confirmed the touch-target register has no numeric-input entry yet; `<input type="time">` is the only precedent for a "new control shape" note, added by Phase 10
- `stub-server/test_poll_cycle.py` (targeted grep + read, lines 1-60, 300-345) — `EXPECTED_CHECK_COUNT = 29`, drift-guard scope confirmed (arithmetic core + regex only)
- `companion/test_config_page.py` (targeted grep + read) — `EXPECTED_CHECK_COUNT = 73`, `theme-status` count assertion (== 3) at lines 319-320
- `server/test_config_history.py` (targeted grep + read) — `EXPECTED_CHECK_COUNT = 39`, confirmed this file (despite its name) is device_config.py's own test harness, 11 occurrences of the exact-dict-equality pattern
- `companion/app.py` (targeted grep) — confirmed `ctx["device_config"] = device_config.load_device_config(state_dir)` (line 673), confirmed `form = self.read_form()` yields plain strings via `parse_qs`
- `deploy/skypane-byos.service` / `deploy/skypane.env.example` — confirmed `SKYPANE_SLEEP_S` only exists in the deploy unit's env substitution and the stub-server's own CLI arg, with no companion-side read path today

### Secondary (MEDIUM confidence)
- `.planning/phases/10-scheduled-quiet-hours/10-CONTEXT.md`, `10-03-SUMMARY.md` — read via 11-CONTEXT.md's own canonical-references pointers; used to confirm the pre-Phase-10 vs. current shape distinction rather than assuming staleness

### Tertiary (LOW confidence)
- None — every claim in this document is either a direct code read (this session) or explicitly tagged `[ASSUMED]` in the Assumptions Log above.

## Metadata

**Confidence breakdown:**
- Standard stack: N/A (no new packages) — HIGH confidence there is nothing to evaluate
- Architecture: HIGH — every pattern shown is copied from and cross-checked against live, currently-shipped code in this exact repo, not inferred from documentation or memory
- Pitfalls: HIGH — all four pitfalls were derived from actually reading the current code and test files rather than speculating; Pitfalls 2 and 3 are mechanically certain to occur (grep-counted), not merely likely

**Research date:** 2026-09-04
**Valid until:** Until any of the four touched files (`server/device_config.py`, `stub-server/byos_server.py`, `companion/pages/config_page.py`, their three test files) changes shape again — this is an internal-codebase research doc, not a fast-moving external-library one; no calendar-based expiry applies, but re-verify line numbers before executing if any other phase lands first.
