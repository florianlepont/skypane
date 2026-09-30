# Phase 44 Companion Design Proposal

**Status:** Draft for owner review. This proposes an interface direction; it
does not authorise production implementation.

## Product promise

The companion answers three questions without technical interpretation:

1. Is the frame working normally?
2. What did it last show?
3. What can I change now?

Normal operation stays quiet. A problem earns attention only when the owner
can do something about it. Every explanation appears beside its relevant
action, never as a page slogan or a hidden technical essay.

## Shared structure

- Use a restrained reading width on desktop. A status panel must not stretch
  across an empty wide screen just because space is available.
- Remove every page-description slogan and redundant freshness line.
- Keep one compact freshness indicator in the persistent navigation area.
- Use a green, amber, or red status mark only for the current actionable
  state. Unknown airline data is informational, never a warning.
- Reserve cards for an action, an image, or a compact comparison. Do not turn
  every sentence into a card.
- Preserve one clear heading per page, sentence-case labels, and a visible
  keyboard focus state. Desktop and mobile use the same content order.

## Navigation

Proposed navigation labels:

| Current label | Proposed label | Reason |
| --- | --- | --- |
| Home | General | It groups the frame's current situation and recent activity. |
| Display | Display | It remains the place where the image's appearance is chosen. |
| Flights | Flights | It remains a simple history. |
| Airlines | Airlines | It remains the place for image and company information. |
| Health | Status | It names the result the owner needs to understand. |
| Device | Advanced settings | It groups wake interval, diagnostic LED, and immediate refresh without pretending they are daily tasks. |
| Update | Updates | It uses a plain plural label for current software and available releases. |

The bottom navigation shows only the selected destination and a compact,
non-interactive freshness state. It must never overflow at 360 px.

## General

**Owner decision:** Direction B, "The frame signal", is approved as the
baseline. General becomes a concise overview of the frame rather than a
diagnostics dashboard.

```text
Desktop
+----------------------------+  +------------------------------+
| Latest frame image         |  | Recent flights               |
| generated time + flight    |  | airline, flight, route, time |
|                             |  | [Show image] on each row     |
+----------------------------+  +------------------------------+

[Battery: 94%]              [Actionable warning, only if one exists]
```

The current frame signal is the visual anchor: latest flight, route, generated
time, and a compact normal-or-action-needed state. Recent flights remain
adjacent on desktop and follow this signal on mobile. The actual frame image is
available from the signal rather than competing with it. Battery stays as a
compact, readable fact. Connection, data-source, and schedule tiles disappear
while healthy; an actionable problem becomes a short linked status instead.
The daily activity band moves to Status. The next-refresh state explains the
cadence in one plain sentence only when it helps understand a delay.

## Display

**Owner decision:** The configuration model is approved: what appears → choose
its appearance → optional per-flight rule override → Quiet hours.

Display is a three-part configuration flow, with a single live frame preview:

1. **What appears** — Departures, arrivals, and calendar flights each expose
   their current appearance in the same compact row.
2. **Choose its appearance** — selecting one source reveals its accurate colour
   choices and updates the uncropped preview. Rules per flight are visibly
   subordinate overrides, not a competing fourth category.
3. **Frame schedule** — Runway and Quiet hours are separate sections. Quiet
   hours use start/end fields plus simple presets (Night, Day, Always on), not
   a clock wheel as the primary control.

No duplicate screen-status cards, duplicate "Appearance" heading, next-wake
copy, or decorative description survives.

## Flights

Flights is a simple, scan-friendly history. Each row contains airline, flight,
route, arrival/departure, relative time, and a direct "Show image" action.
There is no corroboration column, technical expansion, hex code, or explanatory
intro. Filtering can remain available only when it has a concrete user need,
without tutorial copy occupying the page.

## Airlines

**Owner decision:** The source-information and owner-changes distinction,
including the discoverable aircraft-type selector, is approved.

Airlines becomes an explicit two-level editor:

```text
Airline
  Source information              Your changes
  Known aircraft types (A320, …)  Images and crop
  [Choose aircraft type]          [Edit company] [Add image]
```

Every known aircraft type is discoverable through the same selector. Each type
follows the same badge rule. Source information and owner changes are visibly
separate, so a person knows what can be edited. Images offer a labelled action
and a framed drag-to-position crop area. "Replaced" is removed unless it can
be expressed as a clear source-versus-personal-image relationship. Deleting a
manual image includes an explicit outcome and leaves a clear edit path.

## Status

Status uses a centred, readable stack instead of full-width empty cards:

1. **Frame connection** — a clear sentence plus short help explaining the
   timestamp's meaning.
2. **Battery** — current percentage and a switch for Percentage / Voltage,
   with the readings action visually secondary.
3. **Flight data** — a single current result; source-comparison help lives in
   an accessible information control, not a long expansion.
4. **Today's activity** — the moved daily band, shown as history rather than
   a Home distraction.

No battery-duration range, technical caveat expansion, repeated last-aircraft
copy, unknown-airline warning, or repeated resolution instruction appears.

## Advanced settings

Advanced settings contains only controls that change frame behaviour:

- **Wake interval** — select the cadence with a concise explanation of its
  practical effect.
- **Diagnostic LED** — choose its behaviour with an observable explanation.
- **Refresh now** — a direct action with a confirmation of the requested
  refresh and its resulting image/state.

Screen type, next wake, generic hardware/data/diagnostic copy, and unrelated
battery-history explanations are removed.

## Updates

Updates starts with one current-software panel: a firmware icon, installed
version, installed state, and one relevant date. Below it, only real,
installable releases appear. Bench images and failed test builds are not
presented as choices. Release rows use a compact version label, short purpose,
and one explicit install action.

## Decisions requested from the owner

1. Approve or change the navigation labels, particularly **General**, **Status**,
   and **Advanced settings**.
2. **Approved:** Use the General page's frame-signal-first desktop split and
   mobile sequence from Direction B.
3. **Approved:** Use the Display configuration model: what appears → accurate
   appearance → optional rule override → Quiet hours.
4. **Approved:** Separate source information from owner changes and provide a
   discoverable aircraft-type selector on Airlines.

After these decisions, focused plans will be created only for the accepted
seams and files.
