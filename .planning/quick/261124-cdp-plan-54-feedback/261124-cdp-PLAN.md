---
type: quick
slug: plan-54-feedback
workstream: v1-2
---

# Plan 54: owner feedback fixes (Companion and Console)

Small fixes, one branch, atomic commits. Each item gets a behaviour test
(served HTML/CSS/JS or Playwright; never source text).

## Tasks

1. **Home: remove the edit pencil** next to the frame name (rename stays in
   Account). Fix the info "i" button wrapping under the text at 360 px in
   French (it must stay on the line of the text, or wrap with it). Browser test
   at 360 px FR.
2. **Airlines page: default sort is by rarity** (rarest first). Keep the
   existing sort control and its other options.
3. **French nav label for the Airlines entry is "Airlines"** (`nav.airline_collection`
   in `companion/i18n_fr/nav.py`). Check every other nav/page-title entry for the
   same regression and keep EN/FR ids free of orphans.
4. **Credits page when signed in has no navigation at all** (no sidebar, no tab
   bar, no Console nav, no space switch): only a back link to Account. Public
   (signed-out) behaviour is unchanged.
5. **Frame page tab chips (État/Réglages/Accès) sticky bar**: content shows
   through above it on iPhone. Give it a solid background and cover the
   safe-area gap above it.
6. **Wake interval default is 15 minutes (900 s) for NEW frames only.** Existing
   frames keep their stored value. No migration.
7. **Airline type row menu labels**: FR "Image par défaut" / "Retirer par défaut",
   EN "Set as default" / "Remove as default". Shorten the add-illustration modal
   title (one line; airline name as subtitle).
8. **Auth0 invitation link ("Lien d'invitation non créé")**: investigate only.
   Read the code path, report the exact request made and which Auth0 setting is
   most likely missing. Do NOT change production config. Write findings to
   `261124-cdp-AUTH0.md` in this directory.

## Rules

- Do not touch STATE.md, ROADMAP.md, requirements. Do not switch branches,
  push, or open PRs.
- Gates: ruff, mypy, `scripts/check_function_size.py check --max 80 server stub-server`,
  `scripts/check_comment_history.py check`, `companion/app.py` <= 1500 lines,
  JS <= 1500 lines.
- Tests: `SKYPANE_REQUIRE_BROWSER=1 server/.venv/bin/python -m pytest` on the
  files that mention the changed modules plus `companion/test_companion_app_04.py`,
  `companion/test_stylesheet_structure.py` and the i18n orphan test.
- Do not regenerate `companion/testdata/render_baseline.json`; the orchestrator
  does it once.
- Commit trailers: `Co-Authored-By: Claude Sonnet 5.5 <noreply@anthropic.com>` and
  `Claude-Session: https://claude.ai/code/session_019w4bpiFf6X8ShsAqfXcEhe`.
