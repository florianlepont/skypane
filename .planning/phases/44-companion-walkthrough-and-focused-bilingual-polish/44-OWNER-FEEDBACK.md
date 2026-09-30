# Phase 44 Owner Feedback

**Captured:** 2026-09-30  
**Status:** Input collected; no production change is authorised until the owner
approves a focused design proposal.

## Design objective

The companion must be understandable and usable by a person with little
technical knowledge. It should show the current state in plain language,
remove repeated information, explain only what is needed at the moment of a
decision, and make the next action obvious.

## Navigation

- Remove the "screen on" and "quiet hours enabled" status text from its
  current navigation position; it has little value there.
- Repair the dark-theme control overflow shown in the captured narrow layout.
- Explore a compact, shared freshness/status indicator in the bottom
  navigation rather than repeating "updated just now" on individual pages.

## Home

- Evaluate renaming "Home" to "General"; the owner raised this as an open
  naming question, not an approved change.
- Remove the page description (for example, "Your frame at a glance"). This
  applies as a cross-page principle: page-description slogans add no value.
- Merge the duplicated screen and quiet-hours cards into one clear current
  state. Do not repeat "on" and do not show a next-wake note outside the
  configuration action where it matters.
- Explain the update cadence in plain language near the next-update state, so
  a non-technical person understands why the frame does not update
  continuously.
- Keep battery information visible during normal operation. Replace normal
  connection and flight-data tiles with a contextual warning or success state
  only when it requires attention, linking to Health for detail.
- Move the daily activity band from Home to Health.
- Give the latest-frame preview and recent-flight list stronger priority; they
  are among the most useful Home information.
- Produce a modern, more pleasant Home proposal for both desktop and mobile
  after feedback for the remaining pages is collected.

## Display

- Remove the non-actionable "Screen: aircraft frame" information and all
  page-description slogans, including "Everything the frame displays, and
  when" and the explanatory theme sentence.
- Remove repeated on/off and quiet-hours configuration tiles from this page;
  they duplicate the actual controls.
- Remove the repeated "Appearance" title.
- Repair the truncated aircraft preview below colour selection.
- Make colour swatches accurately distinguish the real output, including
  light and non-light variants that currently look identical.
- Redesign the appearance-selection interaction so departures, arrivals,
  calendar flights, and per-flight rules are understandable as a single
  coherent configuration model.
- Rename the "What it watches" section to "Runway", remove its duplicated
  label, and remove the next-wake text from the runway description.
- Rename the on/off timing section to "Quiet hours".
- Improve the quiet-hours time selector so it is more approachable than the
  current clock-wheel presentation.

## Flights

- Remove the freshness line, the "last 50 aircraft" explanation, and the
  callsign/hex filtering hint. They do not help the owner complete the core
  task.
- Remove the corroboration column.
- Remove the expanded technical-detail toggle and its hex code, full timestamp,
  and runway details; this information has no user value in this view.
- Put the action to display a flight image directly on each flight row.

## Airlines

- Establish one clear rule for aircraft types. A type must either be presented
  consistently for every airline, or omitted consistently; the current
  inconsistent badges are confusing.
- Make every known aircraft type for an airline discoverable. For example, the
  owner must be able to see both Transavia aircraft types rather than only one.
- Remove the "Air France illustration" label.
- Replace the "crop preview" explanatory sentence with a self-evident framed
  drag-and-drop crop area.
- Explain or remove the "replaced" badge; it currently has no understandable
  purpose.
- Clarify the purpose of the delete control for manually added images and add
  an understandable path to edit flight or airline information.
- Restructure the page so a person can distinguish source data from their own
  changes, understand which company- and aircraft-type-level actions exist,
  and find those actions without guessing.

## Health

- Remove the freshness line and the page-description sentence that combines
  frame state with server-data quality; neither helps the owner act.
- Do not treat an unidentified airline as a warning. There will always be
  unknown companies, so this is informational background rather than an
  actionable problem.
- Constrain wide desktop status cards to a readable content width. The current
  full-width tiles leave an unattractive, uninformative empty area.
- Remove the physical-frame explanatory subtitle. Add a short, plain-language
  explanation next to "last device connection" so the meaning of that status
  is clear where it is needed.
- Remove the "three months" battery range label and any explanation of that
  scale; it creates noise rather than helping the owner.
- Let the battery chart switch between percentage and voltage readings.
- Reduce the visual weight of the "view the 20 readings" control.
- Remove the expanded battery-details toggle and its technical explanatory
  text.
- Replace the repeated and unclear last-aircraft-detected wording with one
  understandable status.
- Replace the large source-comparison explanation toggle with a compact
  information icon and hover/focus help that explains the result when wanted.
- Remove the repeated instruction explaining that each "Resolve" link opens
  Airlines.
- Correct the visual hierarchy throughout: a healthy-server result with a
  green status mark must be more prominent than its secondary detail text.
- Replace "Our ability to identify flights" with a plainer, more useful
  section title; the exact wording remains a proposal decision.

## Device

- Evaluate renaming "Device" to a clearer term such as "Advanced features";
  this remains an open naming decision.
- Remove the non-actionable screen type, next-wake status, and the
  "hardware, data, and diagnostics" page-description sentence.
- Rename the wake-up section to "Wake interval".
- Remove the explanatory text claiming an aircraft appears within five
  minutes, the insufficient battery-history note, and the repeated wake-up
  cadence explanation; they do not help configure the setting.
- Rename the frame-light section to "Diagnostic LED".
- Replace the current LED sentence and next-wake note with a concise
  explanation of the LED's observable purpose and behaviour.
- Replace the "When you cannot wait" title with a direct action name for
  refreshing now, and add an understandable confirmation of what happened.

## Update

- Clarify the installed-version status so current version, installation state,
  and relevant time are not repeated or competing for attention.
- Remove bench/test firmware images from the installable release list.
- Present each real firmware release with a clearer visual version label or
  small identifying icon.
- Redesign the page's overall hierarchy so updates feel approachable rather
  than like a raw release table.

## Deferred review

The owner will provide feedback for the remaining companion pages before a
single consolidated design proposal is prepared. No item in this document is
an implementation instruction by itself.
