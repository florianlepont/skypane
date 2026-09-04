---
phase: quick-260904-kug
plan: 01
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - .planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md
  - .planning/seeds/SEED-002-web-configurable-wake-interval.md
autonomous: true
requirements: [QT-kug-01, QT-kug-02]
user_setup: []

must_haves:
  truths:
    - "A reader opening `.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md` learns from the frontmatter alone that the idea shipped, and from the first body section that Phase 10 (`.planning/phases/10-scheduled-quiet-hours/`, plans 10-01 through 10-05) is the shipping evidence — without having to search ROADMAP.md or STATE.md to find out."
    - "A reader opening `.planning/seeds/SEED-002-web-configurable-wake-interval.md` learns the same for Phase 11 (`.planning/phases/11-web-configurable-wake-interval/`, plans 11-01 through 11-04)."
    - "Both closures cite the phases' own completed quality gates by filename (`10-VERIFICATION.md`/`10-UAT.md`, `11-VERIFICATION.md`/`11-UAT.md`) rather than asserting completion on the planner's word — every one of those four files was read during planning and independently carries `status: passed` / `status: complete` with zero issues."
    - "Each seed's own open design questions are answered in its closure section, including where the shipped answer contradicts what the seed itself predicted — the divergences are recorded, not quietly dropped."
    - "Neither seed over-claims: each points at its phase's `*-REVIEW.md` as the authoritative home of the non-blocking warnings that remain open, rather than restating them or implying nothing is left."
    - "Both seeds' original bodies survive byte-for-byte below the new dated section, and their original H1 title lines survive unchanged — the record of what was believed at planting time is superseded in place, never deleted, trimmed or rewritten. This is machine-checked against each file's own baseline commit, not trusted to review."
    - "No code file, no `REQUIREMENTS.md`, no `ROADMAP.md`, and none of the six other files in `.planning/seeds/` changes — this plan is documentation-only, and its own verification fails if any tracked file outside the two targets is modified."
  artifacts:
    - path: ".planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md"
      provides: "Frontmatter `status: fulfilled` (replacing `dormant`) + `resolved_date: 2026-09-04`, plus a `## Fulfilled 2026-09-04` section between the H1 and `## Why This Matters`; original body retained verbatim below"
    - path: ".planning/seeds/SEED-002-web-configurable-wake-interval.md"
      provides: "The same two frontmatter edits plus a `## Fulfilled 2026-09-04` section citing Phase 11's four plans; original body retained verbatim below"
  key_links:
    - "Both new sections -> the pinned baseline commits `05e6cf5` (SEED-001) and `f1e9f72` (SEED-002) — each task's `<verify>` diffs the post-`## Why This Matters` tail against its baseline AND asserts the pre-section head region differs by exactly the two intended frontmatter lines, so the 'supersede, don't delete' promise is enforced mechanically in both directions."
    - "`SEED-001`'s new section -> `.planning/phases/10-scheduled-quiet-hours/` (plans 10-01..10-05, all five SUMMARYs `status: complete`, completed 2026-09-03). `SEED-002`'s new section -> `.planning/phases/11-web-configurable-wake-interval/` (plans 11-01..11-04, all four SUMMARYs `status: complete`, completed 2026-09-04)."
    - "Both new sections -> their phase's `*-REVIEW.md`, named as the owner of the remaining non-blocking warnings. If either review's findings are ever closed or promoted to a requirement, these pointers are the first thing to re-check."
    - "The new `status: fulfilled` values -> the convention `.planning/quick/260902-ipj/` established on `bring-up-debug-led-remote-toggle.md`: frontmatter `status`/`resolved_date` plus a dated section above the first original body heading. `fulfilled` (not `partially-fulfilled`) is correct for both seeds here because, unlike the fault-icon seed, neither has an unshipped half."
---

<objective>
Close out `.planning/seeds/`'s two remaining stale entries — `SEED-001` (scheduled quiet hours) and `SEED-002` (web-configurable wake interval) — whose ideas shipped as Phases 10 and 11 but whose files still read `status: dormant`.

Purpose: `.planning/seeds/` is the project's idea backlog. Two of its eight files now actively mislead: a future `/gsd-review-backlog` or `/gsd-new-milestone` surfacing run would re-propose work that is already deployed, verified, UAT-signed-off and security-cleared. Closing them keeps the backlog honest and records, at the seed itself, which of each seed's own speculative design questions the shipped work actually answered — and where it answered them differently than the seed predicted.

Output: two edited markdown files. Nothing else. No code, no `REQUIREMENTS.md`, no `ROADMAP.md`, no other seed.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md
@.planning/seeds/SEED-002-web-configurable-wake-interval.md
@.planning/seeds/bring-up-debug-led-remote-toggle.md
</context>

<research_notes>

Everything below was cross-checked against the repo during planning — every phase SUMMARY, VERIFICATION, REVIEW, SECURITY and UAT file named here was read in full, not skimmed or inferred from ROADMAP prose. Do not re-derive it; do not restate anything beyond it. If a claim you want to write is not in this block, it was not verified — leave it out.

**The convention to match (read `bring-up-debug-led-remote-toggle.md` in `<context>` — it is the byte-for-byte precedent)**

Quick task `260902-ipj` established the shape: (1) frontmatter gains/changes `status` and gains `resolved_date`, with every other key left exactly as planted; (2) a `## Fulfilled <date>` section is inserted directly above the file's **first original body heading**, separated by a blank line; (3) the original body below it is untouched; (4) the section closes with a line stating that everything below is the original record, retained unchanged as history. Tone: factual, dated, specific about what the evidence of record actually is, and never quietly erasing what was believed before.

**Structural difference from the precedent, and how it is resolved.** `bring-up-debug-led-remote-toggle.md` has no H1 — its frontmatter is followed directly by `## Context`, so the new section went immediately after the frontmatter. `SEED-001`/`SEED-002` DO have an H1 (`# SEED-001: ...` / `# SEED-002: ...`) followed by `## Why This Matters`. The faithful analog is therefore: H1 stays first, the new `## Fulfilled 2026-09-04` section goes **between the H1 and `## Why This Matters`**. The H1 is part of the original record and must not be edited.

**Frontmatter difference from the precedent.** These two seeds already carry `status: dormant`, so `status` is *changed in place*, not inserted. They use `planted:` (not the precedent's `planted_date:`), and `resolved_date: 2026-09-04` goes immediately after that `planted:` line — the same relative position the precedent used. `id`, `planted`, `planted_during`, `trigger_when` and `scope` are all left exactly as they are; the trigger conditions are now historical, and rewriting them would destroy the record of what was originally being waited on.

**Why plain `fulfilled` is honest for both.** The precedent introduced `partially-fulfilled` for a seed with a genuinely unshipped half. Neither seed here has one: every plan in each phase executed to `status: complete`, and both phases' four quality gates are closed (details below). `partially-fulfilled` would be the wrong value.

---

**SEED-001 — shipped as Phase 10, `.planning/phases/10-scheduled-quiet-hours/`, completed 2026-09-03**

Five plans, all with `status: complete` in their SUMMARY frontmatter:

- `10-01` — `server/device_config.py` gained the three registry fields (`quiet_hours_enabled`, `quiet_hours_start`, `quiet_hours_end`), the never-raising read-path helpers `normalise_quiet_hours_enabled()`/`normalise_quiet_hours_time()`, a strict pre-write gate in `save_device_config()`, and the DST-safe Europe/Paris window arithmetic `seconds_until_quiet_hours_end()` plus its epoch wrapper `quiet_hours_status()`. `load_device_config()` went from three keys to six. Commits `05ca4b5`, `715d8fb`.
- `10-02` — `server/plane/render.py` gained `_build_quiet_hours_canvas()`, rendering the locked "QUIET HOURS" / "Back at HH:MM" copy on a flat White/Black panel, dispatched *before* the empty-state branch, plus a `--state quiet_hours` preview CLI path. Commits `49b2277`, `92e2bae`.
- `10-03` — `stub-server/byos_server.py` gained `read_quiet_hours()` and `quiet_hours_sleep_s()`, and `GET /device/v1/display`'s `sleep_s` now extends past an active window. The window arithmetic is a byte-for-byte vendored duplicate (the stub server never imports `server.*`), pinned by an automated text-diff drift guard in `stub-server/test_poll_cycle.py` that was exercised as a deliberate negative control. `stub-server/VENDOR.md` records it as local modification 5. Commits `ee3c46b`, `3ea72ef`.
- `10-04` — `server/poll_loop.py`'s `run_once()` gained the early-return gate: render the quiet-hours screen exactly once at window entry, hold silently for the rest of the window without ever calling `detect.load_geofence()`/`detect.poll_current_aircraft()`, and force exactly one repaint of the live board on the first cycle after the window ends (no symmetric "waking up" screen). State lives in `poll_state.json`'s `quiet_hours_active` flag. Commits `f3bd3f3`, `e506caf`.
- `10-05` — `companion/pages/config_page.py` gained `quiet_hours_group()`, the Settings page's fourth group: an enable checkbox plus two `<input type="time">` fields, written through the page's single existing `save_device_config()` call. `.led-checkbox` was generalised to `.settings-checkbox`. Commits `80c1ff7`, `2b9367f`, `2c88cbf`.

Quality gates, all read directly:
- `10-VERIFICATION.md` — `status: passed`, `score: 27/28 must-haves verified`, `behavior_unverified: 0`, "No gaps found."
- `10-UAT.md` — `status: complete`, 2 tests, 2 passed, 0 issues.
- `10-SECURITY.md` — `status: verified`, `threats_open: 0`, 16 threats all closed, ASVS level 1.
- `10-REVIEW.md` — 0 critical, 2 warnings, 1 info.

Answers to SEED-001's own open questions, and the divergences:

1. **The seed's central design question (its item 3, option (a) stop waking entirely vs. option (b) still wake but skip the display refresh) resolved as (a) — and the seed's stated reason for hesitating about (a) turned out to be wrong.** The seed predicted (a) would mean "a bigger change to `state_machine.c`/`app_main.c`'s sleep-duration logic." ROADMAP.md's Phase 10 entry records that `/gsd-discuss-phase 10` corrected that premise: `sleep_s` is already a per-response, fully server-controlled value, so extending it needs **zero firmware change**. That is why D-01 chose the full sleep-cycle extension after all. The seed's own framing — that (a) buys the bigger battery win but costs firmware work — was half right: the win is real, the cost was not.
2. **The seed's item 4 (what the panel shows during the window) resolved as:** a dedicated one-time "QUIET HOURS / Back at HH:MM" screen rendered once at entry (D-05/D-06), held for the rest of the window, with no symmetric screen at exit (D-07) — not a blank panel and not a held previous image.
3. **The seed's trigger did not fire as written.** It said to wait for Phase 5's multi-day discharge run to produce a battery-life verdict. It did not wait — the phase was promoted at the developer's direct request on 2026-09-02, and ROADMAP.md records that D-01's choice "no longer depends on Phase 5's pending battery-discharge verdict."
4. **The seed's Notes predicted a `CFG-13`-style entry would be added to `REQUIREMENTS.md` on promotion. That did not happen.** Phase 10 shipped as an unmapped backlog phase — all five plans declare `requirements: []`, and `.planning/REQUIREMENTS.md` still contains no quiet-hours entry (independently confirmed during planning: a case-insensitive grep for "quiet" over that file returns nothing).

Still open, non-blocking, and **owned by `10-REVIEW.md`, not by this seed**: two WARNING-level findings (0 critical). Point at that file; do not restate their content.

---

**SEED-002 — shipped as Phase 11, `.planning/phases/11-web-configurable-wake-interval/`, completed 2026-09-04**

Four plans, all with `status: complete` in their SUMMARY frontmatter:

- `11-01` — `server/device_config.py` gained `WAKE_INTERVAL_MIN_S = 60` / `WAKE_INTERVAL_MAX_S = 3600`, the never-raising `normalise_wake_interval_s()`, a seventh `load_device_config()` key `wake_interval_s`, and a strict pre-write gate in `save_device_config()`. Commits `330d2f9`, `b8c4525`.
- `11-02` — `stub-server/byos_server.py` gained the fail-open `read_wake_interval_s()`, and `GET /device/v1/display`'s `sleep_s` now uses it as the base value that Phase 10's `quiet_hours_sleep_s()` extends — replacing the direct `self.args.sleep` reference. `stub-server/VENDOR.md` records it as local modification 6. Commits `e4883eb`, `4e24ef2`.
- `11-03` — `companion/pages/config_page.py` gained `wake_interval_group()`, the Settings page's fifth group and this codebase's first native `<input type="number" min="60" max="3600">`, wired through an explicit string-to-`int()` conversion gate into the page's single existing `save_device_config()` call. Commits `4753ba5`, `a203da8`.
- `11-04` — `companion/app.py` gained `SLEEP_ENV_VAR` and the fail-open `env_wake_interval_default()`, threading the deployed `SKYPANE_SLEEP_S` into the page context as `wake_interval_env_default` so the field pre-fills from the real deployed cadence, degrading to a "Uses server default" placeholder when that value is absent or out of bounds. `deploy/skypane.env.example`'s `SKYPANE_SLEEP_S` comment was corrected to describe it as an overridable fallback — with no change to its shipped value and no change to either systemd unit file. Commits `5c6db08`, `a768052`.

Quality gates, all read directly:
- `11-VERIFICATION.md` — `status: passed`, `score: 22/22 must-haves verified`, `behavior_unverified: 0`, "No gaps."
- `11-UAT.md` — `status: complete`, 1 test, 1 passed, 0 issues.
- `11-SECURITY.md` — `status: verified`, `threats_open: 0`, 16 threats all closed, ASVS level 1.
- `11-REVIEW.md` — 0 critical, 2 warnings, 1 info.

Answers to SEED-002's own open questions, and the divergences:

1. **The seed's central design question (its item 3, option (a) server returns the interval in the poll response vs. option (b) the config write restarts the service) resolved as (a), exactly as the seed itself predicted was "the more natural fit."** A saved value reaches the device as `sleep_s` on its very next `/device/v1/display` poll. No service restart, no protocol change beyond reusing the existing field, and `deploy/skypane-byos.service` untouched.
2. **The seed's item 2 ("a sane min/max — too short burns battery, too long risks staleness") resolved as 60-3600 seconds (D-02)** — the floor grounded in `firmware/main/Kconfig.projbuild`'s own `FP_MIN_REFRESH_SPACING_S` default, the one-hour ceiling developer-confirmed.
3. **The seed's item 1 predicted the field would follow the existing `normalise_*()`/`load_device_config()`/`save_device_config()` pattern "used for theme/runway/LED." It mostly did — with one deliberate exception the seed did not anticipate:** `wake_interval_s` is the only field in that registry whose unset state is `None` rather than a `DEFAULT_*` constant (D-07), because the true fallback (`SKYPANE_SLEEP_S` / `--sleep`) lives in a different OS process's argparse namespace and is not knowable from `device_config.py`.
4. **One thing shipped beyond the seed's scope.** The seed only asked for the value to be settable from the web form. Plan `11-04` additionally made the field pre-fill from the deployed `SKYPANE_SLEEP_S`, and corrected the comment in `deploy/skypane.env.example` — a file the seed itself listed as a breadcrumb.
5. **`REQUIREMENTS.md` was not extended.** Like Phase 10, Phase 11 shipped as an unmapped backlog phase; all four plans declare `requirements: []` and no wake-interval requirement ID exists.
6. **One cosmetic observation from UAT, accepted rather than fixed.** `11-UAT.md` records that the field's "Uses server default" placeholder renders visually truncated to "Uses" at both 375px and 1280px, because the native number input sizes to roughly 74px with no explicit width; the developer reviewed screenshots and explicitly accepted it as-is rather than requesting a change, so it was not filed as a gap. Worth one sentence — it is part of the shipping record.

Still open, non-blocking, and **owned by `11-REVIEW.md`, not by this seed**: two WARNING-level findings (0 critical). Point at that file; do not restate their content.

---

**One ROADMAP trap to avoid.** ROADMAP.md's Phase 11 bullet still carries a stale mid-flight parenthetical reading "4 plans across 3 waves (3/4 executed)". All four plans did complete — `11-04-SUMMARY.md` exists on disk with `status: complete` and `completed: 2026-09-04`, and `11-VERIFICATION.md` verifies must-haves from all four plans. Do not repeat the "3/4" figure; cite the four SUMMARY files instead.

**Baselines for the byte-identity checks.** `SEED-001`'s current content is at commit `05e6cf54d899de48f40bff1f64f879f99426dbb2`; `SEED-002`'s is at `f1e9f724eb643af7aa8050ffe49f67c1daf74f46`. The working tree was confirmed clean at plan time, so both resolve to exactly what is on disk now.

**Project skills.** `.claude/skills/` holds only `sketch-findings-skypane`, the companion web app's design-system reference. It governs UI implementation and does not apply to a change that touches only `.planning/seeds/*.md`. Do not update it.

</research_notes>

<tasks>

<task type="auto">
  <name>Task 1: Mark SEED-001 fulfilled, citing Phase 10 as shipping evidence</name>
  <files>.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md</files>
  <action>
Edit this file in exactly two places. Change nothing else — the H1 title line and every line from `## Why This Matters` to end of file must stay byte-identical, which the verify step checks against the pinned baseline commit `05e6cf54d899de48f40bff1f64f879f99426dbb2`.

**Frontmatter.** Change the existing `status: dormant` line to read `status: fulfilled`. Insert one new line `resolved_date: 2026-09-04` immediately after the existing `planted: 2026-09-01` line. Leave `id`, `planted`, `planted_during`, `trigger_when` and `scope` exactly as they are — the trigger condition is now historical, and rewriting it would destroy the record of what was originally being waited on. Do not reorder or reflow any existing key.

**New body section.** Insert a `## Fulfilled 2026-09-04` heading and its prose between the existing H1 title line and the existing `## Why This Matters` heading, separated from each by a blank line. This is the only section that may be added. It must state, in the dated-addendum tone the precedent seed in `<context>` demonstrates:

1. That this seed shipped in full as Phase 10, directory `.planning/phases/10-scheduled-quiet-hours/`, plans `10-01` through `10-05`, completed 2026-09-03 — so the seed is closed.
2. What each layer actually delivered, named concretely: `server/device_config.py`'s three registry fields with their never-raising read-path normalisers and strict write-path gate, plus the DST-safe Europe/Paris arithmetic `seconds_until_quiet_hours_end()` and its wrapper `quiet_hours_status()` (`10-01`); `server/plane/render.py`'s `_build_quiet_hours_canvas()` and its dispatch ahead of the empty-state branch (`10-02`); `stub-server/byos_server.py`'s `read_quiet_hours()`/`quiet_hours_sleep_s()` extending `GET /device/v1/display`'s `sleep_s`, as a vendored duplicate pinned by an automated drift guard (`10-03`); `server/poll_loop.py`'s render-once-at-entry / hold / repaint-on-exit gate in `run_once()` (`10-04`); and `companion/pages/config_page.py`'s `quiet_hours_group()`, the Settings page's fourth group (`10-05`).
3. That the evidence of record is the phase's own completed gates, cited by filename: `10-VERIFICATION.md` (`status: passed`, 27/28 must-haves, no gaps), `10-UAT.md` (complete, 2/2 passed, 0 issues), and `10-SECURITY.md` (verified, zero open threats). This is a human-signed-off result, not a code-only claim.
4. The four resolutions and divergences from `<research_notes>`, stated plainly: the option-(a)-vs-(b) question resolved as (a), **and** the seed's stated reason for hesitating about (a) — that it would need firmware sleep-logic changes — was wrong, since `sleep_s` was already a server-controlled per-response value and zero firmware change was needed; the display-state question resolved as a one-time "QUIET HOURS / Back at HH:MM" screen at entry with no symmetric screen at exit; the seed's Phase-5-battery-verdict trigger never fired, the phase having been promoted at the developer's direct request instead; and the `CFG-13`-style requirement entry the seed's own Notes anticipated was never created — the phase shipped unmapped, and `REQUIREMENTS.md` still has no quiet-hours ID.
5. One sentence noting that two non-blocking WARNING-level code-review findings (zero critical) remain open and that `10-REVIEW.md` is their authoritative home — without restating what they are. The point of the pointer is that the review file owns that text.
6. A closing line stating that everything below is the original 2026-09-01 record, retained unchanged as history.

Do not soften, hedge or add any claim beyond what `<research_notes>` establishes. Do not add a "next steps" or "future work" framing — this seed has none left. Do not repeat ROADMAP.md's stale "3/4 executed" figure, which belongs to Phase 11's entry and is wrong besides.
  </action>
  <verify>
    <automated>python3 -c "
import difflib, subprocess
P='.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md'
B='05e6cf54d899de48f40bff1f64f879f99426dbb2'
H='## Fulfilled 2026-09-04'
F='## Why This Matters'
new=open(P,encoding='utf-8').read()
old=subprocess.run(['git','show',B+':'+P],capture_output=True,text=True,check=True).stdout
L=new.splitlines()
fm=L[1:L.index('---',1)]
assert len([x for x in fm if x.startswith('status:')])==1, 'frontmatter must carry exactly one status key'
assert 'status: fulfilled' in fm, 'status line is missing or not an exact match'
assert len([x for x in fm if x.startswith('resolved_date:')])==1, 'frontmatter must carry exactly one resolved_date key'
assert 'planted: 2026-09-01' in fm, 'the original planted date must survive untouched'
assert fm[fm.index('planted: 2026-09-01')+1]=='resolved_date: 2026-09-04', 'resolved_date must sit immediately after the planted line'
h1=[x for x in old.splitlines() if x.startswith('# SEED-001')][0]
assert L.count(h1)==1, 'the original H1 title must survive exactly once, unchanged'
assert L.count(H)==1, 'need exactly one dated section heading'
assert L.count(F)==1, 'the original first body heading must survive exactly once'
assert L.index(h1)<L.index(H)<L.index(F), 'order must be H1, then the dated section, then the original body'
assert new.endswith(old[old.index(F):]), 'original body from the first heading onward is not byte-identical to baseline '+B
d=sorted(x for x in difflib.ndiff(old[:old.index(F)].splitlines(), new[:new.index(H)].splitlines()) if x[0] in '+-')
assert d==sorted(['- status: dormant','+ status: fulfilled','+ resolved_date: 2026-09-04']), 'head region changed beyond the two intended frontmatter edits: '+repr(d)
sec=new[new.index(H):new.index(F)]
for c in ['10-scheduled-quiet-hours','10-01','10-02','10-03','10-04','10-05','10-VERIFICATION.md','10-UAT.md','10-REVIEW.md','seconds_until_quiet_hours_end','quiet_hours_group','sleep_s','REQUIREMENTS.md']:
    assert c in sec, 'dated section is missing a required citation: '+c
st=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,check=True).stdout
ok=lambda p: p==P or p.startswith('.planning/quick/260904-kug') or p=='.planning/STATE.md'
stray=[l[3:] for l in st.splitlines() if l.strip() and not l.startswith('??') and not ok(l[3:])]
assert not stray, 'this task modified tracked files outside its scope: '+repr(stray)
print('OK 260904-kug task 1')
"</automated>
  </verify>
  <done>
`.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md` carries `status: fulfilled` and `resolved_date: 2026-09-04` in frontmatter, and a `## Fulfilled 2026-09-04` section between its H1 and `## Why This Matters` that names Phase 10's five plans and its three completed gate files as the shipping evidence, answers the seed's own design questions including the two places the shipped work diverged from what the seed predicted, and hands the remaining non-blocking review findings to `10-REVIEW.md`. The head region differs from baseline `05e6cf5` by exactly the two intended frontmatter lines, and the body from `## Why This Matters` onward is byte-identical. No tracked file outside this one is modified.
  </done>
</task>

<task type="auto">
  <name>Task 2: Mark SEED-002 fulfilled, citing Phase 11 as shipping evidence</name>
  <files>.planning/seeds/SEED-002-web-configurable-wake-interval.md</files>
  <action>
Edit this file in exactly two places, same discipline as Task 1 — the H1 title line and every line from `## Why This Matters` to end of file stay byte-identical, checked against the pinned baseline commit `f1e9f724eb643af7aa8050ffe49f67c1daf74f46`.

**Frontmatter.** Change the existing `status: dormant` line to read `status: fulfilled`. Insert one new line `resolved_date: 2026-09-04` immediately after the existing `planted: 2026-09-02` line. Leave `id`, `planted`, `planted_during`, `trigger_when` and `scope` exactly as they are.

**New body section.** Insert a `## Fulfilled 2026-09-04` heading and its prose between the existing H1 title line and the existing `## Why This Matters` heading, separated by blank lines. It must cover, in the same dated-addendum tone:

1. That this seed shipped in full as Phase 11, directory `.planning/phases/11-web-configurable-wake-interval/`, plans `11-01` through `11-04`, completed 2026-09-04 — so the seed is closed.
2. What each layer delivered, named concretely: `server/device_config.py`'s `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` bounds of 60 and 3600 seconds, `normalise_wake_interval_s()`, the seventh `load_device_config()` key `wake_interval_s`, and the strict pre-write gate (`11-01`); `stub-server/byos_server.py`'s fail-open `read_wake_interval_s()` feeding `GET /device/v1/display`'s `sleep_s` as the base value Phase 10's `quiet_hours_sleep_s()` extends (`11-02`); `companion/pages/config_page.py`'s `wake_interval_group()`, the Settings page's fifth group and the codebase's first native number input, wired through an explicit string-to-integer conversion gate into the page's single existing `save_device_config()` call (`11-03`); and `companion/app.py`'s `env_wake_interval_default()` reading the deployed `SKYPANE_SLEEP_S` into the page context so the field pre-fills, degrading to a "Uses server default" placeholder when that value is absent or out of bounds (`11-04`).
3. That the evidence of record is the phase's own completed gates, cited by filename: `11-VERIFICATION.md` (`status: passed`, 22/22 must-haves, no gaps), `11-UAT.md` (complete, 1/1 passed, 0 issues), and `11-SECURITY.md` (verified, zero open threats).
4. The resolutions and divergences from `<research_notes>`: the option-(a)-vs-(b) delivery question resolved as (a), exactly as this seed itself predicted was the more natural fit — the value reaches the device on its very next poll, with no service restart and `deploy/skypane-byos.service` untouched; the seed's "sane min/max" question resolved as 60-3600 seconds, the floor grounded in `firmware/main/Kconfig.projbuild`'s own `FP_MIN_REFRESH_SPACING_S` default and the one-hour ceiling developer-confirmed; and the one place the seed's prediction did not hold — it expected the field to follow the theme/runway/LED registry pattern exactly, but `wake_interval_s` is the single field whose unset state is `None` rather than a default constant, because the real fallback lives in another OS process's argparse namespace and is not knowable from that module.
5. That one thing shipped beyond this seed's own scope: the environment pre-fill, plus a corrected comment in `deploy/skypane.env.example` — a file this seed itself listed as a breadcrumb — with no change to that file's shipped value and no change to either systemd unit file. Note too that `REQUIREMENTS.md` was not extended; like Phase 10, this shipped as an unmapped backlog phase.
6. One sentence recording the single cosmetic observation from UAT that was accepted rather than fixed: the "Uses server default" placeholder renders visually truncated at the tested viewport widths because the native number input sizes narrowly, and the developer reviewed it and accepted it as-is rather than filing a gap. `11-UAT.md` is where that detail lives.
7. One sentence noting that two non-blocking WARNING-level code-review findings (zero critical) remain open and that `11-REVIEW.md` is their authoritative home — without restating what they are.
8. A closing line stating that everything below is the original 2026-09-02 record, retained unchanged as history.

Do not restate the review findings' content, and do not imply the phase is incomplete because of them — both phases passed every gate. Do not repeat ROADMAP.md's stale "(3/4 executed)" parenthetical on this phase's entry; all four plans completed, and their SUMMARY files are the evidence.
  </action>
  <verify>
    <automated>python3 -c "
import difflib, subprocess
P='.planning/seeds/SEED-002-web-configurable-wake-interval.md'
B='f1e9f724eb643af7aa8050ffe49f67c1daf74f46'
H='## Fulfilled 2026-09-04'
F='## Why This Matters'
new=open(P,encoding='utf-8').read()
old=subprocess.run(['git','show',B+':'+P],capture_output=True,text=True,check=True).stdout
L=new.splitlines()
fm=L[1:L.index('---',1)]
assert len([x for x in fm if x.startswith('status:')])==1, 'frontmatter must carry exactly one status key'
assert 'status: fulfilled' in fm, 'status line is missing or not an exact match'
assert len([x for x in fm if x.startswith('resolved_date:')])==1, 'frontmatter must carry exactly one resolved_date key'
assert 'planted: 2026-09-02' in fm, 'the original planted date must survive untouched'
assert fm[fm.index('planted: 2026-09-02')+1]=='resolved_date: 2026-09-04', 'resolved_date must sit immediately after the planted line'
h1=[x for x in old.splitlines() if x.startswith('# SEED-002')][0]
assert L.count(h1)==1, 'the original H1 title must survive exactly once, unchanged'
assert L.count(H)==1, 'need exactly one dated section heading'
assert L.count(F)==1, 'the original first body heading must survive exactly once'
assert L.index(h1)<L.index(H)<L.index(F), 'order must be H1, then the dated section, then the original body'
assert new.endswith(old[old.index(F):]), 'original body from the first heading onward is not byte-identical to baseline '+B
d=sorted(x for x in difflib.ndiff(old[:old.index(F)].splitlines(), new[:new.index(H)].splitlines()) if x[0] in '+-')
assert d==sorted(['- status: dormant','+ status: fulfilled','+ resolved_date: 2026-09-04']), 'head region changed beyond the two intended frontmatter edits: '+repr(d)
sec=new[new.index(H):new.index(F)]
for c in ['11-web-configurable-wake-interval','11-01','11-02','11-03','11-04','11-VERIFICATION.md','11-UAT.md','11-REVIEW.md','wake_interval_s','read_wake_interval_s','wake_interval_group','env_wake_interval_default','SKYPANE_SLEEP_S','3600','REQUIREMENTS.md']:
    assert c in sec, 'dated section is missing a required citation: '+c
st=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,check=True).stdout
ok=lambda p: p==P or p.startswith('.planning/quick/260904-kug') or p=='.planning/STATE.md'
stray=[l[3:] for l in st.splitlines() if l.strip() and not l.startswith('??') and not ok(l[3:])]
assert not stray, 'this task modified tracked files outside its scope: '+repr(stray)
print('OK 260904-kug task 2')
"</automated>
  </verify>
  <done>
`.planning/seeds/SEED-002-web-configurable-wake-interval.md` carries `status: fulfilled` and `resolved_date: 2026-09-04` in frontmatter, and a `## Fulfilled 2026-09-04` section between its H1 and `## Why This Matters` that names Phase 11's four plans and its three completed gate files as the shipping evidence, records the 60-3600s bounds decision and the `None`-sentinel divergence, notes the out-of-scope environment pre-fill and the accepted cosmetic UAT observation, and hands the remaining non-blocking review findings to `11-REVIEW.md`. The head region differs from baseline `f1e9f72` by exactly the two intended frontmatter lines, and the body from `## Why This Matters` onward is byte-identical. No tracked file outside this one is modified.
  </done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| (none crossed) | This plan edits two markdown planning artifacts. No runtime code path, no network call, no user input, no credential, no dependency install. The only "input" is the developer's own task description, and every factual claim derived from it was independently re-verified against the repo during planning. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-kug-01 | Tampering | The two seeds' original planted record | low | mitigate | Each task's `<verify>` asserts byte-identity of everything from `## Why This Matters` onward against a pinned baseline commit (`05e6cf5`, `f1e9f72`), AND runs a `difflib.ndiff` over the head region asserting it differs by exactly three lines (one changed `status`, one added `resolved_date`). Silently trimming, reflowing, retitling or rewriting either the original body or the H1 is a hard failure, not a review judgement call. |
| T-kug-02 | Repudiation | Shipped-work citations in the new dated sections | medium | mitigate | Every plan ID, phase directory, symbol name, gate filename and status value in `<research_notes>` was read directly out of the nine phase-10 and eight phase-11 artifacts during planning — not inferred from ROADMAP prose, which is independently known to carry a stale "3/4 executed" figure the plan explicitly warns against. Each task's `<verify>` re-asserts the citation strings are present, so an executor cannot quietly drop the provenance that makes the claim auditable. |
| T-kug-03 | Spoofing | Over-claiming completion on a phase that is not actually closed | medium | mitigate | The claim "shipped in full" rests on four independent gates per phase, each read at plan time and each required to be cited by filename in the seed text: VERIFICATION (`status: passed`, zero gaps), UAT (`status: complete`, zero issues), SECURITY (`status: verified`, `threats_open: 0`), REVIEW (zero critical). Both seeds must additionally point at their `*-REVIEW.md` for the warnings that do remain open, so neither file can read as "nothing left anywhere." |
| T-kug-04 | Elevation of Privilege | Scope creep from a docs-only change into code, requirements or roadmap | low | mitigate | Both tasks' `<verify>` inspects `git status --porcelain` and fails if any tracked path other than the task's own target file (plus this quick task's own directory and STATE.md) is modified — catching accidental edits to `REQUIREMENTS.md`, `ROADMAP.md`, the six other seeds, the `sketch-findings-skypane` skill, or any source file. Untracked (`??`) paths are deliberately excluded from that gate: they cannot be introduced by an `Edit` to a tracked file, and the same check in quick task `260902-ipj` produced a documented false alarm on pre-existing untracked files. |
| T-kug-05 | Information Disclosure | `.planning/` content in a repo that may later be published | low | accept | The new sections add no credential, hostname, token or secret — only file paths, plan IDs, symbol names and status values already present throughout `.planning/` and the source tree. Accepting adds no new exposure over the existing baseline. |

No package-manager install task exists in this plan — nothing is installed, downloaded or vendored — so no `T-kug-SC` supply-chain row applies and no package-legitimacy checkpoint is required.
</threat_model>

<verification>
After both tasks, confirm as a set:

1. Both tasks' `<automated>` checks pass.
2. Exactly the two target seeds changed, and the other six are untouched:
   `test "$(git status --porcelain .planning/seeds/ | awk '{print $2}' | sort | tr '\n' ' ')" = ".planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md .planning/seeds/SEED-002-web-configurable-wake-interval.md "`
3. No source tree, requirements, roadmap or skill file moved:
   `test -z "$(git status --porcelain -- server/ companion/ stub-server/ firmware/ deploy/ scripts/ .claude/ .planning/REQUIREMENTS.md .planning/ROADMAP.md)"`
4. Both seeds now carry the same honest status, and neither retains the dormant value:
   `python3 -c "
def s(p):
    return [l for l in open(p,encoding='utf-8').read().splitlines() if l.startswith('status:')][0]
a=s('.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md')
b=s('.planning/seeds/SEED-002-web-configurable-wake-interval.md')
assert a=='status: fulfilled' and b=='status: fulfilled', 'both seeds must read exactly status: fulfilled, got '+repr((a,b))
print('OK both seeds fulfilled')
"`
5. Read both new sections once end to end and confirm no sentence asserts anything beyond `<research_notes>` — in particular that neither implies a requirement ID was created, that neither restates the open review warnings instead of pointing at them, and that neither repeats ROADMAP.md's stale "3/4 executed" figure.
</verification>

<success_criteria>
- Both seeds' frontmatter reads `status: fulfilled` with `resolved_date: 2026-09-04`, every other planted key untouched.
- Each seed opens with a dated section naming the real phase, plans, symbols and completed gate files that shipped its idea, and answering the seed's own open design questions — including where the answer contradicts what the seed predicted.
- Neither seed over-claims: each points at its phase's `*-REVIEW.md` for the non-blocking findings that remain open.
- Both original bodies are byte-identical to their pinned baselines from `## Why This Matters` onward, and both H1 titles survive unchanged.
- The diff touches exactly two files. No code, no `REQUIREMENTS.md`, no `ROADMAP.md`, no other seed, no skill file.
</success_criteria>

<output>
Create `.planning/quick/260904-kug-mark-seed-001-and-seed-002-as-fulfilled-/260904-kug-SUMMARY.md` when done.

Note for the summary: `requirements.mark-complete QT-kug-01 QT-kug-02` will return `not_found`. These are quick-task traceability tags in this plan's own frontmatter, not `REQUIREMENTS.md` entries — the same precedent quick task `260902-ipj` recorded. That is expected, and `REQUIREMENTS.md` is correctly left untouched.
</output>
