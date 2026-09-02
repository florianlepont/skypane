---
phase: quick-260902-ipj
plan: 01
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - .planning/seeds/bring-up-debug-led-remote-toggle.md
  - .planning/seeds/on-device-fault-icon.md
autonomous: true
requirements: [QT-ipj-01, QT-ipj-02]
user_setup: []

must_haves:
  truths:
    - "A reader opening `.planning/seeds/bring-up-debug-led-remote-toggle.md` learns from the frontmatter alone that the idea shipped, and from the first body section exactly which quick task shipped the LED and which phase/plans shipped the remote toggle — without having to search STATE.md or ROADMAP.md to find out."
    - "A reader opening `.planning/seeds/on-device-fault-icon.md` learns that only half of it shipped: the frontmatter status is the partial value, never the plain fulfilled one, and the first body section names CFG-05 as delivered and DEVICE-06 as still open v2 backlog."
    - "That second seed and `.planning/REQUIREMENTS.md` cannot drift apart, because the seed explicitly names DEVICE-06's 'On-Device Fault Fallback' entry as the authoritative home of the remaining scope rather than restating that scope itself."
    - "Both seeds' original 2026-08-27 bodies survive byte-for-byte below the new dated section — the record of what was believed and decided at planting time is superseded in place, never deleted, trimmed or rewritten. This is machine-checked against each file's own baseline blob, not trusted to review."
    - "Every shipped-work claim in the two new sections is traceable to a real artifact on disk: the quick-task directory, the plan and summary files, the requirement entry and the commit that fixed the reviewed badge bugs all exist and say what the seed says they say."
    - "No code file, no `REQUIREMENTS.md`, no `ROADMAP.md`, and none of the four genuinely-dormant seeds in `.planning/seeds/` changes — this plan is documentation-only, and its own verification fails if anything else in the working tree moves."
  artifacts:
    - path: ".planning/seeds/bring-up-debug-led-remote-toggle.md"
      provides: "Frontmatter `status`/`resolved_date` fields plus a leading dated `## Fulfilled 2026-09-02` section; original body retained verbatim below"
    - path: ".planning/seeds/on-device-fault-icon.md"
      provides: "Frontmatter `status`/`resolved_date` fields plus a leading dated `## Partially fulfilled 2026-09-02` section that hands the open half to DEVICE-06; original body retained verbatim below"
  key_links:
    - "`on-device-fault-icon.md`'s new section -> `.planning/REQUIREMENTS.md`'s DEVICE-06 entry (lines ~72-76, 'On-Device Fault Fallback') — the single link that stops the seed and the requirements file from drifting. If DEVICE-06 is ever renamed, promoted or closed, this pointer is the first thing to re-check."
    - "`bring-up-debug-led-remote-toggle.md`'s new section -> `.planning/quick/260827-wo4-add-a-bring-up-debug-feedback-led-to-the/` (LED half, completed 2026-08-27) and `.planning/phases/06.2-led-enable-disable-toggle/06.2-01-PLAN.md` + `06.2-02-PLAN.md` (remote-toggle half, completed 2026-08-28)."
    - "Both new sections -> the pinned baseline blobs `09d469e` (LED seed) and `8be8510` (fault seed) — each task's `<verify>` diffs the post-`## Context` tail against its baseline, so the 'supersede, don't delete' promise is enforced mechanically."
    - "The new `status:` values -> `SEED-001-scheduled-quiet-hours-curfew-pause.md`'s `status: dormant` — the convention these two older-format seeds are being brought into. `partially-fulfilled` is a deliberate third value in that vocabulary, introduced because neither `dormant` nor `fulfilled` is honest for half-shipped work."
---

<objective>
Close out the two seeds in `.planning/seeds/` whose ideas have actually shipped but whose files still read as open, unplanted ideas — one fully, one only half.

Purpose: `.planning/seeds/` is the project's idea backlog. Two of its six files are stale in a way that actively misleads: a future `/gsd-review-backlog` or `/gsd-new-milestone` surfacing run would re-propose work that is already on real hardware. Closing them keeps the backlog honest, and — for the half-shipped one — hands the still-open remainder to the one place that formally owns it (`REQUIREMENTS.md`'s DEVICE-06) so the two documents cannot drift.

Output: two edited markdown files. Nothing else. No code, no `REQUIREMENTS.md`, no `ROADMAP.md`.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@.planning/seeds/bring-up-debug-led-remote-toggle.md
@.planning/seeds/on-device-fault-icon.md
@.planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md
</context>

<research_notes>

Everything below was cross-checked against the repo during planning. Do not re-derive it; do not restate anything beyond it. If a claim you want to write is not in this block, it was not verified — leave it out.

**Seed 1 — LED, both halves confirmed shipped**

- LED half: quick task `260827-wo4`, directory `.planning/quick/260827-wo4-add-a-bring-up-debug-feedback-led-to-the/`, `260827-wo4-SUMMARY.md` frontmatter `completed: 2026-08-27`. Its `provides:` block states: the `fp_led` module (`fp_led_on`/`fp_led_off`) driving the XIAO ESP32-S3's built-in GPIO21 User LED; two unconditional wake-cycle call sites (boot-time on, pre-sleep off); and the `led_enabled` wire field end-to-end (stub server -> firmware parse -> conditional off-early consumer), described there as "the firmware-side half of a future remote toggle". `REQUIREMENTS.md`'s Out-of-Scope "Status LEDs" row independently cites `firmware/main/led.c` and plan `260827-wo4`.
- Remote-toggle half: Phase 06.2 "LED enable/disable toggle", directory `.planning/phases/06.2-led-enable-disable-toggle/`, plans `06.2-01-PLAN.md` and `06.2-02-PLAN.md`, both `- [x]` in ROADMAP.md. `06.2-02-SUMMARY.md` frontmatter `completed: 2026-08-28`.
- 06.2-01 shipped (from its own `provides:`): `server/device_config.py`'s `DEFAULT_LED_ENABLED` + `normalise_led_enabled()`; `load_device_config()`/`save_device_config()` extended with a third `led_enabled` field; `companion/pages/config_page.py`'s `led_fieldset()`/`led_section()` behind their own dedicated `/config-led` form; `companion/app.py`'s `LED_ROUTE` behind `require_session()`; and `byos_server.py`'s `read_led_enabled()` feeding the `/display` response.
- 06.2-02 was a blocking developer checkpoint, signed off: STATE.md records both the cross-process toggle (Part A, 6/6 sub-checks) and the real physical LED on deployed hardware (Part B) confirmed.
- Resolved open question: ROADMAP.md's Phase 06.2 completion note (2026-08-28) records a genuine "LED still lit" report from the first hardware observation round, investigated and root-caused as the firmware unconditionally lighting the LED during the WiFi-connect+poll window regardless of `led_enabled` (existing `app_main.c`/`state_machine.c` design). Second-round observation confirmed the toggle works as designed; no code changed. So the seed's undecided "trigger semantics" question resolved as: lit during the active wake window, with `led_enabled` governing early extinction — not a per-wake gate on lighting at all.
- Divergence from the seed's own speculation, worth recording honestly: the seed predicted the toggle would converge with CFG-03 (device health). It did not — ROADMAP.md line 394 records 06.2's locked decision D-01 as giving the toggle its **own dedicated Config-page section**.
- Also resolved: the seed flagged GPIO21's identity as the built-in User LED as web-sourced and not yet confirmed on real hardware. 06.2-02's Part B physical confirmation settles it.

**Seed 2 — fault icon, server half shipped, device half open**

- Server half (CFG-05) shipped in Phase 6: plan `06-02` (`server/plane/detect.py` runway-parameterisation + the diagnostics signal, CFG-05/CFG-12) and plan `06-06` (`server/plane/render.py`'s `draw_source_fault_badge()`, CFG-05). Both `06-02-SUMMARY.md` and `06-06-SUMMARY.md` exist.
- `server/plane/render.py:310` defines `SOURCE_FAULT_TEXT = "ADS-B source unavailable — check the companion page"`. `draw_source_fault_badge()` is at line 658 and draws a triangular outline alert glyph plus that caption.
- The seed's own false-alarm guard held: plan `06-10` shipped `server/poll_loop.py`'s `_classify_source_fault()`, which derives the alert only from an all-providers-failed diagnostics report and never from an empty selection — exactly the Empty-state conflation the seed warned against.
- The destination the caption points at exists: plan `06-08` shipped `companion/pages/health_page.py` including CFG-05's source-fault landing block.
- Two real bugs in the badge were found by Phase 8's code review, `.planning/phases/08-.../08-REVIEW.md`: **WR-01** — the badge called `_font(TOP_TAG_FONT)` directly and so bypassed the phase's per-theme weight-resolution contract that every other active-state text role had been moved onto; **WR-02** — the exclamation mark's dot was drawn as a degenerate zero-length `ImageDraw.line()`, which Pillow paints as a single pixel rather than expanding by `width`, so the dot was all but invisible on a 1200x1600 panel. Both were fixed in commit `9aa217a` ("fix(08): source-fault badge respects theme weight, exclamation dot is visible"); today's `render.py` carries `draw_source_fault_badge(canvas, ink_idx, weight="bold")` and an ellipse-drawn dot with a `code-review WR-02` rationale comment.
- Device half NOT shipped. It is formalised as **DEVICE-06** in `.planning/REQUIREMENTS.md`'s "On-Device Fault Fallback" section (lines ~72-76), still under v2/deferred: "When the device has failed to reach the server for 2+ consecutive poll attempts (`backoff_n >= 2`), it renders a small local fallback screen (solid fill + pre-baked alert icon) directly in firmware via the existing `fp_panel_draw()` call, without needing a successful server round-trip." That entry already cites this seed file for its full design rationale — so the pointer this plan adds closes the loop in the other direction. The `backoff_n >= 2` trigger the seed decided carried into the requirement verbatim.
- Still genuinely unresolved (because DEVICE-06 has not been built): whether CFG-05's badge glyph and DEVICE-06's local fallback icon should be the same glyph.

**Style precedent to match — dated addendum, supersede without deleting**

`server/plane/enrich.py`'s `"KLJ": "KlasJet"` comment block (lines ~584-611), as edited 2026-09-02. Its shape: (1) lead with the dated resolution stated plainly, naming what the new evidence is and explicitly whether it confirms or contradicts the prior framing; (2) a `SUPERSEDED 2026-09-02` marker line saying the text below is the pre-supersession record, kept as history, whose framing no longer applies; (3) the original record, unchanged; (4) where useful, a forward-looking pointer for whoever revisits. `server/test_poll_loop.py`'s `_DEFAULT_CONFIG_DIGEST` provenance block (lines ~247-312) is the same discipline applied to a pinned value: each re-pin appends a dated entry naming its cause rather than overwriting the previous reasoning.

Match that tone: factual, dated, specific about what the evidence of record actually is, and never quietly erasing what was believed before.

</research_notes>

<tasks>

<task type="auto">
  <name>Task 1: Mark the bring-up LED seed fulfilled, both halves cited</name>
  <files>.planning/seeds/bring-up-debug-led-remote-toggle.md</files>
  <action>
Edit this file in two places. Change nothing else in it — every line from the `## Context` heading to end of file must stay byte-identical, which the verify step checks against the pinned baseline blob `09d469e2339b8c35c861625c44470824cf3423b1`.

**Frontmatter.** Insert one new line `status: fulfilled` immediately after the existing single-line `title:` key, mirroring SEED-001's convention of carrying `status` as the second key. Insert one new line `resolved_date: 2026-09-02` immediately after the existing `planted_date: 2026-08-27` line, i.e. as the last key before the closing `---`. Leave `title`, the `trigger_condition: >` folded block and `planted_date` exactly as they are — the trigger condition is now historical, and rewriting it would destroy the record of what was originally being waited on. Do not reorder or reflow any existing key.

**New body section.** Insert a `## Fulfilled 2026-09-02` heading and its prose directly above the existing `## Context` heading, separated from it by a blank line. This is the only section that may be added. It must state, in the dated-addendum tone of `enrich.py`'s KLJ block described in `<research_notes>`:

1. That both halves this seed proposed have shipped, so the seed is closed.
2. The LED half — quick task `260827-wo4` (completed 2026-08-27), which shipped the `fp_led` module (`fp_led_on()`/`fp_led_off()`) driving the built-in GPIO21 User LED, its two unconditional wake-cycle call sites, and the `led_enabled` field on the `/device/v1/display` wire together with the firmware's parse-and-obey half.
3. The remote-toggle half — Phase 06.2 "LED enable/disable toggle", plans `06.2-01-PLAN.md` and `06.2-02-PLAN.md`, completed 2026-08-28. Name the server/web side concretely: `server/device_config.py`'s `DEFAULT_LED_ENABLED` and `normalise_led_enabled()`, the companion Config page's LED section behind its own `/config-led` route, and `byos_server.py`'s `read_led_enabled()` feeding the value into the `/display` response. Note that `06.2-02-SUMMARY.md` records a blocking developer sign-off including confirmation of the real physical LED on deployed hardware — this is the evidence of record, not a code-only claim.
4. That two of the seed's own listed open questions are now answered: GPIO21's identity as the built-in User LED, flagged here as web-sourced and unconfirmed, was confirmed on real hardware by 06.2-02's Part B; and the undecided trigger semantics resolved as "lit for the active wake window, with `led_enabled` governing early extinction", the resolution that ROADMAP.md's Phase 06.2 completion note records after root-causing a real "LED still lit" observation report as expected firmware behaviour rather than a defect.
5. One honest divergence: this seed predicted the toggle would converge with CFG-03 (device health). It shipped instead as its own dedicated Config-page section, per Phase 06.2's locked decision D-01.
6. A closing line stating that everything below is the original 2026-08-27 record, retained unchanged as history.

Do not soften, hedge or add any claim beyond what `<research_notes>` establishes, and do not add a "next steps" or "future work" framing — this seed has none left.
  </action>
  <verify>
    <automated>python3 -c "
import subprocess
P='.planning/seeds/bring-up-debug-led-remote-toggle.md'
B='09d469e2339b8c35c861625c44470824cf3423b1'
new=open(P,encoding='utf-8').read()
old=subprocess.run(['git','show',B+':'+P],capture_output=True,text=True,check=True).stdout
L=new.splitlines()
fm=L[1:L.index('---',1)]
assert len([x for x in fm if x.startswith('status:')])==1, 'frontmatter must carry exactly one status key'
assert 'status: fulfilled' in fm, 'frontmatter status line is missing or not an exact match'
assert len([x for x in fm if x.startswith('resolved_date:')])==1, 'frontmatter must carry exactly one resolved_date key'
assert 'resolved_date: 2026-09-02' in fm, 'resolved_date must be 2026-09-02'
assert 'planted_date: 2026-08-27' in fm, 'the original planted_date must survive untouched'
assert L.count('## Fulfilled 2026-09-02')==1, 'need exactly one dated section heading'
assert L.count('## Context')==1, 'the original Context heading must survive exactly once'
assert L.index('## Fulfilled 2026-09-02')<L.index('## Context'), 'the dated section must sit above the original body'
tail=old[old.index('## Context'):]
assert new.endswith(tail), 'original body from the Context heading onward is not byte-identical to baseline '+B
sec=new[new.index('## Fulfilled 2026-09-02'):new.index('## Context')]
for c in ['260827-wo4','06.2-01-PLAN.md','06.2-02-PLAN.md','2026-08-28','GPIO21','led_enabled','CFG-03']:
    assert c in sec, 'dated section is missing a required citation: '+c
st=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,check=True).stdout
ok=lambda p: p==P or p.startswith('.planning/quick/260902-ipj') or p=='.planning/STATE.md'
stray=[l[3:] for l in st.splitlines() if l.strip() and not ok(l[3:])]
assert not stray, 'this task changed files outside its scope: '+repr(stray)
print('OK 260902-ipj task 1')
"</automated>
  </verify>
  <done>
`.planning/seeds/bring-up-debug-led-remote-toggle.md` carries `status: fulfilled` and `resolved_date: 2026-09-02` in frontmatter and a `## Fulfilled 2026-09-02` section above `## Context` that names quick task `260827-wo4` and Phase 06.2's two plans as the shipping evidence. The file's original body from `## Context` onward is byte-identical to baseline `09d469e`. No other file in the working tree is modified.
  </done>
</task>

<task type="auto">
  <name>Task 2: Mark the fault-icon seed partially fulfilled, hand the open half to DEVICE-06</name>
  <files>.planning/seeds/on-device-fault-icon.md</files>
  <action>
Edit this file in two places, same discipline as Task 1 — every line from `## Context` to end of file stays byte-identical, checked against the pinned baseline blob `8be851010aaa735635c2f4b4b2dce3bd28b98081`.

**Frontmatter.** Insert one new line `status: partially-fulfilled` immediately after the existing single-line `title:` key. Insert one new line `resolved_date: 2026-09-02` immediately after the existing `planted_date: 2026-08-27` line. `partially-fulfilled` is a deliberately new third value alongside SEED-001's `dormant` — the plain fulfilled value would be a false claim here, since only one of this seed's two halves shipped. `resolved_date` refers to the fulfilled half only; say so in the body section rather than in a frontmatter comment. Leave `title`, the `trigger_condition: >` folded block and `planted_date` exactly as they are.

**New body section.** Insert a `## Partially fulfilled 2026-09-02` heading and its prose directly above the existing `## Context` heading, separated by a blank line. It must cover, in the same dated-addendum tone:

1. That this seed always covered two distinct halves and exactly one of them has shipped — lead with that, so no reader mistakes the dated heading for a full close-out.
2. **Shipped: the server-side half (CFG-05).** Phase 6, plans `06-02` (`server/plane/detect.py`'s runway-parameterisation and the diagnostics signal) and `06-06` (`server/plane/render.py`'s `draw_source_fault_badge()`, which draws a triangular alert glyph beside the `SOURCE_FAULT_TEXT` caption reading "ADS-B source unavailable — check the companion page"). Record that the narrow scoping this seed insisted on genuinely held: plan `06-10`'s `_classify_source_fault()` in `server/poll_loop.py` derives the alert only from an all-providers-failed diagnostics report and never from an empty selection, so the normal Empty state cannot trigger it — the false-alarm trap this seed was written to avoid. Note that the destination the caption points users at exists: plan `06-08` shipped `companion/pages/health_page.py`'s source-fault landing block.
3. **Two real bugs found later, both fixed.** Phase 8's code review (`08-REVIEW.md`) found WR-01, the badge bypassing that phase's per-theme font-weight resolution contract that every other active-state text role had been moved onto; and WR-02, the exclamation mark's dot drawn as a degenerate zero-length line, which Pillow paints as a single pixel rather than expanding it by `width`, leaving the dot all but invisible on the panel. Both were fixed in commit `9aa217a`. Worth recording because neither was caught by the render suite at the time.
4. **Still open: the device-local half.** State plainly that it has not shipped and that its scope now lives formally as `DEVICE-06` in `.planning/REQUIREMENTS.md`'s "On-Device Fault Fallback" v2 section — that entry, not this seed, is the authoritative home for the remaining work, and this seed should not be the place anyone reads to find out what is left to build. Note the `backoff_n >= 2` trigger decided in this seed carried into DEVICE-06 verbatim, and that DEVICE-06's own entry already cites this file for full design rationale, so the two documents now point at each other.
5. That one of this seed's listed open questions stays genuinely open precisely because DEVICE-06 is unbuilt: whether CFG-05's badge glyph and DEVICE-06's local fallback icon should be the same glyph.
6. A closing line stating that everything below is the original 2026-08-27 record, retained unchanged as history.

Do not edit `.planning/REQUIREMENTS.md` — the pointer is one-directional from this file, and DEVICE-06's own entry already carries the reciprocal reference. Do not restate DEVICE-06's requirement text in full beyond the `backoff_n >= 2` trigger note; the whole point of the pointer is that the requirement file owns that text.
  </action>
  <verify>
    <automated>python3 -c "
import subprocess
P='.planning/seeds/on-device-fault-icon.md'
B='8be851010aaa735635c2f4b4b2dce3bd28b98081'
new=open(P,encoding='utf-8').read()
old=subprocess.run(['git','show',B+':'+P],capture_output=True,text=True,check=True).stdout
L=new.splitlines()
fm=L[1:L.index('---',1)]
assert len([x for x in fm if x.startswith('status:')])==1, 'frontmatter must carry exactly one status key'
assert 'status: partially-fulfilled' in fm, 'status must be the partial value, exactly matched'
assert len([x for x in fm if x.startswith('resolved_date:')])==1, 'frontmatter must carry exactly one resolved_date key'
assert 'resolved_date: 2026-09-02' in fm, 'resolved_date must be 2026-09-02'
assert 'planted_date: 2026-08-27' in fm, 'the original planted_date must survive untouched'
assert L.count('## Partially fulfilled 2026-09-02')==1, 'need exactly one dated section heading'
assert L.count('## Context')==1, 'the original Context heading must survive exactly once'
assert L.index('## Partially fulfilled 2026-09-02')<L.index('## Context'), 'the dated section must sit above the original body'
tail=old[old.index('## Context'):]
assert new.endswith(tail), 'original body from the Context heading onward is not byte-identical to baseline '+B
sec=new[new.index('## Partially fulfilled 2026-09-02'):new.index('## Context')]
for c in ['CFG-05','DEVICE-06','.planning/REQUIREMENTS.md','06-02','06-06','06-10','draw_source_fault_badge','08-REVIEW.md','9aa217a','backoff_n']:
    assert c in sec, 'dated section is missing a required citation: '+c
st=subprocess.run(['git','status','--porcelain'],capture_output=True,text=True,check=True).stdout
ok=lambda p: p==P or p.startswith('.planning/quick/260902-ipj') or p=='.planning/STATE.md'
stray=[l[3:] for l in st.splitlines() if l.strip() and not ok(l[3:])]
assert not stray, 'this task changed files outside its scope: '+repr(stray)
print('OK 260902-ipj task 2')
"</automated>
  </verify>
  <done>
`.planning/seeds/on-device-fault-icon.md` carries `status: partially-fulfilled` and `resolved_date: 2026-09-02` in frontmatter and a `## Partially fulfilled 2026-09-02` section above `## Context` that names CFG-05's shipping evidence (plans `06-02`/`06-06`, the `06-10` false-alarm guard, the `08-REVIEW.md` WR-01/WR-02 fixes) and points the still-open device-local half at `.planning/REQUIREMENTS.md`'s DEVICE-06. The file's original body from `## Context` onward is byte-identical to baseline `8be8510`. No other file in the working tree is modified.
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
| T-ipj-01 | Tampering | The two seed files' original historical record | low | mitigate | Each task's `<verify>` diffs everything from `## Context` onward against a pinned baseline blob (`09d469e`, `8be8510`) and fails on any byte difference — silently trimming, reflowing or rewriting the original body is a hard failure, not a review judgement call. |
| T-ipj-02 | Repudiation | Shipped-work citations in the new dated sections | medium | mitigate | Every plan ID, quick-task ID, date, symbol name, requirement ID and commit SHA in `<research_notes>` was cross-checked during planning against STATE.md, ROADMAP.md, REQUIREMENTS.md, the phase SUMMARY frontmatter, `server/plane/render.py`, `08-REVIEW.md` and `git log`. Each task's `<verify>` re-asserts the citation strings are present, so an executor cannot quietly drop the provenance that makes the claim auditable. |
| T-ipj-03 | Information Disclosure | `.planning/` content committed to a repo that may later be published | low | accept | The new sections add no credential, hostname, token or secret — only file paths, plan IDs and symbol names already present throughout `.planning/` and the source tree. Accepting adds no new exposure over the existing baseline. |
| T-ipj-04 | Elevation of Privilege | Scope creep from a docs-only change into code or requirements files | low | mitigate | Both tasks' `<verify>` inspects `git status --porcelain` and fails if any path other than the task's own target file (plus this quick task's own directory and STATE.md) is dirty — catching accidental edits to `REQUIREMENTS.md`, `ROADMAP.md`, `render.py`, `enrich.py` or the four dormant seeds. |

No package-manager install task exists in this plan — nothing is installed, downloaded or vendored — so no `T-ipj-SC` supply-chain row applies and no package-legitimacy checkpoint is required.
</threat_model>

<verification>
After both tasks, confirm as a set:

1. Both tasks' `<automated>` checks pass.
2. Exactly two seed files changed, and the other four are untouched:
   `test "$(git diff --name-only $(git log -n1 --format=%H -- .planning/seeds/SEED-001-scheduled-quiet-hours-curfew-pause.md)..HEAD -- .planning/seeds/ | sort | tr '\n' ' ')" = ".planning/seeds/bring-up-debug-led-remote-toggle.md .planning/seeds/on-device-fault-icon.md "`
3. Neither requirements nor roadmap moved:
   `test -z "$(git status --porcelain .planning/REQUIREMENTS.md .planning/ROADMAP.md)"`
4. The two status values differ from each other — the half-shipped seed must not have been quietly upgraded to match the fully-shipped one:
   `python3 -c "
import re
def s(p):
    return [l for l in open(p,encoding='utf-8').read().splitlines() if l.startswith('status:')][0]
a=s('.planning/seeds/bring-up-debug-led-remote-toggle.md')
b=s('.planning/seeds/on-device-fault-icon.md')
assert a!=b, 'the two seeds must not share a status value: '+a
assert b.endswith('partially-fulfilled'), 'the half-shipped seed carries the wrong status: '+b
print('OK status values are distinct and honest')
"`
5. Read both new sections once end to end and confirm no sentence asserts functionality beyond `<research_notes>` — in particular that nothing implies DEVICE-06 shipped.
</verification>

<success_criteria>
- Both seeds' frontmatter carries an accurate `status` plus `resolved_date: 2026-09-02`, and the two status values are different from each other.
- Each seed opens with a dated section naming the real artifacts that shipped its idea, and — for the fault-icon seed — the real requirement that owns what did not.
- Both original bodies are byte-identical to their pinned baselines from `## Context` onward.
- The diff touches exactly two files. No code, no `REQUIREMENTS.md`, no `ROADMAP.md`, no other seed.
</success_criteria>

<output>
Create `.planning/quick/260902-ipj-archive-2-fulfilled-seeds-bring-up-led-r/260902-ipj-SUMMARY.md` when done.

Note for the summary: `requirements.mark-complete QT-ipj-01 QT-ipj-02` will return `not_found`. These are quick-task traceability tags in this plan's own frontmatter, not `REQUIREMENTS.md` entries — the same precedent every prior 06.x/08.x decimal-phase plan recorded in STATE.md. That is expected, and `REQUIREMENTS.md` is correctly left untouched.
</output>
