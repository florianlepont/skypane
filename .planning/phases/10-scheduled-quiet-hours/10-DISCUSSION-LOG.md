# Phase 10: Scheduled quiet hours - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-09-03
**Phase:** 10-scheduled-quiet-hours
**Areas discussed:** Pause mechanism, Edit responsiveness, Window shape, Panel state at
the boundary (entry screen content/language, exit transition), Enabled/disabled flag

---

## Pause mechanism

A live code finding surfaced before this question: `sleep_s` turns out to be a fully
server-controlled, per-response value (`stub-server/byos_server.py`'s
`self.args.sleep`) that the firmware just deep-sleeps for — contradicting the seed's
own assumption that a full sleep-extension needed firmware changes.

| Option | Description | Selected |
|--------|-------------|----------|
| Extend sleep_s | Server computes sleep_s to span past the window's end; device doesn't wake at all during the window; zero firmware changes | ✓ |
| Skip the display refresh only | Normal wake cadence continues; server re-serves the same image_hash so firmware's existing hash-skip logic suppresses the redraw | |
| Both, chosen by cadence | Hybrid depending on configured wake interval | |

**User's choice:** Extend sleep_s (recommended option).
**Notes:** This reopens and reverses the implicit premise in SEED-001's own "Behavior
decision" bullet, which assumed this was the more expensive path.

---

## Edit responsiveness

Re-asked twice via the question tool after two dismissals (dialog appeared not to be
going through) and once as a plain-text fallback, before being re-asked successfully
through the question tool at the user's request.

| Option | Description | Selected |
|--------|-------------|----------|
| Acceptable as-is | Matches existing "applies on next scheduled poll" rule (06-CONTEXT.md D-06/D-07) | ✓ |
| Need a faster wake | Would require a new mechanism (reusing/extending the manual poll-trigger CFG-07, or a sleep cap) | |

**User's choice:** Acceptable as-is (recommended option).
**Notes:** None.

---

## Window shape

| Option | Description | Selected |
|--------|-------------|----------|
| One daily recurring window | Same start/end every day | ✓ |
| Day-specific windows | Different start/end per weekday | |

**User's choice:** One daily recurring window (recommended option).
**Notes:** Also surfaced, not asked live: the window is a local wall-clock (Europe/Paris)
concept but the codebase currently only reasons in UTC — flagged as a research note
for the phase researcher (stdlib `zoneinfo`, DST correctness), not put to the user as
a question.

---

## Panel state at the boundary — entry screen content

| Option | Description | Selected |
|--------|-------------|----------|
| Freeze on last content | No new render; panel just stays whatever it last showed | |
| Dedicated "going quiet" render | A new visual state drawn once at window entry | ✓ |

**User's choice:** Dedicated render.

### Follow-up: screen content

| Option | Description | Selected |
|--------|-------------|----------|
| Plain fill, no text | Neutral background, no information, no exception to the "no status text" rule needed | |
| Message with a return time | A real, deliberate exception to the "no status text" rule, same class as the battery icon | ✓ (via free text) |

**User's choice (free text):** "Un message en mode 'couvre-feu / Bonne nuit' Retour à ..." — a curfew/good-night framing with a return time, given as a French example.

### Follow-up: screen language

| Option | Description | Selected |
|--------|-------------|----------|
| English, consistent with the rest of the panel | e.g. "QUIET HOURS" / "Back at 07:00" | ✓ |
| French, as in the example | e.g. "COUVRE-FEU" / "Retour à 07h00" | |

**User's choice:** English (recommended option).
**Notes:** The developer's own example was French, but every other piece of panel text
(DEPARTING/ARRIVING, RWY 3) is English — asked explicitly to confirm the translation
was wanted rather than assumed.

---

## Panel state at the boundary — exit transition

| Option | Description | Selected |
|--------|-------------|----------|
| Silent transition | Next normal poll renders the real board directly, no intermediate screen | ✓ |
| Symmetric "waking up" screen | A dedicated transition screen before resuming normal display | |

**User's choice:** Silent transition (recommended option).
**Notes:** None.

---

## Enabled/disabled flag

| Option | Description | Selected |
|--------|-------------|----------|
| Separate enabled/disabled checkbox | Independent boolean, same pattern as led_enabled — times persist even when disabled | ✓ |
| Presence of times = enabled | Simpler; disabling means clearing the fields | |

**User's choice:** Separate checkbox (recommended option).
**Notes:** None.

---

## Claude's Discretion

- Exact config field names in `device_config.py`'s registry
- Exact companion-page form layout for the quiet-hours fieldset
- Exact pixel layout/typography/color of the "QUIET HOURS / Back at HH:MM" screen (the
  copy direction and language are locked; the visual design is not)
- Behavior when a single poll's normal sleep_s would already carry the device past the
  window on its own
- Boundary hysteresis/off-by-one handling at the exact configured end time

## Deferred Ideas

- A faster way to apply a quiet-hours edit mid-sleep (extending CFG-07's manual poll
  trigger, or a sleep cap) — explicitly rejected for this phase, revisit only if the
  edit lag proves to be a real annoyance in practice.
- Day-specific/multiple quiet-hours windows — explicitly rejected in favor of one
  daily recurring window.
- A symmetric "waking up" screen at window exit — explicitly rejected in favor of a
  silent transition.
