# Phase 17: Connect a calendar from the companion instead of over SSH - Research

**Researched:** 2026-09-08
**Domain:** stdlib file-permission mechanics; a companion-form secret-clear sentinel; an in-process
sync trigger reusing an existing lock/cooldown pattern
**Confidence:** HIGH on all stdlib claims (empirically verified in this session, see commands below);
MEDIUM-HIGH on the code-reuse recommendations (verified against shipped code at HEAD, not assumed
from docstrings); LOW/flagged-as-open only where the codebase itself is ambiguous (see Open Questions)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** The URL lives in a dedicated file in `state_dir`, created explicitly at mode `0600` —
  the temporary file included. Chosen over a dedicated directory outside `state_dir` and over a
  field in `device_config.json`. The mode must be set **at creation** of the temporary file
  (`os.open(tmp, O_WRONLY | O_CREAT | O_EXCL, 0o600)`), never `chmod` after writing.
  `os.replace()` preserves the source file's mode, so getting the tmp file's mode right is
  sufficient and getting it wrong is silent.
- **D-02:** If the file's mode is found more permissive than owner-only, the read refuses the
  secret and the interface says so — never silently re-tightens the mode, never writes without
  re-checking.
- **D-03:** `SKYPANE_CALENDAR_ICS_URL` is retired. The field is the only way to connect a
  calendar. `CALENDAR_URL_ENV_VAR` disappears; `calendar_is_configured()` /
  `configured_calendar_url()` change their source from the environment to the file. No migration
  needed — the developer never set the variable on the VPS. `deploy/skypane.env.example`'s line is
  removed, and the Settings copy naming the variable must be rewritten, not merely re-pointed.
- **D-04:** Emptying the field disconnects, and the flights already fetched are deleted from disk
  in the same action.
- **D-05:** Replacing the URL with a different one also clears the previous calendar's entries.
  The form must distinguish "field left empty because I did not touch it" from "field emptied on
  purpose" — follow Phase 15's `device_config.CLEAR_THEME_ARRIVING` sentinel precedent, not a
  second, differently-shaped invention.
- **D-06:** Saving triggers the fetch immediately and the page reports the outcome — connected
  with N flights retained, or the failure and its reason. The immediate sync must **bypass
  `CALENDAR_FETCH_INTERVAL_S`** (1800s) scoped to this one path only — the poll loop's own throttle
  is unchanged. The failure message must name the cause **without ever re-rendering the URL** —
  built from a classified failure kind, never from `str(exc)`. Reuse the five `FETCH_*` outcome
  constants rather than duplicating them.
- **Corrections to Phase 16's recorded security posture:** the companion process already holds the
  calendar URL in its environment (all three units load the same `EnvironmentFile=`); the companion
  process already reads the URL's value on a path that runs today (`POST /poll-now` →
  `poll_loop.run_once()` → `refresh_calendar_registry()` → `configured_calendar_url()`), in-process.
  Nothing leaks today because no rendering path touches the value — but "the companion never learns
  the value" was never true of the process, only of `companion/`'s own module code. The practical
  consequence: `/poll-now` is a working in-process precedent for D-06's immediate sync — reuse that
  path, don't invent a second cross-process trigger.

### Claude's Discretion

- The exact rendered wording of the field, its three-or-four status states, and the failure
  message text. Phase 16's copy discipline (no surveillance verbs, no promise the frame cannot
  keep) carries forward.
- Whether the field validates the URL's shape before storing it, or lets `_url_is_safe()` and the
  fetch be the single arbiter. Constraint if an earlier check is added: it must not become a
  second, drifting definition of an acceptable URL.
- Whether repeated saves need their own cooldown beyond the existing `/poll-now` one.
- Task and wave decomposition.

### Deferred Ideas (OUT OF SCOPE)

- Showing which upcoming flights the connected calendar holds (a browsable list/preview).
- More than one connected calendar.
- Connecting a calendar from the device itself, without a browser.

</user_constraints>

## Summary

This phase is almost entirely a **plumbing move**, not new mechanism: swap one accessor pair's
data source from `os.environ` to a file, add a write path with a permission property the codebase
has never needed before, and wire the existing in-process `/poll-now` call into a save handler.
Every piece the plan needs already exists in the codebase in a form to copy — `write_calendar_registry()`'s
tmp-write-then-`os.replace()` shape, `device_config.CLEAR_THEME_ARRIVING`'s identity-compared
sentinel, `_handle_poll_now()`'s non-blocking lock, and `_resolve_flash_text()`'s
opaque-key-plus-server-computed-value flash pattern. The one genuinely new piece of mechanics is
D-01's file-mode requirement, because **no code in this project has ever set a file mode before**
— every other state write inherits the process umask (0644 in practice). This research empirically
verified, against a live Python 3 interpreter in this session (not from memory), that the mode
argument to `os.open()` is masked by umask but never widened by it, that `os.replace()` fully
replaces the destination's mode with the source's (not a merge), and that the state directory's
`setgid` bit affects only which *group* owns a new file, never its *permission bits* — so a file
created at `0600` defeats Caddy's group membership regardless of that bit.

The second load-bearing finding is a genuine gap in the shipped Phase 16 code that D-06 depends on
closing: **`refresh_calendar_registry()` has no parameter to bypass its own throttle.** It calls
`calendar_fetch_is_due(registry["last_attempt_at"], now)` with no `min_interval_s` argument, so
every caller — including a hypothetical Settings-triggered call — inherits the hardcoded 1800s
interval. The plan must add a `min_interval_s=None` parameter to `refresh_calendar_registry()`
that threads through to `calendar_fetch_is_due()`, defaulting to `None` (preserving
`poll_loop.py:765`'s existing call unchanged) so the Settings POST handler can pass `min_interval_s=0`
for its one call only.

The third finding narrows what D-06's "failure and its reason" can actually say: `FETCH_REJECTED_URL`
is a **declared but dead** constant — `fetch_ics()` collapses an SSRF-refused URL and a genuine
network failure into the identical `None` return, and `refresh_calendar_registry()` only ever emits
`FETCH_OK` / `FETCH_SKIPPED_UNCONFIGURED` / `FETCH_SKIPPED_THROTTLED` / `FETCH_FAILED` in practice.
Distinguishing "that URL isn't allowed" from "couldn't reach it" at the coarse `FETCH_FAILED`
outcome would require either touching the SSRF gate (out of scope by the anti-goals) or a duplicate
`_url_is_safe()` pre-check purely for copy purposes (same-module call, not a leaf violation, but a
second thing to keep in sync). Recommended: a single generic failure message covering both cases.

**Primary recommendation:** add the new secret file's read/write/mode-check functions to
`server/plane/calendar_rules.py` (same leaf module, since `calendar_is_configured()` /
`configured_calendar_url()` already live there and every existing caller already goes through
them unchanged); use a plain single-line text file, not JSON, since the file holds exactly one
string; give `refresh_calendar_registry()` a `min_interval_s=None` parameter for D-06's bypass;
and model the form's clear-vs-unchanged decision on `theme_arriving_enabled`'s checkbox-keyed
branch in `config_page.handle_post()`, not on the text field's own presence or emptiness.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Secret file read/write/mode-check | API / Backend (`server/plane/calendar_rules.py`) | — | Same leaf module already owns `calendar_is_configured()`/`configured_calendar_url()`; leaf-import discipline forbids `companion/` from touching the file directly |
| Settings form field + clear sentinel | Frontend Server (`companion/pages/config_page.py`) | — | Mirrors `theme_arriving`'s existing form-to-`device_config` pattern; this module owns all Settings markup and POST validation |
| Immediate sync trigger (D-06) | Frontend Server (`companion/app.py`'s POST `/settings` handler) | API / Backend (`refresh_calendar_registry()`, called in-process) | `/poll-now`'s existing precedent already calls `poll_loop.run_once()` in-process from the companion; the same process boundary applies here — no new cross-process call |
| Outcome reporting (flash message) | Frontend Server (`companion/app.py` flash mechanism) | — | Existing opaque-flash-key pattern (`_resolve_flash_text()`) already exists; must not carry the URL or raw exception text |
| Deploy artifact cleanup (env var line, unit files) | Deployment / Ops | — | `deploy/skypane.env.example` edit is a plain file change; systemd units need **no** change (see Common Pitfalls / hard constraint verification below) |

## Standard Stack

### Core

No new dependency of any kind. `server/requirements.txt` is unchanged (`Pillow==12.3.0`,
`requests==2.34.2`) — this phase touches zero HTTP/JSON/crypto surface that isn't already
satisfied by `os`, `json` (or plain text I/O), `stat`, `threading`, already-imported stdlib
modules in `calendar_rules.py`.

### Supporting

Nothing new. `os.open`/`os.fdopen`/`os.replace`/`os.stat`/`stat.S_IMODE` are all stdlib, already
verified against the running interpreter in this session (Python 3.14.7 locally; the project pins
Python 3.12 in production — the specific stdlib behaviours verified below are unchanged across
that range, confirmed against the CPython `posix`/`os` module docstrings which do not version-gate
any of these functions after 3.3).

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Plain single-line text file for the secret | JSON file (matching every other state file's shape) | JSON adds parse/escape surface for zero benefit on a single string value; a bare `.strip()`'d text file is simpler and there is exactly one thing to serialize. Recommended: plain text. |
| `os.open()` + `os.fdopen()` wrapping | `open(path, "x")` with a `chmod()` follow-up | Rejected — this is precisely the window D-01 forbids: `"x"` mode uses `open(2)`'s default mode (0666 masked by umask, i.e. 0644 in practice) with no way to pass an explicit mode, so a `chmod()` after write leaves the file at 0644 momentarily |

**Installation:** none — no new packages.

**Version verification:** N/A — no packages to verify. `server/requirements.txt` verified
unchanged and current at HEAD (`Pillow==12.3.0`, `requests==2.34.2`).

## Package Legitimacy Audit

**Not applicable.** This phase installs zero external packages. Confirmed by inspection of
`server/requirements.txt` (unchanged) and by the same AST-import-set discipline Phase 16's own
security audit used: the new functions this phase adds belong in `server/plane/calendar_rules.py`,
which already imports only stdlib plus `requests` (pinned since Phase 2) plus
`server.device_config`. No new import is needed for a file-mode write.

## Architecture Patterns

### System Architecture Diagram

```
Operator's browser
      |
      | POST /settings  (calendar_url=<pasted text or blank>, session cookie)
      v
companion/app.py  do_POST()  ---- require_session() gate (existing, unchanged)
      |
      v
companion/pages/config_page.py  handle_post()
      |
      |-- submitted_calendar_url == "" (deliberate clear signal, see below)
      |       -> calendar_rules.clear_calendar_url(state_dir)   [D-04/D-05: also drops entries]
      |
      |-- submitted_calendar_url is a non-empty string
      |       -> calendar_rules.save_calendar_url(state_dir, submitted_calendar_url)
      |               (creates tmp at mode 0600, os.replace() onto the real path)
      |
      v
companion/app.py  _handle_poll_now()'s reused shape (D-06)
      |
      |-- _POLL_LOCK.acquire(blocking=False)  (existing non-blocking guard, reused)
      v
server/plane/calendar_rules.py  refresh_calendar_registry(state_dir, now, min_interval_s=0)
      |         (NEW parameter — bypasses CALENDAR_FETCH_INTERVAL_S for THIS call only;
      |          poll_loop.py's own call keeps the default and is untouched)
      |
      |-- configured_calendar_url()  [NOW reads the new file, not os.environ]
      |-- fetch_ics(url)             [UNCHANGED — SSRF gate, size cap, timeout, redirects: all Phase 16]
      |-- parse_ics_events() / select_window_entries()   [UNCHANGED]
      |-- write_calendar_registry(state_dir, entries, ...)  [UNCHANGED]
      v
result_code (one of FETCH_OK / FETCH_SKIPPED_UNCONFIGURED / FETCH_SKIPPED_THROTTLED / FETCH_FAILED)
      |
      v
companion/app.py  redirect("/settings?flash=<opaque key>")
      |
      v
companion/pages/config_page.py's flash resolution (existing pattern, _resolve_flash_text()-style)
      |    -- recomputes flight count FRESH from disk (len(load_calendar_registry(...)["entries"]))
      |    -- never re-renders the submitted URL, never touches str(exc)
      v
Settings page: "Connected — N flights retained." / generic failure copy / disconnected copy
```

### Recommended Project Structure

No new files. Every change lands in existing modules:

```
server/plane/calendar_rules.py   # + calendar_secret_path(), save_calendar_url(),
                                  #   clear_calendar_url(), CLEAR_CALENDAR_URL sentinel,
                                  #   mode-check inside calendar_is_configured()/
                                  #   configured_calendar_url(); CALENDAR_URL_ENV_VAR removed;
                                  #   refresh_calendar_registry() gains min_interval_s=None
companion/pages/config_page.py   # calendar_group() gains the text field + clear control;
                                  # handle_post() gains the branch; copy constants rewritten
companion/app.py                 # POST /settings handler calls the D-06 sync after a
                                  # successful save, reusing _POLL_LOCK's non-blocking shape
deploy/skypane.env.example       # SKYPANE_CALENDAR_ICS_URL line + its comment block removed
server/test_calendar_rules.py    # ~15 fixture setups migrate from os.environ[...] to a
                                  # file-write helper (see Common Pitfalls)
companion/test_config_page.py    # copy-constant assertions + calendar_is_configured() fixtures
```

### Pattern 1: The mode-set-at-creation write (D-01's genuinely new idiom)

**What:** Create the tmp file with `os.open()` passing the mode directly, never `open()` followed
by `chmod()`.

**When to use:** Any file whose permission bits are a security property, not merely a matter of
umask default. This is the *only* file in the codebase with that property today.

**Verified in this session** (Python 3.14.7, local sandbox — not from memory):

```
$ python3 - <<'EOF'
import os, stat
os.umask(0o022)
fd = os.open("tmp1.tmp", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(fd)
print(oct(stat.S_IMODE(os.stat("tmp1.tmp").st_mode)))
os.umask(0o027)
fd = os.open("tmp2.tmp", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(fd)
print(oct(stat.S_IMODE(os.stat("tmp2.tmp").st_mode)))
os.umask(0o000)
fd = os.open("tmp3.tmp", os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(fd)
print(oct(stat.S_IMODE(os.stat("tmp3.tmp").st_mode)))
EOF
0o600
0o600
0o600
```

**Finding [VERIFIED: local CPython 3.14.7 interpreter, cross-checked against `open(2)`'s BSD man
page: "the file is created with mode `mode` as described in chmod(2) and modified by the process'
umask value"]:** the umask can only ever **remove** bits from the requested mode
(`mode & ~umask`), never add them. `0o600` has zero group/other bits to begin with, so **no**
umask value — 022, 027, or even 000 (maximally permissive) — can widen it. `os.umask()` alone is
therefore unnecessary; the explicit mode argument to `os.open()` is sufficient and safe on its
own. (Edge case worth noting, not a real risk: an extreme umask like `0o700` would strip the
*owner* bits too, since `0600 & ~0700 == 0000` — but that host-wide umask would break every other
file the process writes, not just this one, so it is not a scenario this plan needs to special-case.)

**Wrapping the fd for text writing, and cleanup on failure — verified end to end:**

```
$ python3 - <<'EOF'
import os, stat, threading, json

def write_secret(path, value):
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
    fd = None
    try:
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fd = None  # fdopen() took ownership of the fd; avoid a double-close below
            fh.write(value)
        os.replace(tmp, path)
        return True
    except Exception:
        if fd is not None:
            try: os.close(fd)
            except OSError: pass
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except OSError: pass
        return False

ok = write_secret("calendar_secret.json", "https://example.com/feed.ics")
print("write ok:", ok)
print(oct(stat.S_IMODE(os.stat("calendar_secret.json").st_mode)))
EOF
write ok: True
0o600
```

This is `write_calendar_registry()`'s existing tmp-naming convention (`"%s.%d.%d.tmp" %
(path, os.getpid(), threading.get_ident())`) verbatim — **the tmp filename pattern needs no
change**; only the file-open call inside the `try:` block changes from `open(tmp, "w")` to the
`os.open()` + `os.fdopen()` pair above. Everything else in `write_calendar_registry()`'s existing
shape (create `state_dir` first, `os.replace()`, remove-tmp-on-any-exception, never raise) carries
over unchanged. `os.fdopen()` is CPython's documented way to wrap a raw fd from `os.open()` in a
text-mode file object — confirmed via `pydoc os.fdopen` locally, no special-casing needed beyond
setting `fd = None` before entering the `with` block so the exception handler doesn't try to
`os.close()` an fd that `os.fdopen()`'s context manager already closed.

### Pattern 2: `os.replace()` preserves the *source* file's mode, not the destination's

**Verified empirically** (this is D-01's second stated consequence, and it is the one the whole
security property rests on):

```
$ python3 - <<'EOF'
import os, stat

dest = "secret.json"
with open(dest, "w") as fh: fh.write("old")
os.chmod(dest, 0o644)
print("dest before:", oct(stat.S_IMODE(os.stat(dest).st_mode)))

tmp = dest + ".12345.67890.tmp"
fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.fdopen(fd, "w").write("new")  # (simplified for the transcript; use the try/finally shape above)
print("tmp before replace:", oct(stat.S_IMODE(os.stat(tmp).st_mode)))

os.replace(tmp, dest)
print("dest after replace:", oct(stat.S_IMODE(os.stat(dest).st_mode)))
EOF
dest before: 0o644
tmp before replace: 0o600
dest after replace: 0o600
```

**Finding [VERIFIED]:** `os.replace()` (POSIX `rename(2)`) does not merge, average, or inherit
anything from the pre-existing destination — the destination's directory entry is atomically
repointed at the source inode, and the resulting file's mode is **exactly** the source's mode.
A pre-existing `calendar_secret.json` sitting at 0644 (e.g. from an earlier, buggy implementation)
is fully corrected to 0600 the instant a correctly-mode-set tmp file replaces it. This means
D-01's mode requirement is **self-healing on every successful write** — the only way the mode
stays wrong is if it was never set correctly at the *creation* of the tmp file in the first place,
exactly as D-01 states.

### Pattern 3: setgid on `state_dir` affects group ownership, never a file's permission bits

**Verified empirically** (macOS sandbox does not permit setting the setgid bit via `chmod` in
this environment, so gid-inheritance itself could not be directly reproduced here — but the
**mode-independence** half, which is what D-01's security claim actually rests on, was
reproduced):

```
$ python3 - <<'EOF'
import os, stat
os.makedirs("setgid_test_dir", exist_ok=True)
os.chmod("setgid_test_dir", 0o2775)
os.umask(0o022)
p = "setgid_test_dir/secret.tmp"
fd = os.open(p, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
os.close(fd)
print(oct(stat.S_IMODE(os.stat(p).st_mode)))
EOF
0o600
```

Cross-checked against the local BSD `chmod(1)` man page (`man chmod`), which documents the
directory-inheritance property directly: *"The `w` permission on directories will permit file
creation, relocation, and copy into that directory. Files created within the directory itself
will inherit its group ID."* — this sentence is explicitly and only about **group ID**, never
about permission bits. `deploy/provision.sh:70-77`'s own comment corroborates this from the other
direction: *"640 alone is not enough — group ownership matters too... setgid makes every
new/rotated log file inherit group `skypane` regardless of which user created it, and membership
is what lets skypane actually use that group-read bit."* — i.e., the project's own deploy script
already documents that setgid's whole purpose is to fix *group ownership* so that an *already
group-readable* mode (like `calendar_rules.json`'s 0644) becomes usable by `caddy`. Since 0600 has
**zero** group bits, which group owns the file is irrelevant — `caddy`'s membership in the
`skypane` group buys it nothing against a file with no group-read bit set. **This closes D-01's
central security claim with no residual doubt:** mode 0600, correctly set at creation, defeats
Caddy's group membership regardless of `chmod g+ws STATE_DIR` (`deploy/provision.sh:77`).

### Pattern 4: reading the mode back for D-02's refusal check

```python
import os, stat

mode = stat.S_IMODE(os.stat(path).st_mode)
if mode & (stat.S_IRWXG | stat.S_IRWXO):
    # more permissive than owner-only — refuse the secret, return "not configured"
    # equivalent, and let the caller distinguish this from a genuine absence.
    ...
```

`stat.S_IMODE()` masks out the file-type bits, leaving the permission bits **plus** any
setuid/setgid/sticky bits (`S_ISUID`/`S_ISGID`/`S_ISVTX`), which live at higher bit positions
(0o4000/0o2000/0o1000) than `S_IRWXG`/`S_IRWXO` (0o070/0o007) and therefore never collide with this
predicate. Checking `S_IRWXG | S_IRWXO` (all of read/write/execute for group and other) rather
than only the read bits is deliberate and matches D-02's wording ("more permissive than
owner-only") — a file that's merely group-*writable* (but not readable) is still a integrity risk
worth refusing, not only a confidentiality one.

### Anti-Patterns to Avoid

- **`open(path, "w")` then `os.chmod(path, 0o600)`:** the exact anti-pattern D-01 calls out by
  name — there is a real window (however short) where the file exists world/group-readable at the
  process umask.
- **Re-deriving the write idiom from scratch instead of copying `write_calendar_registry()`'s
  shape:** the tmp-naming, `state_dir` creation, and cleanup-on-failure logic are all correct and
  battle-tested; only the single `open()` call inside the `try:` needs to change.
- **Reaching for `configured_calendar_url()`'s string value anywhere in a log line, exception
  message, or flash message** — this project already has a standing rule (this module's own
  docstring, and `companion/auth.py`'s docstring for the password) that a secret value is never
  interpolated into anything that reaches a log or the browser.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| "field left blank on purpose" vs "field left blank because untouched" | A second, differently-shaped sentinel scheme (e.g. a hidden JS-computed dirty flag, or treating empty string itself as the clear signal) | `device_config.CLEAR_THEME_ARRIVING`'s exact shape: a module-level `object()` sentinel compared by identity in the write function, decided in `handle_post()` by an explicit companion signal — for `theme_arriving` that signal is a checkbox (`theme_arriving_enabled`); for this field, an explicit "Disconnect" control (checkbox or button) alongside the text input plays the same role, since the text field itself can never distinguish "I didn't touch this" from "I want it empty" (see Open Questions — this is the one place D-05's instruction genuinely needs a new UI decision, not a copy of `theme_arriving`'s exact markup) | `CLEAR_THEME_ARRIVING` already proves this shape is correct, tested (127/127 in `test_config_page.py`), and reviewable — a bespoke second scheme would be new surface with no test precedent |
| Throttle-bypassing a fetch for one caller | A parallel fetch/parse/persist function copy-pasted from `refresh_calendar_registry()` | Add `min_interval_s=None` to `refresh_calendar_registry()`'s own signature and thread it into its internal `calendar_fetch_is_due()` call | Keeps exactly one function performing "throttle, fetch, parse, window, persist" — duplicating it would immediately create the kind of drift T-16-BRANCH's audit exists to catch |
| Detecting "did the poll trigger fail because of a bad calendar URL vs. something else" | Catching the exception from `refresh_calendar_registry()` and inspecting `str(exc)` | `refresh_calendar_registry()` is contractually never-raising (verified: its own top-level `try/except Exception` swallows everything and falls back to `load_calendar_registry()`) — consume its `(result_code, registry)` return value only | Any `try/except` wrapping this call that touches the exception string reintroduces exactly the URL-leak risk T-16-SECRET closed for the poll path |

**Key insight:** every piece of new mechanics this phase needs already has a shipped, tested
analogue somewhere in this codebase. The risk in this phase is not "what pattern to invent" but
"which existing pattern to copy without silently dropping the one property that made it correct" —
mode-at-creation for the write, identity-compared sentinel for the clear signal, and
never-touch-the-exception for the outcome report.

## Runtime State Inventory

This phase is not a rename/refactor, but it does retire a secret's storage location, so the
canonical question ("after every file in the repo is updated, what runtime systems still have the
old string cached, stored, or registered?") was checked against all five categories:

| Category | Items Found | Action Required |
|----------|-------------|------------------|
| Stored data | None — the developer never set `SKYPANE_CALENDAR_ICS_URL` on the VPS (confirmed in `17-CONTEXT.md`: "Phase 16 shipped but was never deployed, and this branch is still unmerged"). No production `calendar_rules.json` window entries exist to migrate either, since Phase 16 has never run against a real feed in production. | None |
| Live service config | None — no external service (n8n, Datadog, etc.) has any configuration referencing this env var. | None |
| OS-registered state | None — no systemd unit, cron, or task scheduler entry names the variable outside `deploy/skypane.env.example`'s own template comment. | None |
| Secrets/env vars | `SKYPANE_CALENDAR_ICS_URL` in `deploy/skypane.env.example` (never a real deployed value, only the placeholder `replace-with-your-private-ics-feed-url`) — this is a **code edit**, not a data migration: remove the line and its three-line explanatory comment block (`deploy/skypane.env.example:85-90`). | Code edit only |
| Build artifacts / installed packages | None — no package or build artifact embeds the env var name. | None |

**Confirmed:** `deploy/skypane-companion.service` and `deploy/skypane-poll.service` both already
declare `ReadWritePaths=/opt/skypane/state` (verified: `grep -n ReadWritePaths` on both files
returns exactly that path) and both already load `EnvironmentFile=/opt/skypane/skypane.env`
(verified: same command). Since D-01 places the new secret file inside `state_dir`, **neither unit
needs any change, and no `daemon-reload` is required** — the hard constraint holds cleanly, not by
assumption but by direct inspection of both shipped unit files.

## Common Pitfalls

### Pitfall 1: Believing the throttle bypass is "just call `refresh_calendar_registry()`"

**What goes wrong:** A plan that calls `calendar_rules.refresh_calendar_registry(state_dir, now())`
straight from the Settings POST handler, expecting D-06's "bypass `CALENDAR_FETCH_INTERVAL_S`" to
happen automatically, silently does nothing new — the function is hardcoded to the default 1800s
interval on every call.

**Why it happens:** `refresh_calendar_registry(state_dir, now, transport=None)`'s signature has no
`min_interval_s` parameter at all; internally it calls
`calendar_fetch_is_due(registry["last_attempt_at"], now)` with no third argument, so
`calendar_fetch_is_due()`'s own `min_interval_s` default (`CALENDAR_FETCH_INTERVAL_S`) always wins.
`calendar_fetch_is_due()` itself *does* already accept `min_interval_s` — the gap is one level up,
in `refresh_calendar_registry()` not exposing it.

**How to avoid:** Add `min_interval_s=None` to `refresh_calendar_registry()`'s signature, pass it
straight through to the internal `calendar_fetch_is_due()` call (`None` preserves today's default
behaviour for `poll_loop.py`'s existing call), and have the Settings POST handler pass
`min_interval_s=0`.

**Warning signs:** A test that saves a URL immediately after an unrelated poll cycle and expects
`FETCH_OK`, but observes `FETCH_SKIPPED_THROTTLED` instead.

### Pitfall 2: Trying to report *which* FETCH_* reason fired when only "ok" and "failed" actually exist

**What goes wrong:** Designing three or four distinct failure copy strings (bad URL / unreachable
host / timed out / TLS error) under the assumption that `refresh_calendar_registry()`'s return
code already distinguishes them.

**Why it happens:** `FETCH_REJECTED_URL` is declared (`calendar_rules.py:166`) and reads like it
should be a distinct outcome, but grep confirms it is **never returned** anywhere in the module —
`fetch_ics()` returns bare `None` for a rejected URL, a non-200 status, an oversized body, an
exhausted-redirect loop, and a transport exception alike, and `refresh_calendar_registry()` maps
every `None` return to the single `FETCH_FAILED` code.

**How to avoid:** Design the failure copy as a single generic message ("Couldn't connect to that
calendar — check the URL and try again.") covering every `FETCH_FAILED` case. If per-reason
messaging is wanted later, that requires either exposing a reason from inside `fetch_ics()`
(touching the SSRF/fetch internals — explicitly out of this phase's scope per the anti-goals) or a
same-module, pre-flight call to `_url_is_safe()` purely for the "obviously malformed/private URL"
case, which duplicates a private helper's judgment and needs its own sync-with-fetch discipline.
Recommend the single generic message for this phase; flag per-reason messaging as a future
enhancement if the operator finds it insufficiently informative in practice.

**Warning signs:** A UI-SPEC or copy deck listing 3+ distinct failure strings with no
corresponding distinct `FETCH_*` constant behind each one.

### Pitfall 3: Test fixture churn undercounted

**What goes wrong:** Underestimating how many existing tests set up their fixture via
`os.environ[cr.CALENDAR_URL_ENV_VAR] = ...` and will break once the env var is retired.

**Measured:** `grep -n "CALENDAR_URL_ENV_VAR" server/test_calendar_rules.py` returns **26 lines**
across roughly 13 distinct test functions, every one of which patches `os.environ` in a
setup/teardown pair as its way of "configuring" the feature for that test. `companion/test_config_page.py`
has a further 2 test functions doing the same (lines ~3564-3578, ~4090-4118), plus roughly a dozen
assertions against `CALENDAR_STATUS_NOT_CONFIGURED`/`CALENDAR_STATUS_CONFIGURED_PENDING`/
`CALENDAR_STATUS_CONFIGURED_SYNCED_PREFIX` (lines 3438-3535) that don't need behavioural changes
but will need re-reading once `CALENDAR_STATUS_NOT_CONFIGURED`'s copy no longer names an env var.

**How to avoid:** Budget for a single shared test helper (e.g. `_write_calendar_secret(state_dir, url)`
mirroring the shape of any existing "write a fixture file directly" helper in this test module) that
every one of those ~13 functions swaps in for its `os.environ[...] = ...` line. This is mechanical,
one-line-per-callsite churn, not a design problem — but it is real effort the plan should size
correctly rather than discover mid-execution.

**Warning signs:** `EXPECTED_CHECK_COUNT` mismatches in `server/test_calendar_rules.py` (currently
76) or `companion/test_config_page.py` (currently 127) after the refactor, or `git diff` showing
far more test-file churn than the plan anticipated.

### Pitfall 4: Assuming the whole-config-dict equality test needs updating

**What was checked, and the good news:** `companion/test_config_page.py:1654` contains a
whole-dict equality assertion (`if on_disk != {"theme": ..., "calendar_theme_id": None, ...}`)
against `device_config.load_device_config()`'s return. Since D-01 places the calendar URL in its
**own** file, not in `device_config.json`, this assertion is **not** expected to need any change —
it is a risk only if a plan mistakenly adds a new key (like a `calendar_url_configured` boolean) to
`device_config.json` instead of keeping the presence check entirely inside `calendar_rules.py`'s
`calendar_is_configured()`. **Recommendation: do not add any new key to `device_config.json` for
this phase; the existing `calendar_is_configured()`/`configured_calendar_url()` accessor pair,
re-pointed at the file, is sufficient and was designed for exactly this swap.**

### Pitfall 5: Forgetting the trailing-newline/whitespace normalisation the env var reading already had

`configured_calendar_url()`'s current implementation does `raw.strip()` before validating. A
pasted URL from a browser `<input>` won't usually carry a newline, but a value read back from a
file (especially one a human might later hand-edit, matching D-02's own "hand-edited file" framing
elsewhere in this codebase) can easily pick one up. Strip on both write and read.

## Code Examples

### The full write function shape (adapt into `calendar_rules.py`, following `write_calendar_registry()`'s existing structure)

```python
# Source: verified locally against server/plane/calendar_rules.py:697-728's shape (the tmp-write-
# then-os.replace() idiom this function must depart from ONLY at the os.open() call), and against
# this session's own experiments confirming os.replace() preserves the source file's mode.

CLEAR_CALENDAR_URL = object()  # identity-compared sentinel, D-05's CLEAR_THEME_ARRIVING precedent

def calendar_secret_path(state_dir):
    return os.path.join(state_dir, CALENDAR_SECRET_FILENAME)  # plain text, not JSON

def save_calendar_url(state_dir, value):
    """value is CLEAR_CALENDAR_URL (delete the file + drop entries), a non-blank string
    (write it, mode 0600, at creation), or anything else is a caller error. Never raises;
    returns True/False."""
    path = calendar_secret_path(state_dir)
    if value is CLEAR_CALENDAR_URL:
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except OSError:
            return False
    tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
    fd = None
    try:
        os.makedirs(state_dir, exist_ok=True)
        fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w") as fh:
            fd = None
            fh.write(value.strip())
        os.replace(tmp, path)
        return True
    except Exception:
        if fd is not None:
            try: os.close(fd)
            except OSError: pass
        if os.path.exists(tmp):
            try: os.remove(tmp)
            except OSError: pass
        return False
```

### The mode-check read (D-02)

```python
# Source: verified via stat.S_IMODE() semantics, this session's local interpreter.
def _calendar_secret_mode_is_safe(path):
    try:
        mode = stat.S_IMODE(os.stat(path).st_mode)
    except OSError:
        return None  # doesn't exist — not a permission problem, just "not configured"
    return not (mode & (stat.S_IRWXG | stat.S_IRWXO))
```

### The D-06 throttle-bypass parameter (the one required signature change to Phase 16 code)

```python
# server/plane/calendar_rules.py — refresh_calendar_registry()'s existing signature is
# (state_dir, now, transport=None). Add one parameter, thread it through unchanged:
def refresh_calendar_registry(state_dir, now, transport=None, min_interval_s=None):
    ...
    if not calendar_fetch_is_due(registry["last_attempt_at"], now, min_interval_s):
        return FETCH_SKIPPED_THROTTLED, registry
    ...
# server/poll_loop.py:765's existing call is untouched (min_interval_s defaults to None,
# which calendar_fetch_is_due() already resolves to CALENDAR_FETCH_INTERVAL_S):
_, calendar_registry = calendar_rules.refresh_calendar_registry(state_dir, now_s())

# companion/app.py's new Settings-save sync call:
result_code, registry = calendar_rules.refresh_calendar_registry(
    state_dir, time.time(), min_interval_s=0)
```

## State of the Art

Not applicable in the usual sense (no external library/API version drift to track) — the relevant
"state of the art" question this phase answers is purely intra-project: moving a v1 SSH-edited
config value into a first-class Settings field is this project's now-established pattern (Phase 6
onward), and this phase is the calendar URL's turn.

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| `SKYPANE_CALENDAR_ICS_URL` in `skypane.env`, edited over SSH | A Settings-page text field, backed by a mode-0600 file in `state_dir` | This phase | The companion becomes the single way to connect a calendar; `deploy/skypane.env.example` loses one line |

**Deprecated/outdated:** `CALENDAR_URL_ENV_VAR` / `SKYPANE_CALENDAR_ICS_URL` — removed outright,
not kept as a fallback (D-03 explicitly rejected a precedence-ordered override).

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | A plain-text single-line file (not JSON) is the right shape for the secret file | Standard Stack / Code Examples | Low — trivial to change; no consumer outside the two accessors this phase controls exists yet |
| A2 | The clear-vs-unchanged form signal should be a second control (checkbox/button) alongside the text field, mirroring `theme_arriving_enabled`, rather than any scheme keying off the text field's own submitted value | Don't Hand-Roll | Medium — this is the one place the codebase has no *exact* precedent (the text field itself is new; `theme_arriving`'s checkbox pairs with a `<select>`, not a free-text input) and Claude's Discretion in `17-CONTEXT.md` explicitly leaves the rendered mechanics open. If a future UI-SPEC session picks a different mechanism, the underlying `CLEAR_CALENDAR_URL` sentinel and `save_calendar_url()` contract should still hold — only `handle_post()`'s branch-selection logic would change. |
| A3 | A single generic failure message is sufficient for D-06's "failure and its reason", rather than distinguishing SSRF-refused from network-failed | Common Pitfalls (Pitfall 2) | Low-Medium — this is a UX completeness question, not a correctness one; `FETCH_FAILED` genuinely does not carry more information today, so a plan promising finer-grained copy would need new mechanism this research recommends against building in this phase |

**If this table is empty:** N/A — see rows above. Every stdlib mechanics claim in this document is
`[VERIFIED]` by a command actually run in this session (Standard Stack, Architecture Patterns
Patterns 1-4); the two `[ASSUMED]`-flavoured items above are UI/UX design choices explicitly left
to discretion by `17-CONTEXT.md`, not unverified facts.

## Open Questions

1. **What exact control lets the operator say "disconnect" when the text field is, and always
   looks, empty?**
   - What we know: the sentinel *contract* (`CLEAR_CALENDAR_URL`, compared by identity in
     `save_calendar_url()`) is settled by D-05's instruction to reuse `CLEAR_THEME_ARRIVING`'s
     shape. What is NOT settled is which companion form control decides which branch fires,
     because `theme_arriving`'s own precedent pairs a checkbox with a `<select>` (whose value is
     always present and valid), not with a write-only text input that is *always* rendered empty
     regardless of state.
   - What's unclear: whether "leave the text field blank and click Save" should mean "no change"
     (safe default — matches "the file is invisible to them" per `17-CONTEXT.md`'s Specifics) or
     "disconnect" (matches the literal reading of D-04: "Emptying the field disconnects"). These
     two readings actively conflict for the single most common real submission (a user who never
     touches this field while saving an unrelated setting) unless a second, explicit signal exists.
   - Recommendation: add one explicit control (a "Disconnect calendar" checkbox, or a distinct
     "Disconnect" button/route outside the merged form) that must be the actual trigger for the
     clear branch; the bare text field being empty on its own must NOT trigger a clear, or every
     unrelated Settings save would silently wipe a configured calendar. This is the single design
     decision most likely to cause a real production bug if left implicit — flag it plainly for
     UI-SPEC / plan-time resolution, do not let a plan default to "empty string == disconnect"
     without also gating on an explicit second signal.

2. **Should the new copy add a fifth "not-configured, but the file exists at a wrong mode" status
   string, distinct from D-02's "not configured"?**
   - What we know: D-02 says the read "returns 'not configured' without ever reading the value"
     but the interface "shows a state distinct from both 'not configured' and 'connected', naming
     the problem and the remedy" — i.e. the *page* needs a third, distinct status even though the
     *accessor* degrades to the same boolean as genuine absence.
   - What's unclear: whether `calendar_is_configured()` itself needs to return a tri-state (not
     just `bool`) for the page to render this third status, or whether a separate, page-level
     accessor should independently `os.stat()` the file to detect "exists but mode is wrong" as
     its own signal.
   - Recommendation: keep `calendar_is_configured()` returning a plain `bool` (preserving every
     existing call site's contract) and add a *second*, narrowly-scoped accessor (e.g.
     `calendar_secret_mode_is_unsafe(state_dir)`) that `config_page.calendar_group()` alone
     consults for the third status branch — this avoids widening a well-tested boolean accessor's
     return type.

3. **Does the D-06 sync's `_POLL_LOCK` reuse risk colliding with a concurrent `/poll-now` click?**
   - What we know: `_POLL_LOCK` is a single module-level `threading.Lock()` guarding
     `poll_loop.run_once()`. D-06's sync also needs to call `refresh_calendar_registry()`, but
     NOT the whole `poll_loop.run_once()` — those are different functions with different scopes
     (one refreshes only the calendar registry; the other runs a full detection/render cycle).
   - What's unclear: whether reusing `_POLL_LOCK` for the calendar-only sync is correct (it would
     serialize a Settings save against a manual poll trigger, which seems safe and desirable) or
     whether a second, narrower lock is more correct (avoids blocking a calendar save behind an
     unrelated in-flight full poll cycle, and vice versa).
   - Recommendation: reuse `_POLL_LOCK` for simplicity and because Settings saves are already rare
     relative to poll cycles — but note this explicitly in the plan as a deliberate choice, since
     the two operations don't strictly need to be serialized against each other.

## Environment Availability

Not applicable — every dependency this phase needs (`os`, `stat`, `threading`, `json`) is already
imported by the runtime `server/plane/calendar_rules.py` process today, and no external tool,
service, or CLI is newly required. The `python3` interpreter version used for this session's
verification (3.14.7) differs from production's pinned 3.12, but every stdlib behaviour verified
above (`os.open`'s mode-masking, `os.replace`'s mode-preservation, `stat.S_IMODE`) is unchanged
across that range — confirmed by the absence of any version-gate note in the corresponding CPython
docstrings/man pages consulted.

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | Hand-rolled `check(name, fn)` harness with an `EXPECTED_CHECK_COUNT` ledger per file |
| Config file | none — `scripts/run-all-tests.sh`'s `HARNESSES` array is the single source of truth |
| Quick run command | `server/.venv/bin/python3 server/test_calendar_rules.py` (and similarly for the other two touched files) |
| Full suite command | `scripts/run-all-tests.sh` |

### Phase Requirements → Test Map

This phase has no mapped `REQUIREMENTS.md` IDs (unmapped backlog phase, matching the Phase 10-16
precedent noted in the task scope). Behaviour-to-test mapping instead follows the locked decisions:

| Decision | Behavior | Test Type | Automated Command | File Exists? |
|----------|----------|-----------|-------------------|-------------|
| D-01 | Secret file created at mode 0600 at creation, not via later chmod | unit | `server/.venv/bin/python3 server/test_calendar_rules.py` | ✅ file exists — new checks needed |
| D-01 | `os.replace()` onto a pre-existing wide-mode file corrects it to 0600 | unit | same file | ✅ — new check needed |
| D-02 | A hand-widened file mode causes the read to refuse the secret and report a distinct status | unit | `server/test_calendar_rules.py` (accessor) + `companion/test_config_page.py` (status string) | ✅ both files exist — new checks needed |
| D-03 | `calendar_is_configured()`/`configured_calendar_url()` read the file, not `os.environ`; env var fully inert | unit | `server/test_calendar_rules.py` | ✅ — ~13 existing tests need their fixture rewritten (see Pitfall 3), not just new tests added |
| D-04/D-05 | Emptying/replacing the URL clears prior entries in the same action | unit + integration | `server/test_calendar_rules.py` (registry-clearing) + `companion/test_companion_app.py` (POST /settings end to end) | ✅ — new checks needed |
| D-06 | Save bypasses `CALENDAR_FETCH_INTERVAL_S` for this one call only; poll loop's own throttle unaffected | unit | `server/test_calendar_rules.py` (`min_interval_s` parameter) + `server/test_poll_loop.py` (regression: unchanged default behaviour) | ✅ — new checks needed |
| D-06 | Failure message never contains the URL or `str(exc)` | integration/manual | `companion/test_config_page.py` / `companion/test_companion_app.py` — grep-style assertion that the response body never contains the fixture's test URL substring | ✅ — new check needed |

### Sampling Rate

- **Per task commit:** the single most relevant harness (`server/test_calendar_rules.py`,
  `companion/test_config_page.py`, or `companion/test_companion_app.py` depending on the task)
- **Per wave merge:** `scripts/run-all-tests.sh` (all 19 harnesses)
- **Phase gate:** full suite green, plus `ruff check .` (no lint step exists inside
  `run-all-tests.sh` — CI's `ruff check .` is a separate blocking job; run it locally before every
  commit, since a green local suite does not prove CI green)

### Wave 0 Gaps

- None — all three touched test files (`server/test_calendar_rules.py`, `companion/test_config_page.py`,
  `companion/test_companion_app.py`) already exist, are already registered in
  `scripts/run-all-tests.sh`'s `HARNESSES` array, and already have a working `EXPECTED_CHECK_COUNT`
  ledger (currently 76 / 127 / 165 respectively) to increment.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | no | Reuses the existing shared-password session gate unchanged; no new auth surface |
| V4 Access Control | yes | The new field rides the already-`require_session()`-gated `POST /settings` route — no new route, confirmed by the same pattern Phase 16's `T-16-CSRF` transfer used (verify no new `do_POST()` branch is added for this field) |
| V5 Input Validation | yes | Membership/shape checks before use, matching every other `handle_post()` field (`device_config.THEME_IDS` membership tests are the model); URL shape validation is optional per Claude's Discretion, but if added must not create a second URL-acceptability definition |
| V6 Stored Cryptography | no | No encryption at rest is in scope (explicitly an anti-goal); D-01's mode-0600 file is a discretionary-access-control property, not a cryptographic one |
| V7 Error Handling and Logging | yes | The single highest-severity concern in this phase: never log or flash the raw URL or `str(exc)` — verified `fetch_ics()`/`refresh_calendar_registry()` already enforce this on the existing path; the NEW companion-side code must not reintroduce it via its own `try/except` |
| V9 Communication | no (unchanged) | HTTPS-only fetch with SSRF hardening is entirely Phase 16's, untouched by this phase |
| V12/V14 Configuration | yes | File permission (0600) as the access-control boundary for a secret stored outside the process environment; `deploy/skypane.env.example` line removal is a configuration-hygiene item |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Secret written at default umask, briefly or permanently world/group-readable | Information Disclosure | Mode set at `os.open()` creation time, never via a later `chmod()` (D-01, verified this session) |
| A future code path reading `os.environ.get(CALENDAR_URL_ENV_VAR)` after retirement, silently resurrecting the old source | Tampering (of configuration provenance) | `CALENDAR_URL_ENV_VAR` fully removed, not merely deprecated-but-present; a plan-time grep for the string across the repo (deploy files, code, docs) after the change is a cheap, valuable verification step |
| Flash message or log line embedding the submitted URL or an exception's string form | Information Disclosure | Opaque flash keys only (existing `_resolve_flash_text()` pattern); no `try/except` around `refresh_calendar_registry()` that touches `str(exc)` — none is needed, since that function never raises |
| A crafted `calendar_url` POST value reaching `save_calendar_url()` unvalidated (e.g. a value containing path-traversal-shaped or NUL-byte content) | Tampering | The value is written as file *content*, not used as a path component anywhere — `calendar_secret_path()` is a fixed, hardcoded filename inside `state_dir`, never derived from user input, so path traversal is structurally impossible here regardless of content validation choices |
| A hand-edited secret file left with a permissive mode by a future operator/deploy step | Information Disclosure | D-02's read-time mode check refuses the secret rather than silently trusting or silently repairing it |

## Sources

### Primary (HIGH confidence)

- Live commands run against this session's local CPython 3.14.7 interpreter (`os.open`,
  `os.replace`, `os.fdopen`, `stat.S_IMODE`, `os.umask` — full transcripts inlined above under
  Architecture Patterns 1-4)
- Local BSD `open(2)` and `chmod(1)` man pages (`man 2 open`, `man chmod`) — quoted verbatim above
  for the umask-masking and group-ID-inheritance claims
- `server/plane/calendar_rules.py` read at HEAD (this worktree) — `write_calendar_registry()`
  (:697-728), `calendar_is_configured()`/`configured_calendar_url()` (:504-538), `fetch_ics()`
  (:980-1076), `refresh_calendar_registry()` (:1100-1202), `calendar_fetch_is_due()` (:766-789),
  the `FETCH_*` constants (:163-167)
- `server/device_config.py` read at HEAD — `CLEAR_THEME_ARRIVING` (:98-111),
  `normalise_theme_arriving()`/`normalise_calendar_theme_id()` (:456-509), `save_device_config()`
  (:646-760)
- `companion/pages/config_page.py` read at HEAD — `calendar_group()` (:876-960), `handle_post()`
  (:1563-1770), the copy constants (:321-349), the flash-key constants (:234-262)
- `companion/app.py` read at HEAD — `page_context()`'s calendar keys (:1018-1033),
  `_handle_poll_now()` (:1911-1941), `_resolve_flash_text()` (:449-479), `FLASH_MESSAGES` (:222-260)
- `companion/auth.py` read at HEAD — `configured_password()` (:64-74), the fail-closed
  `AuthNotConfigured` shape
- `deploy/provision.sh` (:70-77), `deploy/skypane-companion.service` / `deploy/skypane-poll.service`
  (`ReadWritePaths`/`EnvironmentFile` lines), `deploy/skypane.env.example` (:85-90) — all read at HEAD
- `server/test_calendar_rules.py` / `companion/test_config_page.py` / `companion/test_companion_app.py`
  read at HEAD for `EXPECTED_CHECK_COUNT` values and `CALENDAR_URL_ENV_VAR` fixture-usage counts
- `.planning/phases/17-.../17-CONTEXT.md` — the phase's own locked decisions (dense, verified
  file:line references already cross-checked against the shipped code in this session)
- `.planning/phases/16-.../16-SECURITY.md` — Phase 16's verified threat register, used to confirm
  the "companion already holds/reads the URL in-process" correction and to source the FETCH_*
  constant list

### Secondary (MEDIUM confidence)

None used — every claim above was either directly verified against shipped code/live commands or
is an explicit, flagged discretionary recommendation (see Assumptions Log).

### Tertiary (LOW confidence)

None.

## Metadata

**Confidence breakdown:**
- Stdlib file-mode mechanics (D-01/D-02): HIGH — empirically verified this session against a live
  interpreter, cross-checked against BSD man pages
- Code-reuse recommendations (write idiom, sentinel pattern, flash pattern, lock reuse): HIGH —
  read directly from shipped code at HEAD, not inferred from docstrings alone
- The clear-vs-unchanged form control mechanism (Open Question 1): MEDIUM — the underlying sentinel
  contract is settled, but the exact rendered control is explicitly left to discretion and flagged
  as the phase's one genuinely novel UI decision
- D-06's failure-message granularity limits (`FETCH_REJECTED_URL` dead code): HIGH — confirmed by
  direct grep of the shipped module; zero call sites return that constant

**Research date:** 2026-09-08
**Valid until:** effectively indefinite for the stdlib claims (CPython's `os.open`/`os.replace`
mode semantics have been stable since long before 3.9); re-verify the code-location line numbers
and `EXPECTED_CHECK_COUNT` values if planning is deferred more than a few phases, since this
codebase's own history shows those numbers shift with almost every plan.
