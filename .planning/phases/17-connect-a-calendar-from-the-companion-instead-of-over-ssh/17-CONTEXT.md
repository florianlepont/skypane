# Phase 17: Connect a calendar from the companion instead of over SSH - Context

**Gathered:** 2026-09-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Phase 16 built calendar-linked flight highlighting end to end — fetch, iCal parse, registry,
matching, theme resolution, Settings copy — and then put its single input, the feed URL, in an
environment variable edited over SSH. This phase moves that input into the companion's Settings
page so the person the feature was built for can actually connect a calendar.

**In scope:** the write-only field and its status states; the on-disk handoff between the two
processes; retiring the environment variable; disconnect semantics including what happens to
already-fetched flights; and the immediate sync on save with its reported outcome.

**Out of scope:** anything about how a calendar *matches* a flight. The match key, the tolerance
window, the retention window, the entry cap, the SSRF gate, the theme resolver's precedence and
the rendered copy deck are all Phase 16's and stay untouched. This phase changes where the URL
comes from and nothing about what is done with it.

</domain>

<decisions>
## Implementation Decisions

### Where the secret lives, and how it is protected

- **D-01: The URL lives in a dedicated file in `state_dir`, created explicitly at mode `0600` —
  the temporary file included.** Chosen over a dedicated directory outside `state_dir` and over
  a field in `device_config.json`.

  The reason this decision needed making at all, and the trap it exists to defuse: **no code in
  this project has ever set a file mode.** Every state write goes through the same
  tmp-write-then-`os.replace()` idiom, copied verbatim from `colour_rules.py` into
  `calendar_rules.write_calendar_registry()` and elsewhere, and every one of them creates its
  file at the process umask — `0644` in practice. Meanwhile `deploy/provision.sh:76` runs
  `chmod g+ws` on `STATE_DIR` and `usermod -aG skypane caddy`, so files there carry group
  `skypane` and Caddy — the internet-facing reverse proxy — is in that group. Copying the house
  idiom for this file would therefore deposit the calendar URL group-readable by Caddy.
  `skypane.env` is `0600` and escapes this entirely, which is the one genuine security
  regression available in this phase.

  Two consequences the planner must carry, not infer:
  1. The mode must be set **at creation** of the temporary file — `os.open(tmp, O_WRONLY |
     O_CREAT | O_EXCL, 0o600)` — never `chmod` after writing, which leaves a window where the
     file exists at `0644`.
  2. `os.replace()` preserves the source file's mode, so getting the tmp right is sufficient and
     getting it wrong is silent.

  A dedicated directory outside `state_dir` was the more robust option — isolation would rest on
  the directory rather than on one file's mode surviving future copy-paste — and it was rejected
  for a specific cost: `state_dir` is the only path in `ReadWritePaths=` in both
  `deploy/skypane-companion.service` and `deploy/skypane-poll.service`, so a new location means
  editing both units plus a `daemon-reload` on the VPS, which the developer would have to run
  themselves. The plan must instead make the mode requirement impossible to miss by pattern
  matching.

- **D-02: If the file's mode is found more permissive than owner-only, the read refuses the
  secret and the interface says so.** The reader checks the mode and, when it is too open,
  returns "not configured" without ever reading the value — `ssh`'s behaviour with an
  over-permissive private key. Settings then shows a state distinct from both "not configured"
  and "connected", naming the problem and the remedy. Rejected: silently re-tightening the mode
  and continuing (the secret may already have been read, and the silent repair destroys the
  evidence that it was), and writing the mode without ever re-checking it.

### The environment variable

- **D-03: `SKYPANE_CALENDAR_ICS_URL` is retired. The field is the only way to connect a
  calendar.** The variable comes out of `deploy/skypane.env.example`, `CALENDAR_URL_ENV_VAR`
  disappears, and `calendar_is_configured()` / `configured_calendar_url()` — the two existing
  accessors at `server/plane/calendar_rules.py:504` and `:526` — change their source from the
  environment to the file. Keeping it as a precedence-ordered override was rejected: it buys a
  deployment the option of a secret that never touches disk, at the cost of two sources to test,
  a precedence rule to explain in the interface, and a state where the field refuses what is
  typed into it.

  **No migration is needed.** The developer never set the variable on the VPS — Phase 16 shipped
  but was never deployed, and this branch is still unmerged. The plan must nonetheless not
  assume that silently: `deploy/skypane.env.example`'s line is removed, and the Settings copy
  that currently names the variable
  (`companion/pages/config_page.py:333-337`, which interpolates `CALENDAR_URL_ENV_VAR` rather
  than retyping it) must be rewritten, not merely re-pointed.

### Disconnecting

- **D-04: Emptying the field disconnects, and the flights already fetched are deleted from disk
  in the same action.** "Disconnected" must mean what the word promises: nothing of a named
  person's schedule remains on the server. Letting the entries age out of the retention window
  instead was rejected — it leaves someone's roster on disk for up to two days after an explicit
  disconnection.

- **D-05 (drawn from D-04, not separately asked): replacing the URL with a different one also
  clears the previous calendar's entries.** Otherwise "disconnected" would mean two different
  things depending on the gesture, and one calendar's flights could colour the frame while
  another is connected.

  The form must distinguish "field left empty because I did not touch it" from "field emptied on
  purpose". This is exactly the problem Phase 15 solved for `theme_arriving`, and the precedent
  to follow is its sentinel — `device_config.CLEAR_THEME_ARRIVING = object()` at
  `server/device_config.py:111` — not a second, differently-shaped invention.

### What happens on save

- **D-06: Saving triggers the fetch immediately and the page reports the outcome** — connected
  with N flights retained, or the failure and its reason. This is the only moment at which a
  wrong URL can be reported usefully; without it a mistyped feed is indistinguishable from a
  correct one for up to thirty minutes, which is precisely when the operator doubts their copy
  and paste.

  Two constraints drawn from this, not separately asked:
  1. The immediate sync must **bypass `CALENDAR_FETCH_INTERVAL_S`** (1800s,
     `server/plane/calendar_rules.py:107`). Connecting shortly after an unrelated sync must not
     silently do nothing. The bypass must be scoped to this one path — the poll loop's own
     throttle is unchanged.
  2. The failure message must name the cause **without ever re-rendering the URL**. Network and
     DNS exception strings routinely embed the full request URL, so the message must be built
     from a classified failure kind, never from `str(exc)`. Phase 16's five outcome constants
     (`FETCH_OK`, `FETCH_SKIPPED_UNCONFIGURED`, `FETCH_SKIPPED_THROTTLED`, `FETCH_REJECTED_URL`,
     `FETCH_FAILED`, at `:163-167`) already provide that classification and should be reused
     rather than duplicated.

### Amendments after research (2026-09-09)

Three decisions settled after `17-RESEARCH.md` returned. The first corrects a defect in D-04 as
originally written; the other two close the researcher's Open Questions 2 and 3 so the planner
does not have to guess.

- **D-07 (corrects D-04): the disconnect signal is a checkbox, not an empty field.** D-04 said
  "emptying the field disconnects". That cannot work, and the defect is in D-04's wording, not in
  the intent. D-01 and D-02 make the field write-only, so it renders **empty on every page load
  regardless of state** — meaning an unrelated Settings save (changing a theme, say) submits it
  empty and would disconnect the calendar every time.

  The project already solved exactly this. `companion/pages/config_page.py:1726-1736` documents
  the reasoning for `theme_arriving`: an unchecked checkbox is **absent** from the submission, and
  that absence is the only signal able to distinguish "clear" from "leave alone" — `None` cannot
  carry it, because `None` already means "not supplied, carry forward" for every field on this
  write path.

  So: a checkbox inside the Calendar group, rendered **only when a calendar is connected**,
  unchecked by default. Checked plus save disconnects and erases the fetched flights. The
  direction is deliberately the safe one — default does nothing — unlike `theme_arriving`, whose
  checkbox is rendered *checked* when set and whose absence therefore means clear.

  Consequences the plan must carry:
  - An empty field on its own now means "carry forward" and nothing else. D-04's intent survives
    intact; only its trigger changes.
  - A non-empty URL submitted **together with** the disconnect box checked is contradictory. Reject
    the whole save with a flash rather than guessing, following the `else: return
    FLASH_SAVE_FAILED` branch already at `config_page.py:1737-1738`.
  - D-05 is unaffected: submitting a *different* non-empty URL still replaces and clears the
    previous calendar's entries. That path never involves the checkbox.
  - The control stays inside the shared save bar. That is what the developer was protecting when
    they rejected a standalone Disconnect button during discussion; a checkbox keeps it.

- **D-08 (Open Question 2): `calendar_is_configured()` keeps returning a `bool`, and D-02's third
  state gets its own narrow accessor.** Widening the existing accessor to a status string would
  make every current truthiness test silently wrong — a non-empty string is truthy, so a
  permission-drift status would read as "configured" at every existing call site, which is the
  exact failure D-02 exists to prevent. Instead `calendar_is_configured()` returns `False` when the
  mode has drifted (the feature is off, which is true), and a second, narrowly-scoped predicate
  answers "off *because* the mode drifted" for the status line alone. Existing callers need no
  change and cannot mishandle a type they never see.

- **D-09 (Open Question 3): the immediate sync reuses `_POLL_LOCK`, with its existing non-blocking
  acquire.** A separate lock would let a save-triggered calendar refresh run concurrently with a
  poll cycle's own refresh; both do a read-modify-write of the registry, and
  `calendar_rules._WRITE_LOCK` guards only the write, not the interval between load and write.
  Reusing `_POLL_LOCK` means a save arriving during a running poll gets the same honest
  "already running" answer `/poll-now` already gives (`companion/app.py:1913-1922`) instead of
  racing. The cost — an unrelated Settings save can briefly contend with a poll — is bounded and
  visible, which is the trade `_handle_poll_now()` already made deliberately.

### Two findings from research that change what the plan must build

Recorded here because both contradict what `<decisions>` assumed when it was written, and both were
verified directly against the tree rather than taken on the researcher's word.

- **`refresh_calendar_registry()` has no throttle-bypass parameter.** Its signature is
  `(state_dir, now, transport=None)` and it calls `calendar_fetch_is_due(registry["last_attempt_at"],
  now)` at `server/plane/calendar_rules.py:1155` with no interval argument — even though
  `calendar_fetch_is_due()` itself already accepts `min_interval_s=None` at `:766`. D-06's
  "bypass the 1800s throttle" is therefore **new work**, not a call-site option: the parameter must
  be threaded through `refresh_calendar_registry()`, defaulting to today's behaviour so
  `server/poll_loop.py:765`'s existing call is byte-for-byte unaffected.

- **`FETCH_REJECTED_URL` is dead code.** `grep` across `server/` and `companion/` returns zero call
  sites outside its own definition at `:166`; `fetch_ics()` collapses an SSRF-refused URL and a
  genuine network failure into `FETCH_FAILED`. D-06's "the failure and its reason" therefore cannot
  distinguish "that URL is not allowed" from "the fetch failed" without changing Phase 16's SSRF
  internals, which is out of scope. **Plan for one honest generic failure message**, not a
  per-cause copy deck. Do not wire `FETCH_REJECTED_URL` into the UI as though it fires — that would
  ship a message no user can ever see. Whether to make it fire is a separate, later decision.

### Two corrections to Phase 16's recorded security posture

These came out of the codebase scout during this discussion, they contradict statements made
while Phase 16 was being scoped, and the security audit did not catch either. They are recorded
here because the phase's threat model must start from what is true, not from Phase 16's
docstrings.

- **The companion process already holds the calendar URL in its environment.** All three units —
  `skypane-companion.service:22`, `skypane-poll.service:15`, `skypane-byos.service:17` — load
  the same `EnvironmentFile=/opt/skypane/skypane.env`, and all three run as user `skypane`. The
  environment variable was never a process boundary.

- **The companion process already reads the URL's value, on a path that runs today.** `POST
  /poll-now` calls `poll_loop.run_once()` **in-process** (`companion/app.py:1933`), and
  `run_once()` calls `refresh_calendar_registry()` (`server/poll_loop.py:765`), which calls
  `configured_calendar_url()`. The docstring at `calendar_rules.py:526` states the value is
  "never returned to `companion/`"; that is true of `companion/`'s own module code and false of
  the companion's process. Nothing leaks — no rendering path touches the value, and Phase 16's
  audit did verify the rendered output — but the property that justified recommending the
  environment variable in the first place did not exist.

  **The practical consequence is favourable:** the companion already has legitimate cause to
  hold the URL in memory, and `/poll-now` is a working in-process precedent for D-06's immediate
  sync. The planner should reuse that path rather than invent a second cross-process trigger.

### Claude's Discretion

- The exact rendered wording of the field, its three-or-four status states, and the failure
  message text. Phase 16's copy deck is locked and its discipline (no surveillance verbs, no
  promise the frame cannot keep) carries forward; the new strings must match its register.
- Whether the field validates the URL's shape before storing it, or lets `_url_is_safe()`
  (`calendar_rules.py:935`) and the fetch be the single arbiter. Constraint if an earlier check
  is added: it must not become a second, drifting definition of an acceptable URL.
- Whether repeated saves need their own cooldown beyond the existing `/poll-now` one. The route
  is authenticated, and `_url_is_safe()` already refuses private ranges, so this is a resource
  question rather than an SSRF one.
- Task and wave decomposition.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### The feature this phase re-plumbs
- `.planning/phases/16-calendar-linked-flight-highlighting-a-connected-calendar-sou/16-CONTEXT.md` —
  the locked decisions for matching, retention and copy. This phase changes none of them.
- `.planning/phases/16-calendar-linked-flight-highlighting-a-connected-calendar-sou/16-SECURITY.md` —
  the twelve-threat register. Read alongside the two corrections in `<decisions>` above: T-16-SECRET's
  reasoning rests on a process boundary that does not exist. T-16-PRIV is open and adjacent
  (retention not re-applied on the fetch-failure path) and is being fixed in separate work.
- `.planning/phases/16-calendar-linked-flight-highlighting-a-connected-calendar-sou/16-RESEARCH.md` —
  including its "Corrections applied 2026-09-07" section.

### Code this phase must change
- `server/plane/calendar_rules.py` §`calendar_is_configured()` :504, §`configured_calendar_url()` :526 —
  the two accessors whose source changes; `CALENDAR_URL_ENV_VAR` :97 is removed.
- `server/plane/calendar_rules.py` §`write_calendar_registry()` :703 — the tmp-write idiom this
  phase must deliberately NOT copy verbatim for the secret file (D-01).
- `companion/pages/config_page.py` §`calendar_group()` :876 and the copy constants :321-349 —
  the Settings group the field joins; :333-337 names the retired variable.
- `companion/app.py` :1018-1033 — where `calendar_configured` and `calendar_last_synced_at` enter
  the page context, with the comment asserting the process "must never learn its value".
- `deploy/skypane.env.example` :90 — the line to remove.

### Patterns to follow rather than reinvent
- `server/device_config.py` :111 `CLEAR_THEME_ARRIVING` — the clear-vs-unchanged sentinel (D-05).
- `companion/auth.py` §`configured_password()` :64 — the project's other secret accessor, and the
  fail-closed counterpart to `calendar_is_configured()`'s fail-open shape.
- `companion/app.py` §`_handle_poll_now()` :1912 — the in-process trigger and its non-blocking
  `_POLL_LOCK` + cooldown, the precedent for D-06.

### Deployment facts that constrain D-01
- `deploy/provision.sh` :76-77 — `usermod -aG skypane caddy` and `chmod g+ws "${STATE_DIR}"`.
- `deploy/skypane-companion.service` :20-22,38 and `deploy/skypane-poll.service` :13-15,28 —
  same user, same `EnvironmentFile`, `ReadWritePaths=/opt/skypane/state` only.
- `deploy/deploy.sh` :42-44 — `rsync --delete` excludes `state` and `skypane.env`, which is why
  the new file survives a redeploy.

### Project skill
- `.claude/skills/sketch-findings-skypane/SKILL.md` — the companion's design system; the field
  and its status states must be expressed in existing tokens and patterns.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `calendar_is_configured()` / `configured_calendar_url()` — the single accessor pair already
  exists and is already the only way the value is obtained. This phase swaps what is behind them,
  so no caller outside these two functions needs to learn a new way to get the URL.
- `calendar_rules_path(state_dir)` :492 — the naming and placement convention for a state file,
  directly analogous to what the secret file needs.
- `_handle_poll_now()`'s `_POLL_LOCK` non-blocking acquire plus `poll_cooldown_remaining()` —
  a working answer to "two saves arrive at once" that D-06 should reuse.
- `CLEAR_THEME_ARRIVING` — the sentinel shape for D-05.
- The five `FETCH_*` outcome constants — the classification D-06's message must be built from.

### Established Patterns
- Never-raising loaders with per-field `normalise_*`, validate-before-write, tmp-write then
  `os.replace()`, a module-level `threading.Lock()`, and a bounded entry count. **The mode-setting
  requirement in D-01 is the first deliberate departure from this idiom** and the plan must mark
  it as such where a future reader will look.
- Leaf-module discipline: `calendar_rules.py` may import `device_config` but never `enrich`,
  `manual_resolutions`, `illustrations`, or `colour_rules`. The secret file's reader lives inside
  `calendar_rules.py` and must not pull the companion into the server's import graph.
- stdlib only. `os.open` with a mode argument is stdlib; nothing new is needed.
- Hand-rolled harness: `check(name, fn)` plus an `EXPECTED_CHECK_COUNT` ledger that fails on a
  count mismatch, registered in `scripts/run-all-tests.sh`'s `HARNESSES` array.
- `scripts/run-all-tests.sh` has **no lint step**; CI runs `ruff check .` as a separate blocking
  job. A green local suite does not prove CI green — run `ruff check .` before every commit.

### Integration Points
- `companion/pages/config_page.py` — the field joins the existing Calendar group, riding the same
  merged form and save bar as every other setting.
- `companion/app.py`'s POST handler — where the submitted value is read, the sentinel resolved,
  the file written, and D-06's sync triggered.
- `server/poll_loop.py` :765 — unchanged, but the reason the file must be readable by that
  process and the reason `/poll-now` already exercises the whole path in the companion.

</code_context>

<specifics>
## Specific Ideas

The phase exists because of one sentence from the developer, on first reading Phase 16's shipped
Settings group: *"dans mon esprit ça pouvait être configuré directement sur le companion"*. Their
original framing of the feature, when it was generalised away from a single person's roster, was
**"connect your calendar"** — a gesture in a browser. That phrase is the acceptance test for this
phase: connecting a calendar should be pasting a URL and pressing save, with the frame using it
and the page saying so.

The developer also pushed back mid-discussion on being shown implementation mechanics without
being told they were mechanics — *"pourquoi tu parles de fichier alors que pour moi dans le
companion on indique une url ??"*. The file is invisible to them and must stay that way: it is
never named in the interface, and no status state ever asks them to think about it. The one
exception is D-02's permission-drift state, which exists precisely because it is the one case
where the operator must act on the server.

</specifics>

<deferred>
## Deferred Ideas

- **Showing which upcoming flights the connected calendar holds.** Phase 16 deliberately renders
  no preview and no count of upcoming flights, because doing so would make the frame look like it
  tracks a person. D-06 reports a count at sync time as feedback on whether the URL worked, which
  is a different thing; a browsable list is a new capability and belongs in its own phase if it is
  ever wanted.
- **More than one connected calendar.** Nothing in the discussion asked for it and the registry,
  the match key and the single theme all assume one. Out of scope.
- **Connecting a calendar from the device itself, without a browser.** Not raised; noted only
  because the phase name invites the question.

### Reviewed Todos (not folded)

None — `todo.match-phase 17` returned zero pending todos.

</deferred>

---

*Phase: 17-connect-a-calendar-from-the-companion-instead-of-over-ssh*
*Context gathered: 2026-09-08*
