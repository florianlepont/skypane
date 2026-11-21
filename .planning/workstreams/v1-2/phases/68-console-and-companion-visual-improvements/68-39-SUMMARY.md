---
phase: 68-console-and-companion-visual-improvements
plan: 39
subsystem: companion
tags: [airlines-editor, ai-suggestion, anthropic, messages-api, render-baseline]
key-files:
  created:
    - server/plane/airline_suggest.py
    - server/test_airline_suggest.py
    - test-support/fake_anthropic.py
    - companion/airline_suggest_actions.py
    - companion/static/airline-suggest.js
    - companion/test_airline_suggest_helpers.py
    - companion/test_airline_suggest_page.py
    - companion/test_airline_suggest_routes.py
    - companion/test_browser_airline_suggest.py
  modified:
    - companion/pages/airline_rows.py
    - companion/pages/airline_table.py
    - companion/pages/airlines_page.py
    - companion/static/style-airlines.css
    - companion/i18n_fr/airlines.py
    - companion/ui_base.py
    - companion/ui_modal.py
    - companion/post_actions.py
    - companion/routes.py
    - companion/static_files.py
    - companion/layout.py
    - companion/ui_shell.py
    - companion/app.py
    - companion/testdata/render_baseline.json
    - test-support/matrix_rows_admin_frame.py
    - test-support/companion_render_snapshot.py
    - deploy/README.md
    - deploy/skypane.env.example
    - COMPLIANCE.md
    - pyproject.toml
metrics:
  completed: 2026-11-21
---

# Phase 68 Plan 39: AI-suggested airline names (run 2, tasks 4 to 8)

Run 1 (tasks 1 to 3: mockup, owner approval, record) was done before. This run built the approved `68-MOCKUP-airline-suggest.html` (OWNER-APPROVED 2026-11-21: tag "Suggestion", errors and rate cap silent, reject only in the Edit dialog, 10 calls an hour and 60 a day, one request per prefix ever, `claude-haiku-5-5`, only the prefix and up to 4 sample callsigns sent, livery illustration deferred). It ran in one go; the build was not split.

## What was built

- **Service** (`server/plane/airline_suggest.py`, `requests` only, `server/requirements.txt` and `.in` untouched): `build_request` (model, `max_tokens` 120, `thinking` disabled, one `system` string, one user message holding only the prefix and the filtered samples, no sampling parameter, no prefill), `parse_response` (first text block, JSON object with `airline`, validated like manual naming plus no control characters or markup), persisted cache `airline_suggestions.json` in the state root (state, name, model, `asked_at`, `failed_until`; one request per prefix ever; `none`, `rejected`, `accepted`, `edited` are tombstones; failures 900 s, authentication class 6 h; 500 entries), rolling 10 per hour and 60 per day cap stored in the same file (the call is counted before it is made, under the lock, so concurrent requests cannot overshoot), one attempt with a 3.05 s connect and 8 s read timeout, no redirects, no proxy or netrc, reply capped at 64 KB, key only from the environment, failures become reason codes, one stderr line (`prefix`, reason, `request-id`), the lock is never held across the network call. The loopback-only `SKYPANE_ANTHROPIC_BASE_URL` seam ignores any other host.
- **Fake** (`test-support/fake_anthropic.py`): loopback `ThreadingHTTPServer` in the real success and error shapes, records requests, scripted answers, delay and concurrency counters.
- **Rows** (`airline_rows`, `airline_table`, `style-airlines.css`, FR strings): with a cached suggestion the unidentified row shows the Suggestion tag (new `icon-spark`), the proposed name in bold, the sightings line, an Edit link and the round 44 px check (a real form to `/airlines/resolve`, works without script); a never-asked prefix shows the pending "Looking for a name" tag plus Name it (at most 3 rows per page, `data-suggest-*` on the `<tbody>`); every other state (none, rejected, accepted, edited, failed, service off) is the unchanged Name it row. The page only reads the cache (`suggest_row_html` is the one definition of a row, also used by the route). The Edit dialog is prefilled, carries the "Suggested automatically from the callsign. Check it before using it." hint and a "Remove the suggestion" action (a `formaction` button of the same form).
- **Routes** (`companion/airline_suggest_actions.py`): `POST /airlines/suggest` (administrator, CSRF, prefix re-checked by `unresolved_row_for_prefix`, row position 0 to 999, JSON `{state, html}`) and `POST /airlines/suggest/reject` (redirect back to the editor). `post_actions._handle_manual_resolve_post` records `accepted` (stored name equals the cached suggestion, compared server-side) or `edited` after a successful `add_entry`, and the `airline.resolve` audit detail gains `suggestion`. Refusal conditions, flash keys and redirect targets are untouched.
- **Script** (`airline-suggest.js`, 136 lines, ES5): asks the pending rows one at a time, never while the tab is hidden, swaps in the returned row, stops at the first busy, failed, off or stale answer and then removes the pending tag of the rows it did not ask; no visible text of its own.
- **Docs**: `deploy/skypane.env.example`, a "AI-suggested airline names" section in `deploy/README.md`, and the Anthropic API as the thirteenth source of `COMPLIANCE.md` (count sentence and status table updated together).

## Messages API re-verification (before writing the call)

The `claude-api` skill could not be loaded: this run had no Skill tool (a call returned "No such tool"), and no `claude-api` skill exists on disk. Same for `sketch-findings-skypane`: the Skill tool was unavailable, so the skill's `SKILL.md` and the mock's own tokens were read from `.claude/skills/` and `companion/static/style.css` instead. The facts were therefore re-checked directly against platform.claude.com on 2026-11-21 (versioning, models overview, errors, thinking, data retention pages):

- Model `claude-haiku-5-5`: confirmed as the alias; retirement "not sooner than October 7, 2027". Confirmed.
- `anthropic-version: 2026-10-21`: confirmed current; on it `temperature`, `top_p`, `top_k` are removed and any of them returns 400 on every model. Confirmed, never sent.
- Thinking: Haiku 5.5 has thinking on by default and accepts `thinking: {"type": "disabled"}` at effort high or below (default effort medium; xhigh and max return 400 with it). Confirmed; sent, effort not set.
- Prefill: rejected with 400 on Claude 4.6 and later. Confirmed; the conversation ends with the user message.
- Response and errors: `content` blocks (first text block used), error JSON `{"type":"error","error":{...},"request_id"}`, the `request-id` header, 429 may carry `retry-after` and a spend-cap 429 has none. Confirmed. This client does not honour `retry-after`: one attempt, the 15 minute failure cache is the retry policy.
- No disagreement with the plan was found, so nothing was changed.

## Tests and gates (exact results)

- `server/.venv/bin/python -m pytest` through `./scripts/run-all-tests.sh` with `SKYPANE_REQUIRE_BROWSER=1 SKYPANE_TEST_GROUP=core`: **12306 passed, 7 skipped, 0 failed** (first run of the same group: 9 failed, all pinned lists, fixed in the last commit, see deviations). The 7 skips are the existing root-permission and openssl skips.
- Browser, editor group (`test_browser_airline_suggest`, `_editor`, `_table`, `_collection`, `_promotion`): **114 passed**. `test_browser_french_fit` and `test_browser_overhaul_sweep`: **727 passed**. Both with `SKYPANE_REQUIRE_BROWSER=1`.
- `stub-server/test_phase47_freeze.py`, `companion/test_access.py`, `companion/test_access_matrix.py`: **2141 passed**. `deploy/` tests: 308 passed, 1 skipped.
- New tests: `server/test_airline_suggest.py` 54, `test_airline_suggest_page.py` 15, `test_airline_suggest_routes.py` 31, `test_browser_airline_suggest.py` 13. The pytest-socket guard is untouched: no `enable_socket` anywhere, every test uses the fake client or the loopback fake.
- `ruff check .` clean; `mypy` "no issues found in 47 source files" (module added to the file list and the strict override); `scripts/check_function_size.py check --max 80 server stub-server`: 1172 functions, none over 80; `scripts/check_comment_history.py check` exit code 0; `companion/app.py` 1496 lines; largest JS file 1227 lines (`airline-suggest.js` 136); `server/requirements.txt` and `requirements.in` have no diff.

## Render baseline

Regenerated with `PYTHONPATH=. test-support/companion_render_snapshot.py --write` twice, not once: the first (commit a1594ba7) recorded the changes below; the route-table test then needed the two new POST routes in the unauthenticated samples of the snapshot, so a second regeneration added exactly those two entries (6de8d07d). Reviewed diff of the first: 16 paths x 4 variants differ only in the shared sprite line (the new `icon-spark` symbol; removing that one symbol reproduces the old output and the old pinned digests byte for byte) and `/airlines` also in the `style-airlines.css` hash. The editor's script list is not part of the baseline (the `/airlines/manage` page is not in it). The editor rows themselves are unchanged with no key set (asserted by `test_with_the_service_off_the_page_is_the_plain_manual_flow`).

## Captures (fidelity check)

Mock and built are separate full-page images, `…/scratchpad/p39b/mock/` (48 files: `mock-{en,fr}-{light,dark}-fullpage.png` plus every figure as `{desktop-editor,desktop-dialog,desktop-success,phone-suggested,phone-pending,phone-none,phone-error,phone-off,phone-success,phone-dialog,phone-long}-{lang}-{theme}.png`) and `…/p39b/built/` (`{desktop,phone-suggested,phone-pending,phone-none,phone-off,phone-long}-{lang}-{theme}-{full,view,dialog,success}.png`, 1440, 390, 360 for the long name, and `phone-suggested-320-…`). Capture scripts: `p39b/tools/capture_mock.py`, `capture_built.py`.

## Design-system divergences

Mock versus built, each with its reason (none is a behaviour change):

1. **Sightings line**: the built row keeps the real line (`callsign · 9 views · 17 Nov 11:29 (3d ago)`); the mock drew "Seen 4× · 17 Nov · A320 · A321". The registry holds one example callsign, no aircraft types; the line is the existing component.
2. **Name it button has no pencil icon** (mock has one): the existing button is unchanged so that service-off and non-suggested rows stay byte-identical (the plan's acceptance criterion).
3. **Edit dialog uses the shared dialog**: a close X in the header (mock none), "Cancel" as the shared dismiss link (the secondary-button style of `a.modal__dismiss--button` lives in `style-admin.css`, not loaded on this page; the existing Name it dialog looks the same), Validate without a check icon, the real tinted field. Title "OCN · Edit the name" in the real heading style (mock: mono prefix). Remove the suggestion is red text on the left (desktop) and the last button (phone), as drawn.
4. **Check icon stroke**: the shared `icon-check` (1.5 stroke at 22 px) instead of the mock's 2.4 stroke; adding a second check symbol for weight alone was not worth a sprite change.
5. **Pending dot motion**: reuses `.is-breathing` / `skypane-pulse` (opacity 1 to 0.35, `--motion-slow`, 15 beats, then rests); the mock's scale-and-opacity 1.4 s pulse would need a new keyframes block and duration literal, which the motion budget forbids. Reduced motion is handled by the global rule.
6. **Spacing**: row gap and padding are the real row's 16 px tokens (mock 12 and 14 px). The long name at 360 px therefore truncates a few characters earlier ("Oceanair R…" against "Oceanair Regio…").
7. **Edit link is at least 44 px wide** (mock about 38 px): the browser test measured the hit area and failed; the 44 px rule wins.
8. **Narrow wrap**: below roughly 330 px of row width the controls drop under the text (`.airlines-gap--suggest`, body basis 96 px), instead of squeezing the name to two letters (320 px is out of contract; the mock does not draw it). At 390 px English and French stay on one line.
9. **Success toast**: the real manual-naming flash ("Airline name saved. The frame will pick it up next time it wakes and polls.") with the real toast style, not the mock's "Airline named for OCN: Oceanair." (owner instruction).
10. **Pending tag hidden without script** (`@media (scripting: none)`): not drawn in the mock; without a script nothing would ever resolve it.
11. **At most 3 pending rows per page** are drawn pending; the others show plain Name it until a later visit (the mock draws one pending row).
12. **Extra, not visible**: the Edit link's accessible name is "Edit the suggested name for OCN" (the mock only says "Edit"); Remove the suggestion redirects to the editor with no toast (the mock draws none).
13. **Shell**: the mock's sidebar, chips, counts and unrelated blocks are an approximation of the real shell; only the unidentified card, its dialog and the toast were compared.

Not divergences: tag wording, error silence (variant A), reject only in the dialog, caps, model and privacy facts are exactly as approved.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] `ui_modal.dialog_html` needed a place for a second submit action**
- **Found during:** Task 5
- **Issue:** the shared dialog has only Submit and Dismiss; "Remove the suggestion" has to sit in the action row (desktop left, phone last).
- **Fix:** new optional `extra_action_html` argument (empty by default, output unchanged for every other caller).
- **Files modified:** `companion/ui_modal.py`
- **Commit:** 6e8e8269

**2. [Rule 3 - Blocking] A new shared icon changed the sprite of every page**
- **Found during:** Task 5 and the full run
- **Issue:** the approved Suggestion tag has a spark glyph that the sprite did not have (the sprite is shared by all pages).
- **Fix:** `icon-spark` added to `ICON_IDS` and the sprite; the icon-count test (61 to 62), `test_i18n` unchanged-in-French allowance for "Suggestion", three pinned digests in `test_sign_in_surfaces.py` (verified by stripping the symbol) and the render baseline were updated.
- **Commits:** 6e8e8269, a1594ba7, 6de8d07d

**3. [Rule 1 - Bug] Pinned lists missed by the plan failed the first full run**
- **Found during:** Task 8 (9 failures of `companion/test_companion_app_03.py`, `test_csrf.py`, `test_device_routes.py` (47 to 49 device-scoped routes), `test_route_table.py` (3), `test_suite_guards.py` (G9: helper module without `__test__ = False`), `test_sign_in_surfaces.py` (2))
- **Fix:** the lists, the deferred-script count (28 to 29), the digests and the helper module were updated; `airlines_page.AIRLINE_SUGGEST_ROUTE` samples added to the snapshot's unauthenticated POSTs (second baseline regeneration, see above).
- **Commit:** 6de8d07d

**4. [Rule 1 - Bug] 44 px target and narrow-width squeeze found by the new browser tests**
- **Fix:** Edit link `min-width: 44px`; suggestion rows wrap their controls under the text on very narrow rows.
- **Commits:** a9ab5693 (tests), 6e8e8269, f63a2774

**5. Matrix files**: the plan named `test-support/access_matrix_support.py`; the rows live in `test-support/matrix_rows_admin_frame.py` and the hand-written list of `companion/test_access_matrix.py`, which are what changed.

### Plan success-criteria divergences (1) to (6)

1. Owner decisions at Task 2: none changed AIS-01 to AIS-10; the tag stays "Suggestion", error variant A, reject only in the dialog, caps 10 an hour and 60 a day, one request per prefix ever, `claude-haiku-5-5`, livery deferred.
2. `companion/app.py` edited once, one line (1495 to 1496): `layout.AIRLINE_SUGGEST_SCRIPT_SRC` in the manage-route script tuple.
3. Sample callsigns do come from the history: the registry's `example_callsign` first, then up to 3 more distinct recent callsigns of the prefix from `runway_events` (grouped by callsign, newest first), all filtered to `[A-Z0-9]{2,8}` starting with the prefix; a missing or broken history database gives the example alone (tested). The database file is never created by this read.
4. API usage versus the interface block: no difference (see re-verification); the skill itself was unavailable.
5. Phase 64 overlap: `gh api repos/{owner}/{repo}/pulls?state=open` returned one pull request, #481 (dependabot, playwright 1.64.1 to 1.65.2 in `/server`); it touches none of `airlines_page.py`, `airline_table.py`, `style-airlines.css`. This plan edited all three (plus `airline_rows.py`).
6. The build was not split.

## Known Stubs

None.

## Threat Flags

None beyond the plan's register: the two new routes are in the access matrix, CSRF-flagged and admin-only; the new outbound call is the planned one (`api.anthropic.com`, prefix and samples only).

## Server steps for the owner

- The key is already set (`SKYPANE_ANTHROPIC_API_KEY` in `/opt/skypane/skypane.env`). Deploy the usual way (reviewer-gated), then `sudo systemctl restart skypane-companion` so the companion reads it. Nothing else: no new unit, no new package, no schema change; `airline_suggestions.json` is created in the state root on the first request.
- Do not set `SKYPANE_ANTHROPIC_BASE_URL` in production.
- To check: open `/airlines/manage` as administrator; each never-asked prefix shows "Looking for a name" and becomes a Suggestion within a couple of seconds (at most 3 per page load; reload for the next ones). `journalctl -u skypane-companion` shows a single `airline_suggest: prefix=… reason=…` line only when a call fails.

## Open questions

- None blocking. For the owner: if the shell's "Cancel" link in dialogs should be the bordered secondary button the mock drew (divergence 3), that is a change to the shared dialog styles for every dialog, not to this feature.

## Self-Check: PASSED

Created files exist (service, fake, actions module, script, four test modules, helpers); commits 92f8b503, 6e8e8269, a9ab5693, 7ce87012, f63a2774, a1594ba7, 6de8d07d exist; tree clean after this summary's commit.
