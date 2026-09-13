---
quick_id: 260913-cz6
status: complete
date: 2026-09-13
commits:
  - 20e4b6c
files_modified:
  - companion/layout.py
  - companion/pages/health_page.py
  - companion/static/style.css
  - companion/test_browser_ux.py
  - companion/test_status_pages.py
  - .claude/skills/sketch-findings-skypane/references/data-density.md
---

# 260913-cz6 — the readings table stops scrolling on a phone (B12's cause, third table)

## The measurements held, every one of them

Reproduced before touching anything, with a real Chromium tab against a real
`companion/app.py` subprocess, disclosure forced open, at 390px:

| lang | wrap clientWidth | table width | col 1 (timestamp) | col 2 (mV) | `doc.scrollWidth` |
| ---- | ---------------- | ----------- | ----------------- | ---------- | ----------------- |
| FR   | 308              | 431.5       | 301.7             | 129.8      | 390               |
| EN   | 308              | 369.0       | 243.9             | 125.1      | 390               |

`overflow-x: auto` on the wrap, `min-width: max-content` on the table, `white-space:
normal` on the cell. 302 + 130 = 432 against 308 → **124px of overflow**. Every
figure in the brief is confirmed, including the one that matters most: the page
`scrollWidth` is **390 with the disclosure closed and 390 with it open**. Nothing
at page level moves, ever.

The brief's diagnosis of *why every check missed it* is also confirmed, and is
actually two independent blind spots stacked on top of each other:

1. **The wrapper scrolls, not the page.** Every overflow assertion in this repo
   measures `document.documentElement.scrollWidth`. That quantity is structurally
   incapable of seeing an overflowing `overflow-x: auto` box.
2. **The table is never laid out at all** in the state every sweep measures,
   because it sits inside a closed-by-default `<details>`.

Either one alone would have hidden it. It is a page STATE nobody measured, exactly
as described.

The "not a phase-22 regression" framing also holds and I did not go looking for a
commit to blame.

## What I chose, and why — the registry treatment was measured and rejected

The brief anticipated the stacked-cell treatment. I measured it on this table
**first**, and it does not work here. Three candidates, same tab, same fixture:

| treatment | 320/FR | 360/FR | 390/FR | 1280 row height |
| --------- | ------ | ------ | ------ | --------------- |
| (C1) stack, keep `max-content` — the registry's remedy | **+59** | **+19** | 0 | 70.5 (two lines) |
| (C2) release `max-content` — **chosen** | 0 | 0 | 0 | 51 (one line) |
| (C3) C2 + `nowrap` atoms via new spans | **+26** | 0 | 0 | 51 (one line) |

**C1 is rejected on its own numbers, not on taste.** Stacking lowers the
max-content floor from 432px to 297px — which clears 390px by *exactly zero* and
still overflows at **360px** (297 against 278) and **320px** (297 against 238).
Copying 22-12 here would have shipped a fix already broken on a common Android
width, while also forcing two lines at 1280px where the wrap has 830px to spare.
The registry selector was **not** widened to cover both tables.

**C3 is rejected because it pays a real price for a width it does not fix.** It
buys atom integrity at 320px but still overflows there (+26 FR), in exchange for
a markup change to `concise_timestamp_html()` — 86 references across the suite,
and a `.cell-primary`/`.cell-secondary` retrofit would drag `.cell-secondary`'s
`opacity: 0.7` and `.cell-inline-sep`'s middle dot onto **every other page** that
renders a concise timestamp. Not taken. `concise_timestamp_html()` is untouched.

## So I took the remedy 22-12 rejected — here is why it is right here

22-12 deliberately kept `min-width: max-content` on the registry and recorded that
releasing it was the other obvious fix. I released it here. The two decisions are
consistent, and the reason is **specific to each table's columns**:

The floor exists to stop **short opaque codes** cropping. The registry has two such
columns — the prefix and the example callsign (`EXEMPLE D'INDIC`) — and neither has
a safe internal break point, so releasing the floor there would let them wrap
mid-token, which reads as corruption. The floor is doing real work.

This table has **no such column**. It has exactly two:

- the millivolt value, a four-digit integer — **a single token with no break
  opportunity at all**, so the floor is provably inert for it; and
- the timestamp, whose **every** break opportunity is a real word boundary.

Measured at 360px and 390px in both languages, the released line breaks on the
exact semantic boundary the stacked treatment would have forced:

```
390/fr  rowH=75   31 juil. 08:00 | (il y a 44 j)
390/en  rowH=75   31 Jul 08:00   | (44d ago)
1280/fr rowH=51   31 juil. 08:00 (il y a 44 j)
```

That is not luck — the space before the parenthesis is the only mid-string break
opportunity, and French already carries a **non-breaking space inside "44 j"**, so
the age cannot split either. At 768px and 1280px it stays on one line, so the fix
costs **no row height where there is room** — which forced stacking would have.

**The floor protects nothing here that is not already safe, while forbidding the
one break that makes the table fit.**

Scoping is by its own modifier class, per the brief and the registry precedent:
`layout.data_table()` gained an additive `modifier` keyword (default output
byte-identical, `prose=True` byte-identical), the readings table passes
`modifier="readings"`, and the stylesheet carries one rule —
`table.data-table--readings { min-width: 0 }` — whose comment records **this
task's own numbers** and states explicitly that it is not the stacked-cell
exception.

## Final measured state

| width | FR overflow | EN overflow |
| ----- | ----------- | ----------- |
| 320   | 0           | 0           |
| 360   | 0           | 0           |
| 390   | 0           | 0           |

## A check that anchored on the literal I moved

`test_status_pages.py`'s reframe check located the battery table by
`'<table class="data-table">'` — the bare class attribute, which was unique to this
table (the registry's is `--registry`, the stats table's is `--prose`). Adding the
modifier moves that literal. Retargeted **in place** onto
`<table class="data-table data-table--readings">` rather than loosened to a
substring that would also match the other two tables, with its comment corrected
rather than left lying. Caught by running the suite, not by reading it.

## The new harness check, and its mutation test

One check in `companion/test_browser_ux.py`, written for the **class**: at 390px, in
**both languages**, on État — it opens **every** `<details>` on the page, then
measures **every** `.data-table-wrap` against its own `clientWidth`. Not one
selector: any table a future disclosure hides, or any new column on an existing
one, is covered without editing the check. It asserts a non-zero wrap count *and* a
non-zero row count, so it cannot pass by measuring nothing.

**Mutation test, both numbers:**

- `min-width: max-content` restored on the modifier → **23/24**, the new check the
  only one red, naming the overflow precisely: *"a table inside a disclosure
  overflows its own wrap at 390px/en … `[{'cls': 'data-table data-table--readings',
  'wrap': 308, 'table': 369, 'cols': [244, 125]}]`"* — the class, the wrap's
  clientWidth, the table's scrollWidth and the per-column widths.
- fix restored → **24/24**.

`EXPECTED_CHECK_COUNT` re-derived by **running** the harness: 23 → **24**.

## Verification

`./scripts/run-all-tests.sh` — at the documented sandbox baseline of exactly **5**
failing checks, all pre-existing, all root-only artifacts, verified by NAME:

| harness            | result                                   |
| ------------------ | ---------------------------------------- |
| browser-ux         | **24/24**                                |
| companion-app      | 270/272 (2 × WR-11 read-only)            |
| status-pages       | 267/268 (`anomaly_active()`)             |
| manual_resolutions | 21/23 (2 × WR-11 read-only)              |
| view-pages         | PASS                                     |
| i18n               | PASS                                     |

No test exception added — the suite still carries none. No new user-facing string,
so no French catalogue entry was needed; CFG-29/CFG-30 do not regress. The
stylesheet's stray-comment-terminator guard passes by name (the new comment is one
opener, one closer, and never writes a terminator inside itself).

## Design system

`references/data-density.md` updated — and the update deliberately does **not** add
a third stacked-cell consumer. It records this table as a third measurement of the
same cause that took the **other** remedy, keeps the consumer count at two, keeps
the do-not-generalise warning verbatim, and adds the new general lesson: a scrolling
**wrapper** is invisible to `document.documentElement.scrollWidth`, so each
`.data-table-wrap` must be measured against its own `clientWidth` with every
`<details>` forced open.

## Found, not fixed, and deliberately

**The other collapsed states — surveyed, all currently clean, none pinned.** I opened
every `<details>` on every page at 390px in both languages and measured every
`.data-table-wrap`, every element against the viewport, and every scrollable box:

| page        | `<details>` | overflow found |
| ----------- | ----------- | -------------- |
| `/` Accueil | 1 (nav "More" sheet) | none |
| `/flights`  | 37 (per-card `history-card__details` + nav) | none |
| `/airlines` | 1 | none |
| `/health`   | 4 (2 × `readings-disclosure`, `data-card__details`, corroboration) | none (post-fix) |
| `/settings` | 3 ("How rules combine", "How it works") | none |
| `/preview`  | 37 | none |

They are clean **today**, but nothing pins them — my new check covers État only.
The 37-disclosure Flights card list is the obvious follow-up candidate: it is the
densest collapsed content in the app and the same class of defect there would be
equally invisible. A general "open every disclosure on every page, measure every
wrap" sweep is worth its own plan rather than a quick task's drive-by.

**At 320px the break point is uncontrolled, and the table still fits.** The shipped
fix has zero overflow at 320px, but the line breaks mid-atom there —
`31 juil.` / `08:00 (il y` / `a 44 j)`, splitting the date from the time. That is
the honest cost of the floor release at a width nothing in this repo targets;
C3 was measured as the remedy for it and **still overflowed at 320px**, so it buys
nothing. Recorded rather than silently absorbed, alongside quick task 260913-bjy's
own 320px callsign-starvation finding — two independent 320px issues now logged,
which together argue for a deliberate decision about whether 320px is a supported
width at all.

## Anything the brief missed

**The brief's own fix suggestion would not have worked, and only measurement showed
it.** The brief reasoned from B12 that the stacked treatment applies, and asked me
to justify releasing the floor as the *alternative*. In fact the ordering is
inverted: stacking is the one that fails here (it still overflows at 360px), and
releasing is the one that works. Applying the brief's primary suggestion without
measuring past 390px would have shipped a fix that looked correct at the one width
it was tested at and was already broken on the next phone size down — the exact
failure mode the design system's "measure first, in both languages, at the real
viewport" bar exists to prevent.
