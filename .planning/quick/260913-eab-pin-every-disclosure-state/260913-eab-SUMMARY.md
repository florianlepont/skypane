---
quick_id: 260913-eab
status: complete
date: 2026-09-13
commits:
  - d5a1cf5
files_modified:
  - companion/test_browser_ux.py
---

# 260913-eab — every disclosure on every page, opened and measured

One new check in `companion/test_browser_ux.py`. It forces every `<details>` on every
page open and asserts nothing overflows — the general form of the check 260913-cz6 added
for one table on one page. No production code changed: this task ships a guard, not a fix.

## The counts — yours held, the total did not

Re-derived by running, at 390px in French, with every disclosure forced open:

| page       | route       | `<details>` | kinds                          | brief said |
| ---------- | ----------- | ----------- | ------------------------------ | ---------- |
| Accueil    | `/`         | 1           | nav                            | 1 ✓        |
| Affichage  | `/display`  | 3           | nav + 2 « comment ça marche »  | 3 ✓        |
| Vols       | `/flights`  | 37          | nav + 36 row cards             | 37 ✓       |
| Compagnies | `/airlines` | 1           | nav                            | 1 ✓        |
| État       | `/health`   | 4           | nav + readings + 2 data cards  | 4 ✓        |
| Appareil   | `/device`   | 1           | nav                            | —          |
| Connexion  | `/login`    | 0           | renders no nav at all          | —          |

Every per-page figure in the brief is confirmed exactly, and so is its 46 across those
five pages.

**The `~83` total is not real.** There is no panel-preview page. `companion/app.py`
serves exactly six HTML page routes plus `/login`; `/preview` and `/settings` are fixed
303 redirects (to `/flights` and `/display` respectively), so the "panel-preview page's
~37" in that figure is `/flights` counted a second time. The true total is **47**.

The brief's own caution about the raw number was right and is worth keeping: 36 of Vols'
37 are one component repeated per row. **Five distinct kinds** exist — nav "More", the
Display "how it works" pair, the Flights row card, the Health data card, and the Health
readings disclosure. The nav disclosure alone accounts for 6 of the 47.

One fact the survey turned up that matters more than the counts: **all 47 are closed by
default, on every page, at every width** (`closedBefore == n` everywhere). So forcing
them open is doing real work on every single page — this is not a sweep that was already
covering most of them incidentally.

## What the check asserts

For each of **360, 390 and 1280px × {en, fr}** — `/login` measured first in a fresh
context (after `_login()` it is a 303 to `/`), then the six authenticated pages — it
forces every `<details>` open and then asserts:

1. `document.documentElement.scrollWidth` does not exceed the viewport, and nothing lays
   out right of it.
2. **No element whose computed `overflow-x` is `auto` or `scroll` has content wider than
   its own box.** This is the half that catches the readings-table class, where the wrap
   scrolls and the page does not — `documentElement.scrollWidth` stayed exactly 390 with
   that disclosure both closed and open.

`overflow: hidden` is deliberately excluded from (2): `text-overflow: ellipsis` makes
`scrollWidth > clientWidth` by design on every truncated cell in the app, so including it
would produce noise — and noise is how a check ends up with an exception bolted onto it.

**Anti-rot.** Each of the six authenticated pages asserts a minimum disclosure count *and*
that at least one was **closed** before being forced. The second half is the one that
matters: without it the check silently degenerates into an ordinary default-state page
sweep and stops adding anything, while still passing. `/flights`' minimum of 37 is
knowingly coupled to `seed_state_dir()`'s 36 runway events and says so where it is
declared, so a seed change forces a deliberate re-derivation rather than sliding.

`/login` carries **no** count assertion, because it genuinely has zero disclosures —
asserting non-zero there would assert a falsehood. Its "this measured something" guard is
the password field, and it is still measured for the overflow half.

The failure message reports the **scroll-container** diagnostic before the viewport one.
That ordering was chosen from the mutation run, not guessed: when a container overflows,
every descendant's layout rect escapes the viewport too, so the generic assertion also
fires and reports `['data-table data-table--readings', 'THEAD', 'TR', 'TH', ...]`, which
points at nothing. Naming the container, its box and its content width points at the cause.

## Mutation test — it catches the defect unaided

The honest mutation: restore `min-width: max-content` on `table.data-table--readings` in
`companion/static/style.css`, the exact defect the developer found on a phone.

| run                                                      | result    | red checks               |
| -------------------------------------------------------- | --------- | ------------------------ |
| Mutation applied, both checks present                     | **24/26** | cz6's check **and** mine |
| Mutation applied, **cz6's check deleted from the file**   | **24/25** | **mine only**            |
| Mutation reverted                                         | **26/26** | none                     |

The second run is the one that answers the question. "Both went red" does not by itself
prove the general check did any work, so cz6's check was removed outright and the mutation
re-run. The new check still failed, on its own, reporting:

> `/health` at 360px/en gives a scroll container its own horizontal scrollbar with every
> disclosure open, which the page itself never shows (documentElement.scrollWidth 360
> against a client width of 360): `[{'box': 'data-table-wrap', 'boxWidth': 278, 'content':
> 369, 'firstChild': 'data-table data-table--readings'}]`

It names the container, its 278px box and its 369px of content. It is **not** weaker than
the specific check it generalises. `companion/static/style.css` was then restored and
verified byte-identical to its pre-mutation state.

It also caught it at **360px first**, before 390px — the width the specific check does not
measure at all.

## Runtime — measured, not estimated

| harness                              | wall time |
| ------------------------------------ | --------- |
| `test_browser_ux.py`, pristine (25 checks) | 46.2s |
| `test_browser_ux.py`, with this check (26) | 54.5s |
| **this check alone**                 | **8.3s**  |

Full suite total wall time: **52.3s → 60.1s (+15%)**, since this harness sets it.

That is 42 page-state measurements (7 pages × 3 widths × 2 languages) at ~0.2s each. The
matrix was **not** reduced; the runtime was bought down instead, by dropping
`wait_for_load_state("networkidle")` in favour of waiting for the page's own `<main>`. That
alone took the first working version from 22.6s to 6.8s, because networkidle costs ~0.5s on
each of 42 loads and buys nothing measurable here (see the known limit below).

**One width was added rather than dropped.** The brief asked for 390 and 1280; this ships
**360 as well**, at a cost of ~2.8s. 360px is the minimum supported viewport per the
developer's own decision of 2026-09-13 (`.claude/skills/sketch-findings-skypane/SKILL.md`),
and both fixes of that day were driven by 360px failures a phone-sized assumption had
missed. It was measured clean before being added, never assumed. Easy to remove if the
~3s is not judged worth it.

## Known limit, stated rather than papered over

Images marked `loading="lazy"` below the fold are not loaded when this measures, so a
future overflow caused by one would be invisible to it. This is **not** a consequence of
the cheap readiness wait: measuring both ways leaves the identical images pending (72 of
`/display`'s 76, 26 of `/airlines`' 28), because that is what lazy loading means — the
images only load when scrolled into view, and `networkidle` does not scroll. Every image
inside a disclosure today is loaded when this runs (`/flights`: 37 images, 0 pending).

## Nothing was fixed, because nothing was broken

Surveyed at **320, 360, 390, 768 and 1280px × both languages**, every page, every
disclosure forced open: no page scrolls sideways, nothing lays out right of the viewport,
no scroll container's content exceeds its box. The brief's "all currently clean" holds,
across a wider width range than the check itself ships with. No overflow was found, so
none was fixed.

## Verification

- `EXPECTED_CHECK_COUNT` re-derived by **running** the harness: 25 → **26**, cross-checked
  against the real on-disk `check(` call-site count (26), never trusted from arithmetic.
- `./scripts/run-all-tests.sh`: **exactly 5 failing checks**, the same 5 names as the
  pre-change baseline captured at the start of this task — 4 × WR-11 read-only
  (`test_companion_app.py` ×2, `test_manual_resolutions.py` ×2) and 1 × `anomaly_active()`
  (`test_status_pages.py`). All pass in CI; this container runs as root.
- No test exception added. `companion/static/style.css` untouched in the final diff and
  still carries zero stray comment terminators.
- ROADMAP.md untouched. STATE.md gains exactly one row in its "Quick Tasks Completed"
  table, its repaired single-frontmatter structure and quoted historical block intact.
