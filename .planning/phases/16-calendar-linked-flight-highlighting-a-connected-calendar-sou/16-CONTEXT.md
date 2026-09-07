# Phase 16: Calendar-linked flight highlighting — a connected calendar sources colour rules automatically - Context

**Gathered:** 2026-09-07
**Status:** Ready for planning

<domain>
## Phase Boundary

The operator connects a calendar to the companion. When the frame displays a flight that calendar lists, the panel uses a chosen theme for that render. This is SEED-003's third and last sub-idea, deferred out of Phase 15 by that phase's D-01 and now unblocked.

It is deliberately **a new source for an existing mechanism, not a new mechanism**. Phase 15 already ships the rule registry, the effective-theme resolver, the precedence order and the Settings editor. This phase adds a calendar-sourced input consulted at the same seam.

**What this phase is NOT.** It is not a calendar-driven view: the frame does not announce "K is flying now". It is not a general calendar integration (no OAuth, no provider APIs — one iCal feed). It does not name a person anywhere in the design. It changes nothing about how the panel is composed, and does not touch `server/plane/render.py`.

</domain>

<measured_findings>
## Measured before promotion — do not re-derive, do not plan against the seed where it disagrees

These three came from a real supplied `CrewWebPlus` iCal export and real production detections. They are load-bearing.

1. **The export is fully structured.** `SUMMARY:TO7061 MPL-ORY(+0200)` parses as `{flight number} {origin}-{destination}({utc offset})` on 15/15 flight events. `CATEGORIES:FLT` separates flights from `OFFD`/`CAHC`/`CPBL`; `DTSTART`/`DTEND` are UTC block times. Two junk events carry `STATUS:CANCELLED` with an 1899 placeholder date and must be filtered. The seed's fear that a duty event might carry only an internal code does not apply to this exporter.

2. **The flight number cannot be the match key.** The calendar says `TO7061`; the frame detects the same MPL-ORY service as `TO41XX`. Over 300 real cached flights, only 26% carry a commercial-looking IATA number, and **11% of Transavia France ones** — the dominant Orly carrier and this calendar's owner's employer. Meanwhile `origin_iata`/`destination_iata` are populated on **100%** of enriched detections. A same-route collision resolves by time: the two daily NCE-ORY rotations sit at ~06:55Z and ~15:15Z. Incidental discovery worth keeping: these "rotating" callsigns are **stable per scheduled rotation across days**.

3. **The cap on what this can promise.** The frame shows one aircraft at a time and misses most movements. On the owner's only Orly duty day inside recorded history, **none of her three flights were among 201 detections** — the 10:45Z arrival was missed while the frame tracked other aircraft in the same minute. The developer chose this design in full knowledge of that, over a calendar-driven view that would not depend on detection. **Copy, naming and empty states must not overstate it.**

</measured_findings>

<decisions>
## Implementation Decisions

### Where a calendar match lands — the phase's structural decision

- **D-01:** **A separate calendar registry, consulted at the same seam as the manual rules — never written into Phase 15's rule store.** Chosen over writing real rules into the existing registry, and over resolving against the cached calendar with no stored intermediate.

  *Why it matters.* Phase 15's registry means "what the operator typed". Keeping it that way buys three things at once: an automatic source can never overwrite or delete a hand-written rule; expiry becomes "replace a file" rather than "identify and delete other people's entries"; and the Settings editor does not fill with entries the operator did not create. Phase 15's D-02 deliberately reserved no field for this, so the record shape is this phase's to define.

  Rejected: **writing into Phase 15's registry** — nothing new in the resolver, and the entries would be visible and deletable in the existing editor, but it makes one store shared between a human and an automaton, where a colliding key silently replaces a manual rule. Rejected: **no storage, resolve straight off the cached feed** — nothing to expire, but nothing is inspectable either, so the operator cannot see why a flight was coloured.

- **D-02:** **The calendar wins over a manual rule.** A calendar match designates one specific flight on one specific date; a manual rule may cover a whole carrier, and the point of the feature is that these flights stand out.

  **Consequence the developer accepted explicitly:** this also beats a hand-typed *exact-callsign* rule, which is the narrowest thing the operator can write. Someone who deliberately pins one callsign will find a calendar match overriding it. This was raised at decision time and chosen anyway. The resolver's order therefore becomes: calendar match → manual rule (callsign > hex > prefix) → arrivals override → base theme.

- **D-03:** **The registry holds a short rolling window — today plus the next 24 to 48 hours — rewritten whole on every fetch.** Exact width is Claude's discretion.

  Expiry is then a property of the write, not a cleanup job: a past flight cannot colour a present one because it is no longer in the file. It also keeps the privacy footprint minimal, which matters because this file holds a named person's work schedule on a VPS. Rejected: **mirroring the whole feed** — simpler to write and a truer mirror, but it persists that schedule indefinitely, which is what the privacy note exists to limit.

- **D-04 (derived):** **Matching is on airline + the far-end airport + a time window, never the flight number** — the direct consequence of finding 2. The far end is the destination for a departure and the origin for an arrival, both of which the enriched route carries. Matching therefore runs **after** `enrich.resolve_route()`, never on the raw callsign.

### Claude's Discretion

The developer selected only the registry area and left the rest to me. Recorded here so the planner treats these as reasoned defaults, not gaps:

- **Time-window width and ambiguity.** Recommendation: a window generous enough to absorb ordinary delay, and on two candidates matching one calendar entry, take the closest in time rather than colouring both or neither. A flight is one aircraft; colouring two would be visibly wrong.
- **Configuration surface.** The URL is an environment variable in `skypane.env`, entered over SSH — so Settings shows "configured / not configured", never the value, plus the theme picker for calendar matches. Whether to add a connection test or a preview of upcoming parsed flights is a plan-time call; a preview is attractive but renders a person's schedule into a web page, so it needs a deliberate decision rather than a reflex.
- **Fetch cadence and failure.** The server has no long-running process — `deploy/skypane-poll.timer` fires a 30-second oneshot — so a throttled fetch inside that oneshot, persisting to `state_dir`, is the expected shape. It must never delay a render on a slow upstream. A feed that has been unreachable for a long time should degrade to "no matches" silently on the panel; whether the companion surfaces staleness is a plan-time call.
- Field and file names, the record shape, the parser's module placement, all copy, and test strategy.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### This phase's own framing
- `.planning/ROADMAP.md` §"Phase 16" — the three measured findings in full, the expected surface, and the security and privacy framing
- `.planning/seeds/SEED-003-theme-direction-scope-color-rules-calendar-highlighting.md` — the origin; its "Fully promoted 2026-09-07" addendum records that the ROADMAP entry is authoritative wherever the seed's older text disagrees

### The mechanism this phase feeds
- `.planning/phases/15-per-direction-themes-per-flight-colour-rules-and-roster-link/15-CONTEXT.md` — D-07 (rules resolve to registered theme ids, which is why this phase's on-glass footprint is zero), D-09 (the manual precedence order this phase prepends to), D-12 (the `state_dir` registry file contract to copy), D-13 (the resolver and its both-branches invariant)
- `server/plane/colour_rules.py` — the shipped registry and resolver. The leaf-import rule applies to any sibling this phase adds
- `.planning/phases/15-.../15-SECURITY.md` — the threat register this phase extends; `T-15-01`'s allowlist discipline applies to anything parsed out of a feed

### Prior art for the parts that are new
- `server/plane/manual_resolutions.py` — the never-raising load, tmp-write-then-`os.replace()`, write-lock file contract
- `companion/auth.py` — `PASSWORD_ENV_VAR`, the only existing secret-handling precedent, and the model for the calendar URL
- `.planning/seeds/aerodatabox-destination-lookup-rotating-callsigns.md` — the rotating-callsign problem this phase measured and worked around

### Sample data
- A real `CrewWebPlus` export was analysed at discuss time. **It is deliberately not committed** — it is a named person's work schedule. A redacted fixture preserving only the structure is expected at plan time.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server/plane/colour_rules.py` — registry contract, resolver, precedence order; the seam this phase extends
- `server/plane/enrich.py` — `resolve_route()` yields `origin_iata`/`destination_iata`, the actual match key
- `server/poll_loop.py` — the once-per-cycle config and registry read, and the two flight-displaying render branches
- `companion/auth.py` — environment-variable secret handling
- `companion/pages/config_page.py` — the Settings group idiom and theme `<select>`

### Established Patterns
- Never-raising loaders, positive allowlists applied at write and on read, tmp-write then `os.replace()`
- The poll oneshot must never be delayed by network work it does not need
- Locked-English copy as module constants; stdlib only, no new dependencies

### Integration Points
- The resolver's precedence chain gains a first step ahead of the manual rules (D-02)
- A new fetch/parse step inside the poll oneshot, throttled and persisted
- Settings gains a calendar group showing configured state plus a theme picker

</code_context>

<specifics>
## Specific Ideas

- The developer chose "connect your calendar" over a person-named feature. Nothing in the design should name an individual.
- They chose the calendar to win over manual rules knowing it overrides even an exact-callsign pin, because the purpose is that these flights stand out.
- They accepted a feature that will fire rarely, over a calendar-driven view that would fire every time. That trade is settled; do not reopen it, and do not compensate for it with copy that implies more than the frame can see.

</specifics>

<deferred>
## Deferred Ideas

- **A calendar-driven view** — the frame announcing the flight whether or not ADS-B detects it. Offered at discuss time and explicitly not chosen. It remains the design that would actually deliver "know when they are flying", and is worth its own phase if the rarity of matches proves disappointing in use.
- **Multiple calendars, or per-calendar themes.** Out of scope; one feed, one theme.
- **A visible trace that a calendar match fired** — carried over unselected from Phase 15's own deferred list, and more tempting here given how rarely this will trigger. Not in scope.
- **Registration (tail number) matching** — still out, still needs `detect._normalise_selection()` to carry the aggregators' `r` field.

### Reviewed Todos (not folded)
None — `todo.match-phase 16` returned zero matches.

</deferred>

---

*Phase: 16-calendar-linked-flight-highlighting-a-connected-calendar-sou*
*Context gathered: 2026-09-07*
