# Motion

Code: `companion/static/style.css` (tokens at `:root`, `@keyframes`), `static/motion.js`,
`static/toast.js`, `static/splash-boot.js`, `static/splash.js`. Motion is an enhancement: every
page looks and works the same without it.

## The budget is executable

`companion/test_companion_app_04.py` reads the served stylesheet and asserts:
- `test_style_css_honours_the_motion_budget`: each `@keyframes` name defined once; every
  `animation` name resolves; every animation duration is `var(--motion-*)`, never a literal; the
  reduce blocks number `_EXPECTED_REDUCED_MOTION_REDUCE_BLOCKS = 3` and the no-preference blocks 1;
  neither `interpolate-size` nor `calc-size(` is used (animate height with
  `grid-template-rows: 0fr -> 1fr`).
- `test_every_transition_takes_its_duration_from_a_motion_token`: transitions too.
- `test_motion_tokens_are_two_durations_plus_the_documented_exceptions`: which rule may spend
  which token (the toast dwell tokens, `--motion-dot-pulse`, the ambient tokens).
Plus `ENTRANCE_SELECTORS` and the `OPENING_*` lists that pin which blocks get the page opening.
New motion spends a token and, if it adds a keyframe or a reduce block, updates the pinned count.

## Tokens (`:root`)

| Token | Value | Use |
|-------|-------|-----|
| `--motion-fast` | 180ms | a reaction the user is watching confirm (selection, switch, dialog, wash) |
| `--motion-slow` | 2s | an ambient loop nobody waits on (status dot) |
| `--motion-enter` / `--motion-stagger` | 400ms / 60ms | card entrance, per-sibling delay |
| `--opening-opacity` | 0.6 | where the page-opening fade starts |
| `--ease-out` | `cubic-bezier(.22,1,.36,1)` | |
| `--motion-spring`, `--motion-spring-duration` | overshooting curve, 420ms | press release, switch thumb, sliding tab pill (only on `scale`/`transform`) |
| `--motion-press` | 90ms | the un-sprung half of a press |
| `--motion-view-transition` | 260ms | cross-document page change |
| `--motion-shimmer`, `--motion-reveal` | 1.3s, 900ms | loading sweep, blur-up of a picture |
| `--motion-picture`, `--motion-unlock`, `--motion-count` | 480ms, 560ms, 600ms | thumbnail to picture, airline unlock flip, number count-up (read by `motion.js`) |
| `--motion-toast-dwell`, `-long` | 6s, 12s | how long a toast stays; only the timer hairline spends them |
| `--motion-dot-pulse` | 3.2s | the halo around Home's status dot, only `.home-state__dot--pulse::after` |
| `--motion-breathe`, `--motion-glint` | 6s, 12s | Home's two ambient loops |

Rule of thumb: motion is opacity and translate (and scale on a spring), never margin, height,
filter or a row. A bare duration literal on an animation or a transition fails the test.

## Page opening and page change

- Every page's `<main data-page-open>`: the header fades first, then filter bar, chips, facts and
  the first blocks one `--motion-stagger` later; `skypane-reveal` (a 12px rise in `steps(12)`, whole
  pixels so a 44px control is never hit-tested short) plus `skypane-reveal-fade`, both
  `--motion-enter`, fill-mode `backwards`. At most the first five or six blocks and the first three
  Flights days; never a row, a table, a list or the map. A new page needs no markup.
- Cross-document view transition (`@view-transition { navigation: auto }`, only under `prefers-reduced-motion: no-preference`): one change of 260ms. Named groups: `skypane-tab-bar`,
  `skypane-tab-slider`, `skypane-sidebar`, `skypane-strip`, `skypane-picture`,
  `skypane-flight-pic`. When a page arrives by a view transition, `splash-boot.js` adds
  `html.page-crossfade` on `pagereveal` so the block entrance is skipped: one motion, not two.
- Tab strip: any segmented strip with `data-tabs="<name>"`; one `.tabs-thumb` slides (transform and
  width, `--motion-fast`). `data-tabs-content`, `data-tabs-replay="fade"`, `data-tabs-thumb="none"`
  tune it; a switch that stays on the page replays the content with `.reveal-replay`; "Load more"
  enters its first three new items with `.reveal-appended`.
- The tab bar's slider pill (`motion.js`) moves under the current or pressed cell with a spring.
- One-directional entrances: opening animates, closing is instant (a closing element must not stay
  focusable or in the accessibility tree during an exit).

## Other motion

- Splash "Cadre": frame outline, e-paper refresh, scan-line logo reveal; once per browser session,
  hard cap about 3.2s; none without scripts or session storage.
- Toast: `skypane-toast-in`, the timer hairline `skypane-toast-dwell`, swipe to dismiss.
- Home: number count-up once, flight rows FLIP to the top, the ambient loops rest on idle
  (`html[data-ambient="rest"]`).
- Flights: pull to refresh (spinner capped at 9 turns); `skypane-row-arrive` washes a new row.
- Airlines: the unlock flip with a glint and sparks, once per airline and user.
- Save bar: `skypane-bar-arrive`.

## Reduced motion

A global `@media (prefers-reduced-motion: reduce)` block in `style.css` sets animation and
transition durations to 0.01ms with `!important`, and limits transitioned properties to ones that
paint without moving layout. Two more reduce blocks switch off the loops that a 0.01ms override
would leave running (the halo, shimmer, switch ring, slider stretch, press scale) and the Place
map tiles (`style-place.css`). `motion.js` adds no class and starts nothing when the preference is
set. "Every animation is finite" holds except the resting status dot and the ambient loops of Home;
no loop runs under reduced motion.
