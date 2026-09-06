---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
audited: 2026-09-06
auditor: gsd-security-auditor
asvs_level: 1
block_on: high
threats_total: 21
threats_closed: 21
threats_open: 0
threats_open_nonblocking: 0
unregistered_flags: 3
status: secured
---

# Phase 13 — Security Audit

**Verification basis:** every verdict below was read out of the current source tree, not
out of a plan's `<threat_model>` claim. A code review ran after the plans closed and found
two blockers, so a plan-time assertion is treated as a hypothesis here, never as evidence.
All five harnesses were executed against the project venv during this audit and pass:
`manual_resolutions 23/23`, `enrich 59/59`, `poll-loop 64/64`, `companion-app 159/159`,
`status-pages 149/149`.

**Severity note.** The dispatching register listed `T-13-03` at `medium`; `13-01-PLAN.md`
declares it `high` and `13-04-PLAN.md` declares it `medium`. Per the "highest severity
wins" rule this audit grades it **high**. It is CLOSED either way, so the gate is
unaffected.

---

## Threat Verification

| Threat ID | Category | Severity | Disposition | Status | Evidence |
|-----------|----------|----------|-------------|--------|----------|
| T-13-01 | Tampering/Spoofing | high | mitigate | CLOSED | `companion/app.py:1260-1262` (membership test is the first statement), `:511-552` (`_illustration_filenames()`), `:1127-1129` (GET twin); `companion/test_companion_app.py:3260` |
| T-13-02 | Tampering | high | mitigate | CLOSED | `server/plane/manual_resolutions.py:85,98,194-205,277,356`; `companion/app.py:548`; `server/plane/illustrations.py:585,660`; `server/test_manual_resolutions.py:483` |
| T-13-03 | Tampering | high | mitigate / transfer | CLOSED | `server/plane/manual_resolutions.py:74,114,201-204` (one gate, applied at write and at read); `companion/pages/airlines_page.py:905-910` (render guard); `server/test_manual_resolutions.py:142,198` |
| T-13-04 | DoS | medium | mitigate / transfer | CLOSED | `server/plane/manual_resolutions.py:70,262-264,369-370`; `companion/app.py:547`; `server/test_manual_resolutions.py:213` |
| T-13-05 | Tampering (stored XSS) | medium | mitigate | CLOSED | `companion/layout.py:429-441` (`html.escape(quote=True)`); `airlines_page.py:780-787,861,912,919,961,973,989,1052-1053`; `health_page.py:2045-2055,2153-2173`; `app.py:231-253` (static flash map); `test_status_pages.py:2568,6379` |
| T-13-06 | Tampering | medium | mitigate | CLOSED | `server/plane/manual_resolutions.py:133` (`_WRITE_LOCK`), `:377-389`, `:429-441` (pid+tid temp name, `os.replace`, stray-tmp cleanup, `makedirs` inside the guarded `try`); `server/test_manual_resolutions.py:311,327,437,456` |
| T-13-07 | Spoofing (CSRF) | medium | **accept** | CLOSED — accepted risk | `companion/auth.py:138,148`; see Accepted Risks §1 |
| T-13-08 | Spoofing/Tampering | high | mitigate | CLOSED | `airlines_page.py:739-741` (normalisation inside `unresolved_row_for_prefix()`), `:849-859`; `app.py:1387-1392` (re-validate on write, `row[0]` used thereafter), `:1404,1424` (`quote(prefix, safe="")`); `test_companion_app.py:3673`, `test_status_pages.py:6379` |
| T-13-10 | Tampering | medium | mitigate | CLOSED | `server/plane/manual_resolutions.py:394-443` (JSON only; zero path construction under the override dir); `app.py:1450-1461`; `server/test_manual_resolutions.py:291`, `test_companion_app.py:3851` |
| T-13-12 | DoS | high | mitigate | CLOSED (residual, see Open Warnings §1) | `manual_resolutions.py:249-255,379,383,431,435`; `enrich.py:679-689,1000-1010`; `poll_loop.py:733` |
| T-13-13 | Elevation of Privilege | high | mitigate | CLOSED | `companion/pages/health_page.py` holds zero `<form` and exactly one `<button` literal (the docstring at `:1948`); the affordance is an `<a href>` at `:2045-2055` / `:2153-2173`; executable source assertion at `test_status_pages.py:2625-2644` |
| T-13-14 | Information disclosure | low | **accept** | CLOSED — accepted risk | `companion/app.py:1581-1583`; see Accepted Risks §2 |
| T-13-15 | Spoofing | medium | mitigate | CLOSED | `server/plane/enrich.py:683-689` — static table read first with an immediate return; the manual lookup is only reached after a static miss. Branch order, not a comparison |
| T-13-16 | Tampering | medium | mitigate | CLOSED | `server/plane/enrich.py:947-1010` (gated on `airline_from_callsign()`, never on `route_source`); `server/poll_loop.py:1085` — before the miss branch (`:1086`), before `trim_unresolved_prefixes()` (`:1088`) and before the write-back (`:1089`) |
| T-13-17 | Repudiation | low | **accept** | CLOSED — accepted risk | `server/history_db.py:114`; `health_page.py:394-396`; see Accepted Risks §3 |
| T-13-18 | Tampering | low | mitigate | CLOSED (regression guard missing, see Open Warnings §2) | `companion/pages/airlines_page.py` holds zero `<script`, zero `on*=` inline handlers; the suggestion list is a native `<datalist>` at `:798-807`; every control is a plain `<form>` or `<a>` |
| T-13-19 | Tampering | medium | mitigate | CLOSED | `server/poll_loop.py:733` — one `set_manual_registry_state_dir()` at the top of `run_once()`; enrichment reads only the process cache (`manual_resolutions.py:490-508`); the companion never touches that cache (`app.py:891-897`, fresh per-request read) |
| T-13-20 | Tampering | high | mitigate | CLOSED | No `save_poll_state` caller exists anywhere under `companion/` — only `load_poll_state` (`health_page.py:1876`, `airlines_page.py:742`). `git show --stat` for both plan-13-05 commits (`9b55ba9`, `6c23a58`) touches `server/` only |
| T-13-21 | DoS | low | **accept** | CLOSED — accepted risk | See Accepted Risks §4 |
| T-13-22 | Elevation of Privilege | high | mitigate | CLOSED | `companion/app.py:1732-1735` and `:1740-1747` — `require_session()` is the first statement in both branches, before the path slice and before any registry read or write; `test_companion_app.py:3623` |
| T-13-SC | Tampering | n/a | **accept** | CLOSED — accepted risk | `git diff --stat` across `893fbc6..385db33` touches no `requirements*.txt`, `pyproject.toml` or `package.json`; see Accepted Risks §5 |

**Blocking-open count (`threats_open`): 0.** No threat is open at or above the `high`
`block_on` threshold. No threat is open below it either.

---

## The two documented-threat reopenings, examined directly

### T-13-01 — validate-then-join over a set that is no longer frozen at import

**The property holds.** `_illustration_filenames()` is recomputed per request, but nothing
in it is derived from the current request. The union's fixed half is
`illustrations.target_filenames()` (43 vendored names). Its mutable half is one
`"{key}.png"` per entry of `manual_resolutions.load_manual_resolutions(state_dir)` —
durable state that a *prior*, separately authenticated `POST /airlines/resolve` persisted.
`parse_single_uploaded_file()` is single-part-only by construction, so a name and a file
physically cannot travel in one request; there is no single-request path that mints a key
and then uploads to it. `test_companion_app.py:3260` makes exactly this executable: the
same POST 404s and writes nothing before registration, and succeeds after.

The key that survives the membership test is a string-equal match against a set whose
manual half is constrained to `^[a-z0-9][a-z0-9-]*$`, so the `key` later used at
`app.py:1287-1291` and `override_path_for_key(key, state_dir)` cannot be traversal-shaped.
`illustrations._UNSAFE_KEY_RE` at `illustrations.py:585` / `:660` re-checks independently
and holds on its own.

**What would break it,** stated plainly so a future edit is recognisable:
1. Adding any source to the union that reads the *current* request (a form field, a query
   value, a header). The union must stay "server-persisted state only".
2. Dropping the `illustration_key_for_name()` call at `app.py:548` **and** the read-side
   re-validation at `manual_resolutions.py:277` as "redundant". Either one alone still
   holds the line; losing both would leave the boundary resting solely on
   `_UNSAFE_KEY_RE`, which permits a leading `-` and does not know about the reserved
   `generic-*` namespace at all.
3. Moving the membership test below `_read_upload_body()` or below any `os.path.join()`
   on `key`. Its position as the first statement of `_handle_illustration_replace()` is
   the property, not a style choice.

### T-13-02 — an invariant relocated from a fixed table to a runtime allowlist

**The property holds, and it is enforced at three independent points, not one.**
`airline_from_callsign()` can now return operator-supplied text, so the old "fixed-table
values only" guarantee is genuinely gone. Its replacement is `illustration_key_for_name()`
(`manual_resolutions.py:174-205`), which applies, in this order: `_HOSTILE_NAME_RE`
against the **raw** name (before slugging — this is the load-bearing ordering, since
`normalise_airline_key()` would otherwise reduce `"../../etc/passwd"` to the
innocent-looking `"etc-passwd"`), then `_SAFE_KEY_RE` against the slug, then the
reserved-namespace checks. That one function is called from:
- `add_entry():356` — before the filesystem is touched at all;
- `load_manual_resolutions():277` — on every read, so a hand-edited file cannot smuggle a
  name past the write gate;
- `_illustration_filenames():548` and `_resolve_section_html():905` and
  `_manual_resolution_rows():1021` — before any key reaches a path builder.

`server/test_manual_resolutions.py:483` sweeps `"../../etc/passwd"`, `"a/b"`,
`"..\\..\\x"`, `"Generic Fallback"`, `"generic-a320"`, over-length and non-string inputs,
and asserts the registry is still empty afterwards.

**What would break it:**
1. A second writer to `manual_resolutions.json` that does not route through `add_entry()`.
   The read-side gate at `:277` is what makes this survivable today — so removing that gate
   is the single most dangerous edit in this module.
2. `entry_rows()` (`:446-465`) does **not** re-apply the gate; it type-checks only. It is
   safe today because every caller feeds it a `load_manual_resolutions()` result, and
   `_manual_resolution_rows()` re-gates before touching a path. Feeding `entry_rows()` a
   raw `json.load()` dict and then joining its names into a path would reopen the threat.
3. Relaxing `_HOSTILE_NAME_RE` to a slug-shape check alone. The raw-input layer is not
   redundant with the slug layer; it is the only thing that distinguishes "refused" from
   "silently stored under an unrelated name".

---

## Accepted Risks

### 1. T-13-07 — no CSRF token on the two new state-changing routes (medium)

**Accepted, and legitimately so — not an oversight.** `companion/auth.py:138` issues the
session cookie as `HttpOnly; Secure; SameSite=Strict; Path=/`, and `:132` names
`SameSite=Strict` as *the* CSRF control for this service. No route in this codebase carries
a CSRF token: `POST /settings`, `POST /poll-now`, `POST /theme`, and
`POST /illustration/{key}.png` all rely on the same single mechanism.
`POST /airlines/resolve` and `POST /airlines/manual-resolutions/{prefix}/delete` join that
posture rather than inventing a second one for two routes alone, and both handlers
document the decision inline (`app.py:1379-1382`, `:1255-1259`). Single-operator,
single-role app at ASVS L1. **Residual risk:** a browser that ignores `SameSite` would
leave every state-changing route in the app exposed equally; the new routes add no
incremental exposure. Reconsider if a second role, a second origin, or an embeddable
surface is ever introduced.

### 2. T-13-14 — Health page information disclosure (low)

**Accepted.** `/health` already sits behind `require_session()` (`app.py:1581-1583`).
Plan 13-02 added a navigation anchor built from data the page already rendered — no new
route and no new data source. Unchanged posture.

### 3. T-13-17 — `route_source` gains a fifth value in `runway_events` (low)

**Accepted.** `server/history_db.py:114` declares `route_source TEXT` with no `CHECK`
constraint, so no migration is implied and no storage-layer invariant is broken. The only
real exposure was a display-layer omission, and it is closed: `health_page._SOURCE_ROWS`
carries the fifth `("manual", …)` tuple at `:394-396`, asserted by
`test_status_pages.py:2530`.

### 4. T-13-21 — per-request JSON reads on every authenticated request (low)

**Accepted.** The read is bounded by `MANUAL_RESOLUTION_MAX_ENTRIES = 200` regardless of
what is on disk, at one operator's traffic volume, and it is the same order as the
unconditional `device_config.load_device_config()` already in `page_context()`.
**Correction to the plan's arithmetic:** the accept was written as "one small bounded read
per request"; a `GET /airlines?resolve=…` actually performs two (`app.py:897` and
`airlines_page.py:863`). Immaterial at this scale — the accept stands — but the stated
basis is off by one and should not be quoted as a bound.

### 5. T-13-SC — package installs (n/a)

**Accepted.** Verified, not taken on trust: `git diff --stat 893fbc6~1..385db33` over
`server/requirements.txt`, `server/requirements-dev.txt`, `pyproject.toml` and
`package.json` is empty. The phase installs zero packages.

---

## Open Warnings (not threats; no gate impact)

### 1. WR-01 weakens T-13-12's stated contract without currently reopening it

`manual_resolutions_path()` (`:136-138`) has no type guard, so `os.path.join(None, …)`
raises `TypeError` — a type not caught by `load_manual_resolutions()`'s
`except (OSError, ValueError)` at `:252`, and raised before the guarded `try` in both
`add_entry()` (at `:368`/`:376`) and `delete_entry()` (at `:422`/`:428`). Three docstrings
claim "never raises"; for `state_dir=None` all three are false.

T-13-12 stays CLOSED because the declared mitigation is present where the threat lives:
`os.makedirs()` is now inside the guarded `try` (`:379`, `:431` — the CR-01 fix, verified),
every I/O failure degrades to `ADD_FAILED`/`False`/`{}`, and neither reachable caller can
supply `None` — `poll_loop` gets a string from argparse and
`set_manual_registry_state_dir()` guards falsy input at `:484`. The concern is the split
posture: `_illustration_filenames()` (`app.py:546`) and `_manual_resolutions_section_html()`
(`airlines_page.py:1144`) both work around the contract with an ad-hoc `if state_dir:`,
while `page_context()` (`app.py:897`) and both POST handlers rely on it unguarded. Fixing
it at the one choke point would make the split disappear.

### 2. T-13-18's declared regression assertion does not exist

The mitigation is real — `airlines_page.py` contains zero `<script`, zero `on*=` handlers,
and the datalist is native. But 13-04-PLAN.md declared it "asserted by a zero-count grep
for script elements and inline event-handler attributes", and no such check exists in
`companion/test_status_pages.py` for this module (the only script-count assertions there,
`:1918-1929` and `:2798-2801`, are Health's chart-bearing page). A future edit could add a
script to this flow with a fully green suite.

### 3. Reviewed and dismissed — open warnings that do NOT undermine any threat

- **WR-05** (`$` matches before a trailing newline in `_PREFIX_RE` / `_SAFE_KEY_RE`):
  no reachable bypass. `normalise_prefix()` calls `.strip()` before matching, and
  `normalise_airline_key()` collapses every non-alphanumeric run — a newline included —
  to a hyphen, so a slug can never carry one. `_RESOLVE_PREFIX_RE`, the one instance the
  review called "fed attacker-controlled text without a preceding strip", no longer exists:
  the WR-04 fix deleted it. Cosmetic contract drift only.
- **WR-13** (`str.isalpha()` accepts non-ASCII uppercase letters in
  `static_airline_name_for_prefix()`): no impact on T-13-15. Registry keys are constrained
  to ASCII `[A-Z]{3}` by `normalise_prefix()`, and the static-table lookup misses for
  anything else. Contract drift in D-06's supersession oracle, not a shadowing path.
- **WR-07, WR-08, WR-09, WR-12**: CSS/DOM shape, a wrong flash string on an unreachable
  branch, a dead parameter, and a wrong success verb. No security surface.

---

## Unregistered Flags (WARNING — new attack surface with no threat mapping)

No SUMMARY.md in this phase emitted a `## Threat Flags` section, so the register was
audited against the source rather than against an executor-declared list. Three pieces of
surface that D-09 widened have no threat ID:

### UF-01 — the normalized-PNG cache is unbounded and its scope assumption is now stale

`companion/illustration_normalize.py:134` is `@functools.lru_cache(maxsize=None)` keyed on
`(path, mtime_ns)`. Its own comment still reads *"The 43 vendored files are therefore
normalized once per process"* — D-09 widened the reachable key space to 43 plus up to 200
operator-minted keys, and because `mtime_ns` is part of the key, **every re-upload of the
same key mints a permanent new entry** that is never evicted from a long-running
`ThreadingHTTPServer`. Authenticated-operator-only, gradual memory growth. The mechanism is
pre-existing; this phase widened its scope and invalidated the comment that bounded it.

### UF-02 — WR-10's temp-path collision carries a validate/decode TOCTOU on the widened key space

`companion/app.py:1287-1291` names both upload temp files `.{key}.{pid}.…tmp` with no
thread identity. Under `ThreadingHTTPServer` all workers share one pid, so two concurrent
uploads for the same key share both paths. Beyond the lost-update and spurious-failure
defects the code review named, there is a time-of-check/time-of-use window: the file is
validated at `:1300` (`validate_illustration_file()`, which is where the pixel-count and
format gates live) and re-opened at `:1307` (`Image.open()`); a racing thread can replace
its contents in between, so bytes that never passed validation reach the decoder. Bounded
in practice by Pillow's own `MAX_IMAGE_PIXELS` bomb guard and by the blanket
`except Exception` at `:1315`, and it requires an authenticated operator racing themselves.
Pre-existing (quick task 260902-v26); D-09 widened the key space it sits on. The one-line
fix WR-10 already proposes (`threading.get_ident()` in both temp names) closes the sharing,
and the same `_WRITE_LOCK` idiom plan 13-01 adopted would close the TOCTOU.

### UF-03 — a malformed registry entry produces a log line on every authenticated render

`server/plane/manual_resolutions.py:287-291` (the WR-03 fix) prints a drop-count line
whenever the raw file holds more entries than survive validation.
`load_manual_resolutions()` runs one to two times per authenticated page render, so a
single hand-edited or over-cap entry emits a log line per request, indefinitely, rather
than once. Log-volume only — the fix itself is correct and the alternative (silent data
loss) was worse.
