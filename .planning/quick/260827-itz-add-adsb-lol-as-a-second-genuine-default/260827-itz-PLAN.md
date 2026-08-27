---
phase: 05-low-battery-indicator
plan: 260827-itz
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - server/plane/detect.py
  - server/test_plane_detection.py
  - server/poll_loop.py
  - README.md
  - ARCHITECTURE.md
  - COMPLIANCE.md
  - .planning/PROJECT.md
  - .planning/REQUIREMENTS.md
autonomous: true
requirements: [PLANE-03]

must_haves:
  truths:
    - "A default poll — `detect.poll_current_aircraft(geofence)` with no providers argument, which is exactly how `server/poll_loop.py` calls it in production — queries two aggregators: adsb.fi first, then adsb.lol. It never reaches api.airplanes.live."
    - "adsb.lol's aircraft array is read from its own JSON key, which is not the key adsb.fi uses. A fixture-driven check proves the right key is read, because reading the wrong one would silently yield an empty aircraft list on every poll with no error, no log line, and no test failure — leaving cross-validation permanently dormant while appearing to work."
    - "The three cross-validation outcomes the runway3-false-positive fix built — two sources agreeing, two sources naming different aircraft, and one source unreachable — all still behave as designed when reached through the new two-provider default order, not only through an explicit providers argument."
    - "When both default sources agree, the record returned is adsb.fi's, because adsb.fi is first in the order — provider ordering is a load-bearing semantic, not cosmetic."
    - "An adsb.lol outage, block, or future API-key requirement degrades the poll to single-source (uncorroborated) rather than suppressing the display, and airplanes.live stays out of the default order while remaining selectable."
    - "COMPLIANCE.md carries an adsb.lol entry with the same rigour as the four existing entries, and states plainly that adsb.lol's own upstream documentation pre-announces a possible future feeder-contributed API key — the same volunteer-sustainability risk class that removed airplanes.live — so this is recorded as a known-temporary second source, not a permanent guarantee."
    - "Every document describing current runtime behaviour (README.md, ARCHITECTURE.md, COMPLIANCE.md, PROJECT.md, REQUIREMENTS.md) describes a two-source default poll. No document is left asserting that one aggregator is the only source an automated poll queries."
    - "The full suite, ruff, and the attribution check all pass, and README's stated total check count equals the real sum across every harness."
  artifacts:
    - server/plane/detect.py
    - server/test_plane_detection.py
    - server/poll_loop.py
    - COMPLIANCE.md
    - README.md
    - ARCHITECTURE.md
    - .planning/PROJECT.md
    - .planning/REQUIREMENTS.md
  key_links:
    - "`server/poll_loop.py`'s `run_once()` calls `detect.poll_current_aircraft(geofence_data)` with no providers argument. `DEFAULT_PROVIDER_ORDER` is therefore the only thing production reads. Adding an entry to `PROVIDERS` without extending `DEFAULT_PROVIDER_ORDER` changes nothing in production and makes every documentation claim in Tasks 2 and 3 false."
    - "`query_provider()` reads the aircraft array via `PROVIDERS[name]['aircraft_key']`. adsb.fi and adsb.lol do NOT use the same key. A wrong key here fails silently and totally: `data.get(key) or []` returns an empty list, `select_runway3_aircraft([])` returns None, the provider is scored as 'saw nothing on runway 3', and `corroborated` stays None forever — the exact symptom this whole task exists to fix, reproduced by the fix itself. Task 1's transport-level check is the only thing standing between that outcome and a green suite."
    - "`poll_current_aircraft()` sleeps `MIN_SECONDS_BETWEEN_CALLS` before every call after the first. That sleep now runs on every production cycle. Any harness check that exercises the two-provider default order must zero it in a try/finally, or the suite silently gains wall-clock time per check."
    - "`poll_current_aircraft()` returns `selections[0][1]` — the FIRST queried provider's record — when sources agree. Ordering adsb.fi first is what keeps the returned altitude/track/position fields coming from the longer-standing source."
    - "Provider disagreement returns None, which D-04 defines as 'leave the panel alone'. Until now that branch was unreachable in production. It is reachable from the moment this plan ships, so the disagreement rate becomes an operational property that must be observable in the journal and watched after deploy."
    - "COMPLIANCE.md's adsb.fi citation blockquote and README.md's Data sources citation sentence are the same sentence deliberately mirrored in two places, and COMPLIANCE.md says so in its own text. Both are edited by this plan and must still match each other afterwards."
---

<objective>
The runway3-false-positive debug session built per-poll cross-source validation into `poll_current_aircraft()`: query every provider, compare their independent selections, and treat disagreement as doubt. That mechanism has never run in production. `DEFAULT_PROVIDER_ORDER` has exactly one entry, so every production poll takes the single-source branch and reports `corroborated=None` unconditionally. The session's own resolved write-up names this as the remaining gap: "there is currently no second *live* default ADS-B source at all for the new cross-validation path to corroborate against."

This plan closes that gap by registering adsb.lol as a second provider and putting it in the default order behind adsb.fi. Nothing about geofencing, the runway corridor, the track-alignment gate, or the selection rule is touched — this is the fuel the already-built engine has been missing.

Purpose: make a production poll genuinely capable of corroborating or contradicting a runway-3 selection, so a single feed being confidently wrong is detectable rather than invisible.
Output: a two-entry default provider order in `server/plane/detect.py`, four new regression checks pinning both the new provider's response-key contract and all three cross-validation outcomes through the default path, journal-visible corroboration, and a COMPLIANCE.md entry that is honest about adsb.lol's disclosed sustainability caveat.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/debug/resolved/runway3-false-positive.md
@server/plane/detect.py
@server/test_plane_detection.py
@COMPLIANCE.md
@README.md
</context>

<research_already_done>
**The research is complete. Do not re-open it, do not re-evaluate alternatives, do not go looking for a different second source.**

Established facts, verified live on 2026-08-27:

- **Endpoint:** `https://api.adsb.lol/v2/point/{lat}/{lon}/{dist}` — the same path shape airplanes.live used, and the same three substitution placeholders `query_provider()` already formats.
- **Response key:** adsb.lol returns its aircraft array under the key `ac`. This is **not** the key adsb.fi uses (`aircraft`). Confirmed live. Getting this wrong is the single highest-consequence error available in this task — see `must_haves.key_links`.
- **Licence:** CC0, per adsb.lol's own licence/privacy page, verified 2026-08-27. No attribution is contractually required (unlike adsb.fi, whose terms do require a citation and a link). Crediting adsb.lol anyway is a house-style consistency choice, not a legal obligation — say so in COMPLIANCE.md rather than inventing a requirement.
- **Auth:** no API key is required today. **But adsb.lol's own upstream README pre-announces that a feeder-contributed API key may be required in future.** This is disclosed, not speculative, and it is the same volunteer-funding pressure that closed airplanes.live's free tier on the very day this project switched away from it.
- **Rejected and settled, do not revisit:** OpenSky Network (its Terms of Use exclude this automated-polling use case, independent of whether the data would fit) and ADS-B Exchange (no free tier remains).
</research_already_done>

<ground_truth_corrections>
Three things the executor must get right, because the obvious assumption about each is wrong:

1. **README's stated check total is ALREADY stale, before this plan changes anything.** README's Tests section states a number that is supposed to equal the sum of `EXPECTED_CHECK_COUNT` across all nine harnesses. That sum is currently 167; README says 119. The gap predates this task — it is a merge artifact from reconciling this branch with origin/main, where two harnesses grew substantially. **Compute the real sum from the files and write that.** Do not take the number in README and add the count of checks you added.

2. **The three existing cross-source checks pass an explicit `providers=["airplaneslive", "adsbfi"]` argument.** They were deliberately rewritten that way during the branch merge, precisely because a bare call reached only one provider and no longer exercised the comparison path. Leave those three checks exactly as they are — they still cover the explicit-argument path. The new checks are additions that reach the same code through the default order, which is what production actually uses.

3. **The provider that answers first is the one whose record is returned.** `poll_current_aircraft()` returns `selections[0][1]` on agreement. So the ordering decision (adsb.fi first) determines which source's altitude, track, and position values reach the renderer when both agree. Do not describe the ordering as arbitrary or cosmetic in any comment or document.
</ground_truth_corrections>

<scope_boundary>
**In scope** — the eight files in `files_modified`, and nothing else.

**Explicitly out of scope, do not edit:**

| File / area | Why it stays as-is |
|---|---|
| `filter_in_geofence()`, `runway_axis()`, `along_cross_track_m()`, `track_axis_deviation_deg()`, `corridor_params()`, `select_runway3_aircraft()` | The runway3-false-positive geometry fix, shipped and separately verified against a 60-poll real-data replay. This plan adds a data source; it does not touch how a source's records are judged. A diff that reaches into any of these functions is a defect in this plan's execution. |
| `adsb-test/runway3.json` | The geofence and its corridor derivation. Unchanged by adding a provider. |
| `adsb-test/query_aggregator.py`, `adsb-test/RESULTS.md`, `adsb-test/README.md` | A frozen Phase 1 spike and its measurement record. It has its own provider table; leave it alone. Rewriting a record of what was measured in August to match a decision made later is falsification. |
| `server/fixtures/` | No new fixture file is needed. Every new check builds its records inline from the two already-committed real captures, which is the convention checks 9, 10 and 23 already follow. |
| `airplaneslive`'s entry in `PROVIDERS` | Stays registered and stays out of the default order. Confirmed dead (HTTP 403); it remains reachable only by explicit request, for a feeder operator, sponsor, or licensee. |
| The production VPS | This plan changes repository contents only. Deployment happens through the existing CI/CD pipeline on merge. |

**Deliberate, named extensions beyond the narrowest possible diff** — each is a consistency obligation created by the change itself, not new scope:

- `server/poll_loop.py` gains one field in its existing log line. Without it, the corroboration outcome this plan enables is invisible in the journal, and the disagreement branch — newly reachable in production — cannot be observed at all. Two lines; no logic change. There is precedent: `aircraft_type` was added to this same line the same way.
- The `--provider` CLI argument's default and choice names. Its help text currently asserts that one provider is the default and that every other choice is an explicit opt-in. That assertion becomes false the moment the default order gains a second entry, and one choice name literally counts the providers it selects, which is no longer correct with three registered. Leaving either stale ships a CLI that lies about what it does.
- `ARCHITECTURE.md`, `.planning/PROJECT.md`, `.planning/REQUIREMENTS.md`. Each carries a current-state claim that exactly one aggregator is queried. This project's established discipline (see the previous quick task in this same area) is to correct current-state claims in place with a dated note and to leave historical records untouched. Follow it.
</scope_boundary>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Register adsb.lol as the second default provider, pinned by transport-level and cross-validation regression checks</name>
  <files>server/plane/detect.py, server/test_plane_detection.py, README.md</files>
  <behavior>
    Changes to `server/test_plane_detection.py`, following that harness's exact `check(name, fn)` / `(ok, reason)` convention and its stdlib-only rule:

    **Check 20 — updated in place, not replaced.** It currently monkeypatches `detect.query_provider` with a recorder and asserts a default poll records exactly one provider name. It must now assert the recorded list equals adsb.fi followed by adsb.lol, in that order, and its name and comment must describe the two-source default. Its own try/finally must additionally save, zero, and restore `detect.MIN_SECONDS_BETWEEN_CALLS` — `poll_current_aircraft()` sleeps that interval before every call after the first, and the shared stubbing helper that normally zeroes it is defined further down the file and is not in scope at this point in execution. Check 21 (airplanes.live registered but absent from the default order) is unchanged and must still pass untouched.

    **Check 25 — the default order corroborates.** Using the existing `_with_stubbed_providers` helper with responses keyed for both default providers, call `poll_current_aircraft(geofence)` with NO providers argument. Both providers return the real runway-3 arrival record, but adsb.lol's copy carries a different barometric altitude (still on the runway and still below the ceiling, so it remains a legitimate selection). Assert: a selection is returned; its hex is the arrival's; `corroborated` is True; the sorted source list names both default providers; and the returned altitude field equals adsb.fi's value, not adsb.lol's — proving the first-listed provider's record is the one returned.

    **Check 26 — the default order suppresses on disagreement.** Same helper, no providers argument. adsb.fi returns the real arrival; adsb.lol returns a copy relocated to the runway's other published threshold with a matching along-axis track and a different hex, built exactly the way check 23 builds its stand-in. First assert the stand-in is itself independently selectable (so the disagreement is about which aircraft, not about the gate rejecting one). Then assert the poll returns None.

    **Check 27 — the default order degrades to single-source.** Same helper, no providers argument. adsb.fi returns the real arrival; adsb.lol's response is a `requests.RequestException`, standing in for the outage, block, or future key requirement adsb.lol's own documentation warns about. Assert: the arrival is still returned, `corroborated` is None, and the source list names adsb.fi alone. This is the check that proves a second source cannot take the display down.

    **Check 28 — the response-key contract, proven through the transport.** Do not assert the dict value; assert the behaviour. Temporarily replace `detect.requests.get` with a stub returning a minimal fake response object exposing a no-op `raise_for_status()` and a `json()` that returns a payload carrying BOTH candidate array keys, each holding a different, distinguishable aircraft record. Restore it in a finally. Call `detect.query_provider` for adsb.lol and assert it returns the record under adsb.lol's key; call it for adsb.fi and assert it returns the record under adsb.fi's key. Also capture the URL the stub was called with and assert it is the adsb.lol host with the supplied latitude, longitude and distance substituted in. This check fails loudly if the two providers' keys are ever confused, which is the one failure mode that is otherwise completely silent.

    Raise `EXPECTED_CHECK_COUNT` from 24 to 28 and extend the module docstring's check-range map to name the new block.
  </behavior>
  <action>
Edit `server/plane/detect.py`:

1. Add a third entry to the `PROVIDERS` dict, keyed `adsblol`, placed after `adsbfi` and before `airplaneslive`. Its `url_template` and `aircraft_key` are the endpoint and response key stated verbatim in `<research_already_done>`. Copy the response key from that section character by character; do not infer it from the neighbouring adsb.fi entry, which uses a different key.

2. Change `DEFAULT_PROVIDER_ORDER` to a two-element tuple: adsb.fi first, adsb.lol second.

3. Extend the block comment above `PROVIDERS`. Keep everything it already records about the 2026-08-27 airplanes.live withdrawal — that history is still true and still explains why airplanes.live sits outside the default order. Append a dated paragraph recording, in this order:
   - adsb.lol added the same day as a second default source, live-verified, CC0-licensed, no API key required today;
   - that its aircraft array arrives under a different key than adsb.fi's, naming both keys against their providers, because that mismatch is the one silent failure mode in this file;
   - that adsb.lol's own upstream documentation pre-announces a possible future feeder-contributed API key, which places it in the same volunteer-sustainability risk class as the provider that just withdrew — so it is a known-temporary second source, not a permanent guarantee;
   - that the point of a second default entry is that `poll_current_aircraft()`'s cross-validation now actually runs on every production poll instead of always taking the single-source branch;
   - that ordering is load-bearing per `<ground_truth_corrections>` item 3.
   Do not write a fenced code block or a sample payload into this comment.

4. Update `poll_current_aircraft()`'s docstring. Its closing paragraph currently states that the default order has exactly one entry, that a default poll never has a second selection to cross-validate against, that corroboration is always absent in production, and that the comparison path is reachable only through an explicit argument or a test double. Every one of those sentences is false after step 2 — rewrite that paragraph to describe the two-source default and what each of the three outcomes now means for a real poll cycle. Leave the three-outcome table and the reasoning about why disagreement returns nothing exactly as written; only the "today" paragraph is stale. Also update the docstring's opening sentence, which parenthesises the default order as a single named provider.

5. Update the module docstring's usage examples so the illustrated invocation matches the argument spelling after step 6.

6. In `build_parser()`, make the CLI mirror production instead of contradicting it:
   - Add a choice meaning "whatever the production default order is", and make it the argument's default value. Add a separate choice meaning "every registered provider, including the opt-in one". Remove the existing choice whose name asserts a provider count, since three providers are now registered and that name is no longer true.
   - Rewrite the `help=` text: state that omitting the argument queries the production default order and names it, that a single provider name restricts the poll to that one source, and that the all-providers choice additionally reaches the opt-in provider, which is expected to fail for anyone without feeder, sponsor, or licensee access.

7. In `main()`, resolve the new choices: the production-default choice yields no explicit providers argument at all (so `poll_current_aircraft()` reads its own default order and there is exactly one definition of that order in the codebase); the all-providers choice yields every registered provider name in registration order; any single provider name yields a one-element list. Change nothing else in `main()` — the output line already prints the source list and corroboration flag.

Then edit `server/test_plane_detection.py` exactly as `<behavior>` specifies.

Then edit `README.md`'s Tests section: it states a harness count and a total check count. The harness count is unchanged. Recompute the total as the sum of every `EXPECTED_CHECK_COUNT` across `server/test_*.py` and `stub-server/test_*.py` and write that number, heeding `<ground_truth_corrections>` item 1 — the current number is stale for a reason that has nothing to do with this task. Change nothing else in that section.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
import server.plane.detect as d
assert d.DEFAULT_PROVIDER_ORDER == ('adsbfi', 'adsblol'), d.DEFAULT_PROVIDER_ORDER
assert set(d.PROVIDERS) == {'adsbfi', 'adsblol', 'airplaneslive'}, sorted(d.PROVIDERS)
assert 'airplaneslive' not in d.DEFAULT_PROVIDER_ORDER
lol = d.PROVIDERS['adsblol']
assert lol['aircraft_key'] == 'ac', lol['aircraft_key']
assert lol['aircraft_key'] != d.PROVIDERS['adsbfi']['aircraft_key'], 'the two default providers must not share a response key'
assert lol['url_template'] == 'https://api.adsb.lol/v2/point/{lat}/{lon}/{dist}', lol['url_template']
assert lol['url_template'].format(lat=1, lon=2, dist=3).endswith('/1/2/3')
print('detect.py provider registry OK')"</automated>
    <automated>server/.venv/bin/python3 -c "
import sys; sys.path.insert(0, '.')
import server.plane.detect as d
parser = d.build_parser()
ns = parser.parse_args([])
action = next(a for a in parser._actions if '--provider' in a.option_strings)
choices = set(action.choices or [])
assert set(d.PROVIDERS) <= choices, choices
assert len(choices) == len(d.PROVIDERS) + 2, choices
assert ns.provider in choices and ns.provider not in d.PROVIDERS, ns.provider
print('CLI mirrors the production default order:', ns.provider)"</automated>
    <automated>server/.venv/bin/python3 server/test_plane_detection.py</automated>
    <automated>server/.venv/bin/python3 -c "
import glob, pathlib, re
tot = sum(int(re.search(r'EXPECTED_CHECK_COUNT = (\d+)', pathlib.Path(p).read_text()).group(1)) for p in sorted(glob.glob('server/test_*.py') + glob.glob('stub-server/test_*.py')))
assert ('%d checks total' % tot) in pathlib.Path('README.md').read_text(), 'README check count is stale; harnesses now sum to %d' % tot
print('README check count matches harnesses:', tot)"</automated>
    <automated>test "$(git diff --numstat -- adsb-test/ server/fixtures/ | wc -l | tr -d ' ')" = "0" && echo "geofence, spike and fixtures untouched"</automated>
    <automated>./scripts/run-all-tests.sh</automated>
    <automated>server/.venv/bin/python3 -m ruff check .</automated>
  </verify>
  <done>`detect.PROVIDERS` holds three entries with adsb.lol's own response key, distinct from adsb.fi's; `DEFAULT_PROVIDER_ORDER` names adsb.fi then adsb.lol; the CLI's default resolves to that same order with no second definition of it; `server/test_plane_detection.py` reports 28/28 including a transport-level check that the two default providers' response keys are not interchanged and three checks covering agreement, disagreement and single-source degradation through the default path; nothing under `adsb-test/` or `server/fixtures/` is modified; `./scripts/run-all-tests.sh` and `ruff check .` both exit 0 and README's stated check total equals the computed sum.</done>
</task>

<task type="auto">
  <name>Task 2: Make corroboration observable in the journal and correct ARCHITECTURE.md</name>
  <files>server/poll_loop.py, ARCHITECTURE.md</files>
  <action>
Edit `server/poll_loop.py`:

1. In `run_once()`'s single `print(...)` log line, add one field carrying the selection's corroboration flag, placed immediately after the existing aircraft-type field. Read it defensively from the same `(flight or {}).get(...)` pattern every neighbouring field already uses, so a None flight and a selection that predates this key both log cleanly rather than raising. Extend the format string and its argument tuple together; do not restructure the call or reorder the existing fields, and do not add a second print statement.

2. Adjust the comment directly above that print. It currently enumerates what the line is permitted to log and why. The corroboration flag is a three-state provenance signal about this project's own sources — not third-party response content — so it is within that comment's stated rule; say so in one clause rather than rewriting the comment.

3. `_extract_aircraft()`'s docstring maps response keys to the providers that use them and names only two providers. Add the new provider to whichever key it shares, so the mapping stays complete. Do not change the function's behaviour — it already accepts both keys.

Edit `ARCHITECTURE.md`:

4. The end-to-end ASCII data-flow diagram's top-left box carries two label lines naming the aggregators and their roles. Relabel so both default sources are named as queried, with the opt-in provider still marked as not automatically reached. **Preserve the box's column width and alignment** — the vertical bar and arrow characters on the lines below must still line up under it. If the honest label does not fit the existing width, widen the whole box consistently rather than letting the alignment drift.

5. The Detection paragraph names the single aggregator queried and asserts that nothing takes over when that source fails. Rewrite it to describe what the code now does: a poll queries both default sources in order and compares their independent selections; agreement returns a corroborated selection; one source unreachable returns the other's selection flagged as uncorroborated, which is why an outage at either source does not blank the display; two sources naming different aircraft returns nothing, which the pipeline already treats as the between-flights hold rather than an error. State that the ordering determines which source's record is returned on agreement. Leave the rest of that paragraph — including the `select_runway3_aircraft()` total-order description and everything about the corridor and track gates — untouched.

6. Anywhere else in this file that asserts a single-source poll or an absent fallback, correct it in the same pass. Do not restate the corridor/track-gate description; that content is correct and out of scope.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import sys, io, os, json, tempfile, contextlib; sys.path.insert(0, '.')
import server.poll_loop as pl
snap = json.load(open('server/fixtures/geofence_multi_aircraft.json'))
with tempfile.TemporaryDirectory() as d:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        pl.run_once(state_dir=os.path.join(d, 'state'), snapshot=snap)
    line = [l for l in buf.getvalue().splitlines() if l.startswith('poll_loop: ')][-1]
assert 'corroborated=' in line, line
assert 'callsign=' in line and 'aircraft_type=' in line and 'panel_changed=' in line, line
print(line)"</automated>
    <automated>server/.venv/bin/python3 -c "
import pathlib
a = pathlib.Path('ARCHITECTURE.md').read_text()
assert 'adsb.lol' in a, 'ARCHITECTURE.md never names the second default source'
assert 'adsb.fi' in a
assert 'no automatic fallback provider' not in a, 'ARCHITECTURE.md still asserts nothing takes over on failure'
assert 'sole default' not in a, 'ARCHITECTURE.md still describes a single default provider'
# The edited aggregator label sits above the first box, and the connector
# glyphs beneath it must stay in the same columns on every line of that run.
block = next(b for b in a.split('\`\`\`') if '┌' in b).splitlines()
top = next(i for i, l in enumerate(block) if l.lstrip().startswith('┌'))
cols = [tuple(j for j, ch in enumerate(l) if ch in '│▼') for l in block[:top] if ('│' in l or '▼' in l)]
assert cols, 'the aggregator connector lines vanished from the diagram'
assert len(set(cols)) == 1, 'diagram connector columns drifted: %r' % (cols,)
# The right-hand column starts at 41; the left label must keep its gutter.
for l in block[:top]:
    assert len(l) <= 41 or l[38:41] == '   ', 'left label collided with the right column: %r' % (l,)
print('ARCHITECTURE.md OK, connector columns aligned at', cols[0])"</automated>
    <automated>./scripts/run-all-tests.sh</automated>
    <automated>server/.venv/bin/python3 -m ruff check .</automated>
  </verify>
  <done>A real fixture-driven poll cycle logs a corroboration field in the existing single log line, alongside every field it already carried; `_extract_aircraft()`'s key-to-provider mapping names all three providers; ARCHITECTURE.md's diagram names both default sources with its box borders still equal width and its connector characters still aligned, and its Detection paragraph describes the two-source comparison, the ordering semantic, and all three outcomes including which one leaves the panel alone; the full suite and ruff still pass.</done>
</task>

<task type="auto">
  <name>Task 3: Add the adsb.lol compliance entry and reconcile every document that still describes a single-source poll</name>
  <files>COMPLIANCE.md, README.md, .planning/PROJECT.md, .planning/REQUIREMENTS.md</files>
  <action>
Edit `COMPLIANCE.md`:

1. **New adsb.lol entry**, placed directly after the adsb.fi entry so the two default sources sit together, and built from exactly the same field shape the four existing entries use — used in shipped code, upstream, terms checked (with the date), what the terms require, request pattern where relevant, verdict, status. It must record:
   - that it is queried by every automated poll as the second default source, naming `server/plane/detect.py`, the provider key, and the endpoint template, the way the adsb.fi entry names its own;
   - the upstream link, and the date its licence and terms were checked;
   - that the licence is CC0 and therefore imposes no attribution obligation — and that this project credits it in README.md anyway as a consistency choice, stated plainly as a choice rather than as a requirement, so a later reader does not mistake a courtesy for a term;
   - that no API key is required today, **and** that adsb.lol's own upstream documentation pre-announces a possible future feeder-contributed key requirement. Give this its own sentence and do not soften it: this is the same volunteer-funding pressure that closed airplanes.live's free tier, and the airplanes.live entry sitting a few lines below is the worked example of what happens when it arrives.
   - the resulting verdict: adsb.lol is recorded as a **known-temporary** second source rather than a permanent guarantee, and the code already degrades to single-source rather than blanking if it starts refusing — name the check number from Task 1 that proves that degradation, so the claim is machine-backed rather than asserted.
   - a status line, in the same voice the other entries use.

2. **adsb.fi entry.** Its used-in-shipped-code line and its citation blockquote both describe adsb.fi as the only aggregator an automated poll queries. That is no longer true. Rewrite both so they describe adsb.fi as the first-queried of two default sources — the upstream requirement itself (cite adsb.fi, link to their home page) is unchanged and still met, so the citation must keep its live link and its citing sentence. Keep, and honour, this entry's own instruction that the same citation sentence is mirrored in README.md and that both must be edited together.

3. **Runtime behaviour section.** Its poll-cadence bullet states that a production cycle issues a single aggregator request. Rewrite it with the real numbers: two requests per 30-second cycle, separated by the module's inter-call sleep, which is what keeps the pair inside the 1 request/second limit both providers document. State the per-provider rate as well as the aggregate, since each provider only sees its own half.

4. **Status table and closing line.** Add an adsb.lol row matching the columns of the existing rows, update the adsb.fi row's role cell, and confirm the sentence beneath the table still reads correctly with a fifth source present. No row may be left marked as an outstanding item — adsb.lol's disclosed future-key caveat is a recorded risk in its entry, not an open action, and the closing sentence should not imply otherwise.

5. Anywhere in this file that spells out an explicit multi-provider CLI invocation, update it to the argument spelling Task 1 established.

Edit `README.md`'s Data sources section:

6. Name both default sources. The adsb.fi sentence must carry the identical citation text as COMPLIANCE.md's blockquote, with its live link intact, and must no longer describe adsb.fi as the only source an automated poll queries. Add adsb.lol with its own live link, one clause on why a second source exists (two independent feeds can corroborate or contradict a single reading, which one feed alone cannot), and one clause noting it is CC0 and credited by choice. Keep the airplanes.live paragraph, the adsbdb.com sentence, and the no-raw-data-is-republished paragraph, adjusting only what the added source makes inaccurate. Point at `COMPLIANCE.md` for the detail, as the section already does.

Edit `.planning/PROJECT.md`:

7. The plane-detection context bullet ends with a dated 2026-08-27 correction naming a single default provider. Append a further dated note in that same established style recording the addition of a second default source and pointing at Key Decisions. Do not delete or rewrite the existing correction — this file's convention is to layer dated notes, not to overwrite them.

8. Add one new row at the end of the Key Decisions table, in its existing three-column shape. Decision: adsb.lol registered as the second default ADS-B provider behind adsb.fi. Rationale: the runway3-false-positive fix built per-poll cross-source validation that could never run with one default source; adsb.lol is CC0, drop-in compatible with the existing provider abstraction, and live-verified — with the disclosed future-API-key caveat named honestly. Outcome: dated, stating the accepted tradeoffs — two requests per cycle instead of one, and a genuinely reachable disagreement branch that holds the panel rather than guessing. Leave the previous row, which records the single-default decision, exactly as written; append a short supersession pointer to its Outcome cell only, matching how the row above it was superseded.

Edit `.planning/REQUIREMENTS.md`:

9. The validated PLANE-03 line carries a parenthetical naming the aggregator actually queried. Update it to name both default sources. The requirement's substance is unchanged and stays validated.

10. The rejected-alternatives table has a row about a specific aggregator not chosen, whose text asserts which two aggregators are in production. Correct only that factual assertion to match reality; leave the row's rejection rationale intact. Leave the RTL-SDR row entirely alone — it is a historical record and asserts no ordering.
  </action>
  <verify>
    <automated>server/.venv/bin/python3 -c "
import pathlib
c = pathlib.Path('COMPLIANCE.md').read_text()
r = pathlib.Path('README.md').read_text()
for name, t in (('COMPLIANCE.md', c), ('README.md', r)):
    assert 'adsb.lol' in t, name + ' never names adsb.lol'
    assert 'https://adsb.fi' in t, name + ' lost the required adsb.fi link'
    assert 'sole aggregator source' not in t, name + ' still calls adsb.fi the only queried source'
assert c.count('## adsb.lol') == 1, 'expected exactly one adsb.lol compliance entry'
assert 'CC0' in c and 'CC0' in r, 'the CC0 licence is not recorded in both places'
assert 'api.adsb.lol' in c, 'COMPLIANCE.md does not name the endpoint actually called'
assert 'sole default provider' not in c, 'COMPLIANCE.md still describes a single default provider'
assert c.count('| adsb.lol |') == 1, 'adsb.lol missing from (or duplicated in) the status table'
print('COMPLIANCE.md and README.md OK')"</automated>
    <automated>server/.venv/bin/python3 -c "
import pathlib, re
c = pathlib.Path('COMPLIANCE.md').read_text()
# The adsb.fi citation blockquote and README's citation sentence are the same
# sentence mirrored in two places - prove they still match, not just coexist.
quote = [l.lstrip('> ').strip() for l in c.splitlines() if l.strip().startswith('>')]
quote = ' '.join(x for x in quote if x)
assert quote, 'the adsb.fi citation blockquote disappeared from COMPLIANCE.md'
norm = lambda s: re.sub(r'\s+', ' ', s).strip()
r = norm(pathlib.Path('README.md').read_text())
assert norm(quote) in r, 'README no longer carries COMPLIANCE.md citation text verbatim:\n  %s' % quote
print('citation mirrored verbatim in both files')"</automated>
    <automated>server/.venv/bin/python3 -c "
import pathlib
p = pathlib.Path('.planning/PROJECT.md').read_text()
head, sep, tail = p.partition('## Key Decisions')
assert sep, 'Key Decisions heading missing'
assert 'adsb.lol' in head, 'the context bullet was not given its dated note'
assert 'adsb.lol' in tail, 'no Key Decisions row records the second default source'
assert 'adsb.fi is now the sole default provider' in head, 'the earlier dated correction was overwritten instead of layered'
q = pathlib.Path('.planning/REQUIREMENTS.md').read_text()
assert 'PLANE-03' in q and 'adsb.lol' in q, 'PLANE-03 was not updated'
print('planning artifacts OK')"</automated>
    <automated>test "$(git diff --numstat -- adsb-test/ server/fixtures/ | wc -l | tr -d ' ')" = "0" && echo "historical spike records untouched"</automated>
    <automated>./scripts/check-attribution.sh</automated>
    <automated>./scripts/run-all-tests.sh</automated>
  </verify>
  <done>COMPLIANCE.md carries an adsb.lol entry in the same field shape as the other four, recording CC0, the checked date, the endpoint, the credit-by-choice distinction, and the disclosed future-API-key caveat with its known-temporary verdict backed by a named check; the adsb.fi entry and README's Data sources section both describe two default sources and still carry the identical, verbatim-matching citation with its live link; the runtime-behaviour bullet states two requests per cycle with the real per-provider and aggregate rates; the status table has a fifth row and no open item; PROJECT.md layers a new dated note plus a new Key Decisions row without overwriting the earlier ones; REQUIREMENTS.md's PLANE-03 and its rejected-alternatives assertion both name reality; the attribution check and the full suite pass.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| server → adsb.lol (`api.adsb.lol`) | **New.** Unauthenticated third-party HTTPS feed. Untrusted JSON crosses into the detection pipeline on every production poll. |
| server → adsb.fi (`opendata.adsb.fi`) | Existing unauthenticated third-party HTTPS feed, unchanged. |
| server → airplanes.live (`api.airplanes.live`) | Registered but unreachable from any automated code path. Unchanged by this plan. |
| detect.py → poll_loop.py → render.py | Internal. The selection dict gains no new field from this plan; `sources` and `corroborated` already exist and now carry meaningful values. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-itz-01 | Tampering | untrusted adsb.lol JSON → `filter_in_geofence()` / `select_runway3_aircraft()` | medium | mitigate | A second untrusted feed reaches the same normalization boundary. No new parsing path is introduced: adsb.lol is routed through the existing `query_provider()` and the existing geometry gate, which isinstance-check lat/lon and `alt_baro`, skip malformed records instead of raising, never claim below-ceiling on an unknown altitude, and validate the aircraft-type designator against `_VALID_AIRCRAFT_TYPE_RE`. Task 1 forbids touching any of those functions, so the boundary is inherited intact. Net effect is a security **improvement**: a single feed emitting a plausible-but-wrong record is now contradictable, which is exactly the failure mode the cross-validation was built for and has never been able to detect in production. |
| T-itz-02 | Denial of Service | `poll_current_aircraft()` disagreement branch | medium | mitigate | The disagreement branch returns None — D-04's "leave the panel alone" — and becomes reachable in production for the first time. Two feeds with different feeder coverage can legitimately select different aircraft in the same instant, so a sustained disagreement rate would freeze the display without any error surfacing. Mitigated by making the outcome observable: Task 2 logs the corroboration flag on every cycle and `detect.py` already writes the disagreement detail to stderr, which the journal captures. The post-deploy human check requires reading the real disagreement rate rather than assuming it is rare, and the rollback is a one-line revert of `DEFAULT_PROVIDER_ORDER` to a single entry with no other change. |
| T-itz-03 | Denial of Service | added upstream dependency in the poll path | low | accept | Each cycle now issues two outbound requests and sleeps the inter-call interval between them, inside a 30-second oneshot. Per-provider request rate is unchanged at one per cycle; the aggregate stays inside both providers' documented 1 request/second limit. An adsb.lol outage cannot take the display down — check 27 pins that a single reachable provider returns its selection uncorroborated rather than being scored as disagreement. |
| T-itz-04 | Repudiation | terms drift at a volunteer-funded free service | medium | mitigate | adsb.lol's own documentation pre-announces a possible future feeder-contributed API key. Continuing automated polls after such a requirement lands would be use outside the granted terms — precisely what happened with airplanes.live on 2026-08-27. Mitigated by recording the caveat explicitly in COMPLIANCE.md as a known-temporary verdict rather than a settled one (Task 3), and by the code degrading to single-source on a 401/403 instead of silently retrying into a block. Not mitigable further in code; the recorded caveat is what makes the next reader check before assuming. |
| T-itz-05 | Information Disclosure | outbound requests to a new third party | low | accept | The request discloses the geofence centre and radius — Orly airport, already public in `adsb-test/runway3.json` in a public repository — plus the project-identifying `USER_AGENT` constant, which is unchanged and names the project and points at `server/README.md`. No credential, token, home location, or device identifier is transmitted. No API key exists to leak. |
| T-itz-06 | Spoofing | provider response-key confusion | high | mitigate | Not an attacker-driven threat but the highest-consequence defect available here: adsb.fi and adsb.lol return their aircraft arrays under different keys, and `query_provider()`'s `data.get(key) or []` turns a wrong key into an empty list — no exception, no log line, no failing test. The provider would be scored as "saw nothing on runway 3" forever, corroboration would never occur, and the entire task would appear to have succeeded. Mitigated by Task 1's check 28, which proves the mapping through a stubbed transport against a payload carrying both keys with distinguishable records, and by the registry assertion that the two default providers' keys differ. |
| T-itz-SC | Tampering | npm/pip/cargo installs | n/a | accept | No package-manager install is performed and no dependency is added or changed by this plan — `requests` is already a pinned production dependency and the harness is stdlib-only. No package-legitimacy checkpoint applies. |
</threat_model>

<verification>
Run from the repository root after all three tasks:

1. `./scripts/run-all-tests.sh` exits 0 — 9 harnesses, `server/test_plane_detection.py` reporting 28/28, coverage above the `pyproject.toml` threshold.
2. `./scripts/check-attribution.sh` exits 0.
3. `server/.venv/bin/python3 -m ruff check .` exits 0.
4. `git diff --stat` lists exactly the eight files in `files_modified` and no others. In particular nothing under `adsb-test/` or `server/fixtures/`, and no hunk inside `filter_in_geofence`, `runway_axis`, `along_cross_track_m`, `track_axis_deviation_deg`, `corridor_params` or `select_runway3_aircraft`. Confirm the last point by reading `git diff server/plane/detect.py` rather than by trusting the file-level stat.
5. Best-effort live observation, **not a gate**: run `server/.venv/bin/python3 server/plane/detect.py` with no arguments and record the printed source list and corroboration flag in the SUMMARY. This environment's outbound network has been observed proxied/blocked before (a previous plan recorded a live aggregator call returning 403 from a sandboxed run), so a failure here is an environment fact to report, not a task failure — the fixture-driven checks are the binding evidence. If it does answer, note whether the two sources agreed, disagreed, or whether one was unreachable, and quote the exact line.

<human-check>
Two things only a human can settle, both after this reaches the VPS through the normal CI/CD path:

1. **Disagreement rate.** Watch `journalctl -u skypane-poll` across a stretch of real traffic and count how often the poll logs a corroborated selection, an uncorroborated one, and how often `detect.py` writes its providers-disagree line to stderr. The design assumption is that disagreement is rare and mostly reflects genuine ambiguity. If it turns out to be common, the display is being held far more often than before this change and the correct response is to revert `DEFAULT_PROVIDER_ORDER` to a single entry — everything else in this plan can stay. Record the observed counts in the SUMMARY; do not record an assumption in place of a count.

2. **The compliance caveat reads honestly.** Read the new adsb.lol entry in `COMPLIANCE.md` end to end and confirm it does not present adsb.lol as a settled permanent source. The disclosed possibility of a future feeder-contributed API key must be legible as a real risk of the same kind that removed airplanes.live, and the CC0 credit must read as a deliberate courtesy rather than an invented contractual requirement.
</human-check>
</verification>

<success_criteria>
- A production-shaped poll (`detect.poll_current_aircraft(geofence)`, no providers argument) queries adsb.fi and then adsb.lol, and never airplanes.live.
- adsb.lol's aircraft array is read under its own response key, proven through a stubbed transport against a payload carrying both candidate keys — not by asserting a dict literal.
- All three cross-validation outcomes behave correctly through the default order: agreement returns a corroborated selection carrying adsb.fi's record, disagreement returns nothing, and one unreachable source returns the other's selection flagged uncorroborated.
- `server/test_plane_detection.py` reports 28/28 and fails if the two default providers' response keys are ever interchanged, if airplanes.live is returned to the default order, or if the default order shrinks back to one entry.
- Every real poll cycle logs its corroboration outcome, so the newly reachable disagreement branch is observable in the journal rather than silent.
- Nothing in the runway-3 geometry gate, the geofence config, the Phase 1 spike, or the committed fixtures is modified.
- COMPLIANCE.md documents adsb.lol at the same rigour as the existing four sources, including the CC0-credit-by-choice distinction and the disclosed future-API-key caveat, with a known-temporary verdict.
- README.md, ARCHITECTURE.md, PROJECT.md and REQUIREMENTS.md all describe a two-source default poll; COMPLIANCE.md's citation blockquote and README's citation sentence still match each other verbatim.
- `./scripts/run-all-tests.sh`, `./scripts/check-attribution.sh` and `ruff check .` all pass, and README's stated total check count equals the real computed sum across all nine harnesses.
</success_criteria>

<output>
Create `.planning/quick/260827-itz-add-adsb-lol-as-a-second-genuine-default/260827-itz-SUMMARY.md` when done.
</output>
