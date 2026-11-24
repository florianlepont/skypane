# Wave 2 (F2 access window, F3 add a frame, F5 reassign + invitation failure): summary

Branch: phase-68-plan-55-redesign. Variants F2 A, F3 B, F5 A. Not pushed.

Commits: 3bfdbca8 (F2), a80e4089 (F3), 4553d32d (F5).

## What changed

- F2 "Manage access" (`co_managers_card.manage_access_dialog_html`): three labelled glass
  sections (Owner, Co-managers, Add a co-manager) instead of one group. Initials avatars
  (owner filled with the accent). No co-managers: dashed empty card with the existing heading
  and help line. Add form: admin picker and a short "Add" button share one 44 px line; the
  owner's typed e-mail field keeps its label and helper line, button stacks under it. Footer
  row: "Remove this frame" danger link on the left (owners only), "Done" primary on the right
  (`ui_modal.sections_dialog_html(leading_action_html=...)`). The Fleet page's inline Access
  section (`access_rows_html`) is unchanged.
- F3 `/pair-frame`: one glass card: heading "Enter the code shown by the frame", instruction
  line, big centred mono code field, validity line, actions, then a tinted footer with an info
  icon, "No code on screen?" and the Reset hint. On a phone the actions stack full width.
- F5 reassign (`fleet_page.reassign_dialog_html`): new-owner select, then a two-line effects
  list, confirm disabled (aria-disabled, hint "Choose an owner to continue.") until an owner is
  chosen. Small gate in `modal.js` (`data-gate-select` / `data-needs-choice` / `data-gate-hint`);
  without script the button is enabled, the select stays `required` and the server still refuses
  an empty owner. `ui_modal.dialog_html` gained `submit_attrs`.
- F5 invitation-failure dialog: title and two lines (already so), Try again is the primary with
  the refresh glyph, Done secondary.
- EN/FR: new ids `co_managers.add_short`, `co_managers.section_owner`,
  `pair_frame.enter_the_code_shown_by_the_frame`,
  `pair_frame.turn_the_frame_on_it_shows_an_8_character_code`, `pair_frame.no_code_on_screen`,
  `admin_fleet.reassign_choose_owner_hint`, `admin_fleet.reassign_co_managers_lose_access`.
  Removed the orphaned `pair_frame.enter_the_code_shown_on_your_frame_s_screen`.

## Decisions to review

- F5 checklist is NOT the mockup's copy. The mockup says "Nothing is erased... Co-managers keep
  their access", but `fleet_ops.reassign_frame` erases the previous owner's settings, history and
  gallery on a normal frame and removes every co-manager on all frames. The two lines state the
  truth: line 1 is the existing sentence (green tick for the served frame, amber warning for a
  normal frame), line 2 "Co-managers lose their access to this frame." (warning). Confirm stays
  danger-styled for a normal frame.
- F2 "pending person" state (dashed mail avatar, Pending pill) not built: the dialog's data has
  no pending/not-signed-in notion. The co-managers section has no count pill.
- F3: the validity line keeps the existing longer text ("stays valid for about 35 minutes; a
  new one then appears") rather than the mockup's shorter one, as the refusal alert reuses it;
  no clock icon (not in the sprite). The Reset footer is left out after a refused code (existing
  behaviour pinned by a test: the frame did show a code). The old purpose line under the title
  is gone (the card's heading and instruction replace it).
- F2: the owner row now has the long-address ellipsis (title holds the full value) like the
  co-manager rows, where it used to wrap; the test that pinned wrapping was rewritten.
- Failure dialog: kept the existing lead + reason lines (admin-useful, per-cause) instead of the
  mockup's generic wording.

## Tests and gates

- Updated tests that pinned the old layout (one group, "Add a co-manager" button text, wrapping
  owner address, `Try again</button>`, `<form class="pair-form">` regex); none skipped or loosened.
- New behaviour tests: danger link left of primary Done and three labels (desktop and 360 px,
  EN/FR); add-frame card with footer below actions (360/1280, EN/FR); reassign confirm gating
  and two effects (EN/FR); retry glyph in the served failure dialog.
- ruff, mypy, function-size (none over 80), comment-history: clean. `companion/app.py` 1491
  lines; `modal.js` 790 lines.
- Targeted tests (pinned entrance list, stylesheet structure, i18n, fleet, users, pairing,
  co-managers, account): green. Full `companion test-support scripts` run: 11918 passed, 3 skipped, 2 failed: `test_render_baseline` (needs the orchestrator's regenerated baseline) and `test_the_link_is_held_nowhere_and_the_secret_is_in_no_output` (a `history.db-wal` FileNotFoundError race under parallel load; passes alone and 3 of 3 full-file reruns).

## Not done

- `render_baseline.json` not regenerated (orchestrator, end of plan).
- Pending-person state and co-manager count pill (see above).
