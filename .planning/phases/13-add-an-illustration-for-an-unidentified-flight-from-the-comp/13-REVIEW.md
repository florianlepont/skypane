---
phase: 13-add-an-illustration-for-an-unidentified-flight-from-the-comp
reviewed: 2026-09-06T00:00:00Z
depth: standard
files_reviewed: 15
files_reviewed_list:
  - server/plane/manual_resolutions.py
  - server/plane/enrich.py
  - server/poll_loop.py
  - companion/app.py
  - companion/pages/__init__.py
  - companion/pages/airlines_page.py
  - companion/pages/health_page.py
  - companion/static/style.css
  - scripts/run-all-tests.sh
  - server/test_manual_resolutions.py
  - server/test_enrich.py
  - server/test_poll_loop.py
  - companion/test_companion_app.py
  - companion/test_status_pages.py
  - server/plane/illustrations.py (read-only, cross-reference for path-boundary claims)
findings:
  critical: 2
  warning: 13
  info: 0
  total: 15
status: issues_found
---

# Phase 13: Code Review Report

**Reviewed:** 2026-09-06
**Depth:** standard
**Files Reviewed:** 15
**Status:** issues_found

## Summary

Reviewed the phase-13 manual-resolution registry (`server/plane/manual_resolutions.py`), its
enrichment wiring (`enrich.py`, `poll_loop.py`), and the companion surface that writes it
(`companion/app.py`, `companion/pages/airlines_page.py`, `health_page.py`, `style.css`), plus
the four harnesses. All harnesses I ran pass (`test_manual_resolutions` 19/19,
`test_enrich` 59/59, `test_status_pages` 146/146).

### Security posture verification (the five points raised for this phase)

Four of the five hold; I could not break them:

1. **`T-v26-02-01` (validate-then-join over the widened membership set) — HOLDS.**
   `Handler._handle_illustration_replace()` (`companion/app.py:1260-1262`) still runs the
   membership test on `key` as its first statement, before `_read_upload_body()` and before
   any path is constructed from `key`. The widened half of the set
   (`_illustration_filenames()`, `companion/app.py:546-550`) is derived exclusively from
   `manual_resolutions.load_manual_resolutions(state_dir)` — durable prior server state — and
   never from the current request. Step A (`POST /airlines/resolve`) and Step B
   (`POST /illustration/{key}.png`) are separate requests; there is no single-request path
   that mints a key and then uploads to it. `test_companion_app.py`'s
   `_illustration_manual_key_post_unregistered_then_registered` makes this executable.
2. **The moved purity invariant — BOTH HALVES PRESENT.** `add_entry()` gates through
   `illustration_key_for_name()` at `manual_resolutions.py:295` before touching the
   filesystem, and `load_manual_resolutions()` re-applies the identical gate on every read at
   `manual_resolutions.py:237`. There is no third writer of `manual_resolutions.json`.
   Downstream, `illustrations._UNSAFE_KEY_RE` (`illustrations.py:465`),
   `illustration_path_for_key()` (585) and `override_path_for_key()` (660) each re-check
   independently and do hold on their own.
3. **Reserved-key shadowing — REJECTED at both points.** `RESERVED_KEY_PREFIX = "generic-"`
   covers every `generic-{shape}.png` tier-3 asset and `generic-fallback.png`; the check runs
   inside `illustration_key_for_name()`, which both `add_entry()` and
   `load_manual_resolutions()` call. Confirmed against `illustrations.target_filenames()` —
   there is no reserved artwork key outside the `generic-*` namespace.
4. **`normalise_airline_key()` traversal subtlety — GUARD CORRECTLY PLACED.**
   `_HOSTILE_NAME_RE` (`manual_resolutions.py:97`) is applied to the *raw* name at
   `illustration_key_for_name():180`, i.e. before `normalise_airline_key()` slugs it. Every
   registry entry point (`add_entry`, `load_manual_resolutions`, `_illustration_filenames`,
   `_resolve_section_html`) funnels through that one function; none skips it.
5. **CSRF posture — NO DEVIATION.** Both new POST routes are gated by `require_session()` as
   their first statement (`companion/app.py:1733-1748`) and rely on the same
   `SameSite=Strict` session cookie (`companion/auth.py:138`) as `POST /settings`,
   `POST /poll-now` and `POST /illustration/{key}.png`. No second mechanism was invented.

Also verified: **no new third-party imports** (server stays stdlib + the pre-existing
`requests`/`Pillow`), and **zero JavaScript added** (no `.js` file in the diff; the
suggestion list is a native `<datalist>`).

### What is actually wrong

The defects are not in the traversal story. They are in the **failure-handling contract** of
the new storage module (two never-raises claims that are false, one of which produces an
unhandled exception inside an HTTP request handler on the exact failure mode a dedicated
flash key was written for), in a **user-facing dead end** created by the D-14 gap-clearing
interaction, and in a set of drift/duplication defects where code comments assert guards and
guarantees that do not exist.

---

## Critical Issues

### CR-01: `add_entry()` / `delete_entry()` raise on an unwritable state dir — the exact failure the `manual_save_failed` / `manual_delete_failed` flash keys were added for

**File:** `server/plane/manual_resolutions.py:314` and `server/plane/manual_resolutions.py:358`

**Issue:** Both functions document "never raises" and promise `ADD_FAILED` / `False` on a
write failure, and `companion/app.py` builds two dedicated flash keys around that promise —
`FLASH_KEY_MANUAL_SAVE_FAILED` literally reads *"Couldn't save that resolution — the frame's
state directory may not be writable."* But `os.makedirs(state_dir, exist_ok=True)` sits
**outside** the `try:` block that starts on the next-but-one line. Any `OSError` from
`makedirs` therefore escapes the function, escapes `Handler._handle_manual_resolve_post()`,
and escapes `do_POST()` — `BaseHTTPRequestHandler` sends no response at all; the client gets a
dropped connection and the operator gets nothing.

The idiom was copied verbatim from `server/device_config.py:635`, where it is harmless
*because that function's contract is to re-raise* (`raise` at line 648). Copying the statement
order without the contract inverts the outcome.

Reproduced against the real module:

```
$ python3 -c "... m.add_entry('/tmp/mrro/newdir','ABC','Test Air')"
add RAISED PermissionError [Errno 13] Permission denied: '/tmp/mrro/newdir'

$ python3 -c "... m.add_entry('/tmp/mrtest/blocker','ABC','Test Air')"   # state_dir is a file
add RAISED FileExistsError [Errno 17] File exists: '/tmp/mrtest/blocker'
```

**Fix:** Move `makedirs` inside the guarded region in both functions:

```python
    path = manual_resolutions_path(state_dir)
    tmp = path + ".tmp"
    try:
        os.makedirs(state_dir, exist_ok=True)
        with open(tmp, "w") as fh:
            json.dump(registry, fh, indent=1)
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            try:
                os.remove(tmp)
            except OSError:
                pass
        return ADD_FAILED   # / return False in delete_entry()
```

Add a harness check for it — see WR-11; today nothing exercises either failure key.

---

### CR-02: Step B ("add an illustration") becomes unreachable as soon as the poll cycle clears the resolved prefix — the phase's own headline capability, and its "Skip — I'll add artwork later" copy, both dead-end

**File:** `companion/pages/airlines_page.py:803-806` (with `server/poll_loop.py:1085` and
`server/plane/enrich.py:947`)

**Issue:** The *only* route to the Step B upload zone is `/airlines?resolve={prefix}`, and
`_resolve_section_html()` renders it only when `unresolved_row_for_prefix()` returns a row —
i.e. only while `{prefix}` is still a live member of `poll_state.json`'s
`unresolved_prefixes`. D-14's new `enrich.clear_resolved_unresolved_prefix()` call
(`poll_loop.py:1085`) deletes exactly that entry on the first poll cycle that detects a
flight with the now-resolved prefix.

Consequence chain, all reachable:

1. Operator does Step A, then clicks `STEP_B_SKIP_TEXT` — *"Skip — I'll add artwork later"*
   (`airlines_page.py:246`).
2. Next cycle detects a flight with that prefix → the gap entry is removed.
3. Health no longer lists the prefix, so the "Resolve" deep link (D-10) is gone.
4. Navigating to `/airlines?resolve={prefix}` now renders `RESOLVE_STALE_BODY` ("That
   coverage gap isn't there anymore"), not Step B.
5. The manual-resolutions management list offers only **Delete** — no "add artwork" affordance.
6. `POST /airlines/resolve` for that prefix now returns `manual_prefix_stale` and writes
   nothing, so D-07's documented *"delete and re-add to point it somewhere else"* correction
   path (`SUPERSEDED_CAPTION`, `airlines_page.py:288`) is also blocked — the operator must
   delete the entry **and then wait for another live detection** before the prefix reappears
   in the gap registry.

The frame is meanwhile captioning real flights with the operator's airline name over the
generic fallback artwork, with no in-app way to fix it. The gallery grid is built from
`illustrations.target_variants_by_airline()` (static only), so manual airlines never appear
there either.

**Fix:** Decouple the artwork-upload affordance from the gap registry. The cheapest correct
change is to add an upload path keyed on the *manual entry* rather than on the gap:

```python
# _manual_resolution_row_html(): when the stored name has no resolved artwork,
# render a link to a resolve view driven by the manual registry, not the gap registry.
key = manual_resolutions.illustration_key_for_name(airline_name)
if key and illustrations.resolved_illustration_path(key, state_dir) is None:
    artwork_cell = '<a href="%s?%s=%s">%s</a>' % (
        AIRLINES_ROUTE, RESOLVE_QUERY_PARAM, escape_html(prefix), ADD_ARTWORK_LINK_TEXT)
```

and, in `_resolve_section_html()`, fall through to Step B when
`unresolved_row_for_prefix()` returns `None` **but** `manual_resolutions` holds an entry for
the prefix whose key has no artwork — rendering the upload zone without the sighting-context
`<dl>` (which genuinely has no data left). Alternatively, gate
`clear_resolved_unresolved_prefix()` so it does not clear a prefix whose manual entry still
lacks artwork. If the dead end is an accepted trade-off, `STEP_B_SKIP_TEXT` must stop
promising "later" and the management list must say where "later" is.

---

## Warnings

### WR-01: `load_manual_resolutions()` / `add_entry()` / `delete_entry()` raise `TypeError` for `state_dir=None`, contradicting three "never raises" docstrings

**File:** `server/plane/manual_resolutions.py:194`, `:247`, `:332` (via `manual_resolutions_path():124`)

**Issue:** `manual_resolutions_path(None)` calls `os.path.join(None, ...)`, which raises
`TypeError` — not caught by `except (OSError, ValueError)` at line 219, and evaluated inside
the `try:` expression but outside the caught exception set. Verified:

```
load_manual_resolutions(None) -> RAISED TypeError: expected str, bytes or os.PathLike object, not NoneType
add_entry(None, 'ABC', 'Test Air') -> RAISED TypeError
delete_entry(None, 'ABC')          -> RAISED TypeError
```

`_illustration_filenames()` (`app.py:546`) and `_manual_resolutions_section_html()`
(`airlines_page.py:1042`) both work around this with an ad-hoc `if state_dir:` guard, which
shows the contract is already known to be false at two call sites while
`_resolve_section_html():814` and both POST handlers rely on it unguarded. Production
`--state-dir` always defaults to a string, so this is latent rather than live — but the
guard-vs-no-guard split is exactly how it becomes live after the next refactor.

**Fix:** Make the module honour its own contract at the single choke point:

```python
def manual_resolutions_path(state_dir):
    if not isinstance(state_dir, str) or not state_dir:
        return None
    return os.path.join(state_dir, MANUAL_RESOLUTIONS_FILENAME)
```

and have `load_manual_resolutions()` return `{}`, `add_entry()` return `ADD_FAILED`, and
`delete_entry()` return `False` on a `None` path. Then drop the two ad-hoc `if state_dir:`
guards so there is one rule, not three.

---

### WR-02: Unsynchronised read-modify-write with a fixed `.tmp` filename — lost updates and corruptible JSON under `ThreadingHTTPServer`

**File:** `server/plane/manual_resolutions.py:306-320` and `:352-364`

**Issue:** `add_entry()` and `delete_entry()` both do `load_manual_resolutions()` → mutate →
write-whole-file, with no lock. The companion is a `ThreadingHTTPServer`, so two concurrent
POSTs (an add and a delete, or two adds) interleave: the later `os.replace()` wins and the
other operation is silently lost. Worse, both writers open **the same** `path + ".tmp"`
(`manual_resolutions.json.tmp`) — a fixed name, not a per-request one — so their `json.dump()`
writes interleave into one file descriptor before either `os.replace()` runs, and the atomic
rename can promote a structurally broken JSON document. On the next read that file fails
`json.load()`, `load_manual_resolutions()` degrades to `{}`, and **the entire registry is
gone** on the following write.

`companion/app.py`'s own illustration upload path solved this correctly for its own temp files
(`app.py:1287-1291`, pid-suffixed and dot-prefixed inside the destination dir); this module
did not.

**Fix:** Use a unique temp name and serialise writers:

```python
_WRITE_LOCK = threading.Lock()
...
tmp = "%s.%d.%d.tmp" % (path, os.getpid(), threading.get_ident())
with _WRITE_LOCK:
    registry = load_manual_resolutions(state_dir)   # read inside the lock
    ...
    os.replace(tmp, path)
```

The stray-`.tmp` cleanup in the `except` branch should then unlink that unique name, and the
same treatment applies to `server/device_config.py` (out of scope here, same defect).

---

### WR-03: A single load-time rejection permanently deletes registry data on the next write

**File:** `server/plane/manual_resolutions.py:224-244` (consumed by `:306` and `:352`)

**Issue:** `load_manual_resolutions()` drops every entry that fails any of its five checks,
**and** hard-stops at `MANUAL_RESOLUTION_MAX_ENTRIES` in sorted-key order (line 226). Because
`add_entry()`/`delete_entry()` rewrite the whole file from that already-filtered dict, any
rejected or over-cap entry is *permanently erased* the next time the operator adds or deletes
anything. Concretely: a 250-entry hand-edited or migrated file loses 50 entries the first time
the operator clicks Delete on one row. Likewise a future schema change that makes
`created_at` optional would, on first write, silently destroy every legacy entry that lacked it.

This is a data-loss risk hidden behind a function documented purely as a defensive reader.

**Fix:** Separate "the view I render/serve" from "the document I rewrite". Either preserve
unknown/over-cap entries through the write (load the raw dict for the write path and merge),
or — minimally — make the destructive normalisation explicit and logged:

```python
raw = _load_raw(state_dir)             # untouched parsed dict
registry = _validated_view(raw)        # what callers see today
dropped = len(raw) - len(registry)
if dropped:
    print("manual_resolutions: %d entry/entries will be dropped on next write" % dropped)
```

---

### WR-04: The render path and the write path feed `unresolved_row_for_prefix()` differently-normalised input, contradicting the "can never diverge" claim

**File:** `companion/pages/airlines_page.py:803` vs `companion/app.py:1385-1386`

**Issue:** Three separate comments assert that this function is the single D-11 membership
test shared by both paths "so the two can never diverge"
(`airlines_page.py:686-691`, `companion/pages/__init__.py:72-78`, `app.py:876-885`). They do
diverge on their input:

- write path: `unresolved_row_for_prefix(state_dir, manual_resolutions.normalise_prefix(form.get("prefix")))` — strips and **upper-cases**.
- render path: `unresolved_row_for_prefix(state_dir, prefix_raw)` — the raw `?resolve=` query value.

So `GET /airlines?resolve=afr` renders "That coverage gap isn't there anymore" while
`POST /airlines/resolve` with `prefix=afr` for the same live gap is accepted and persists an
entry. The advertised invariant is that these two answer identically; they do not.

**Fix:** Normalise once, at the boundary, in `unresolved_row_for_prefix()` itself:

```python
def unresolved_row_for_prefix(state_dir, prefix):
    prefix = manual_resolutions.normalise_prefix(prefix)
    if prefix is None:
        return None
    ...
```

and drop the caller-side `normalise_prefix()` in `app.py:1386` so there is exactly one gate.

---

### WR-05: `$`-anchored prefix/slug regexes accept a trailing newline

**File:** `companion/pages/airlines_page.py:265`, `server/plane/manual_resolutions.py:75` and `:84`

**Issue:** In Python, `$` matches at end-of-string **or immediately before a trailing
newline**. `_RESOLVE_PREFIX_RE.match("AFR\n")` is therefore a match, and
`_RESOLVE_PREFIX_RE` is applied to the **raw, unnormalised** query value (see WR-04). Today
nothing exploitable follows — `registry.get("AFR\n")` misses and the function returns `None` —
so the traversal story is unaffected. But this is the one gate in the chain that is fed
attacker-controlled text without a preceding `strip()`, and it is documented as "exactly three
uppercase ASCII letters", which it is not. `_PREFIX_RE` and `_SAFE_KEY_RE` share the pattern
but are shielded by an upstream `.strip()` and by `normalise_airline_key()`'s
non-alphanumeric collapse respectively.

**Fix:** Use `\Z` in all three, so the stated contract is the enforced one:

```python
_RESOLVE_PREFIX_RE = re.compile(r"^[A-Z]{3}\Z")
_PREFIX_RE = re.compile(r"^[A-Z]{3}\Z")
_SAFE_KEY_RE = re.compile(r"^[a-z0-9][a-z0-9-]*\Z")
```

---

### WR-06: A claimed cross-module route-constant guard does not exist; Health hardcodes the resolve URL

**File:** `companion/pages/airlines_page.py:214-222` and `companion/pages/health_page.py:2006`

**Issue:** `airlines_page.py:217-218` states the route constants are *"pinned by a
cross-module equality check in companion/test_status_pages.py (plan 13-06)"*. No such check
exists — grepping both harnesses for `airlines_page.RESOLVE_ROUTE`,
`airlines_page.AIRLINES_ROUTE`, `airlines_page.RESOLVE_QUERY_PARAM` and
`airlines_page.MANUAL_DELETE_ROUTE_PREFIX` returns nothing outside `companion/app.py` itself.

Meanwhile `health_page.RESOLVE_LINK_HREF_TEMPLATE = "/airlines?resolve=%s"` (line 2006) is a
hand-written duplicate of `AIRLINES_ROUTE` + `RESOLVE_QUERY_PARAM`. Renaming either constant
silently breaks D-10's deep link — the only entry point into the whole feature — with a green
suite.

**Fix:** Add the check the comment already promises:

```python
def _resolve_route_constants_agree():
    expected = "%s?%s=%%s" % (airlines_page.AIRLINES_ROUTE, airlines_page.RESOLVE_QUERY_PARAM)
    if health_page.RESOLVE_LINK_HREF_TEMPLATE != expected:
        return False, "health_page's deep-link template drifted from airlines_page's constants"
    return True, ""
```

...or delete the false claim from the comment.

---

### WR-07: `.resolve-upload-zone` does not in fact reuse `.lightbox__replace-zone`'s layout — the DOM shapes differ

**File:** `companion/static/style.css:4426-4444` and `companion/pages/airlines_page.py:864-882`

**Issue:** The CSS comment states the Step B zone *"reuses the exact
`.lightbox__replace-zone` visual treatment verbatim"* and *"No declaration inside any of the
six changes."* The declarations are indeed unchanged — but the markup is not:

- lightbox: `form.lightbox__replace-form > div.lightbox__replace-zone > [icon, label, hint, input, button]` — five direct flex children.
- Step B: `div.resolve-upload-zone > [icon, label, hint, form > [input, button]]` — four, with the input and button buried inside a `<form>`.

`display:flex; flex-direction:column; gap: var(--space-sm)` only applies to *direct* children,
so in Step B the file input and the Upload button lose their column stacking and their `gap`
and reflow as inline content inside the form. `.resolve-upload-zone input[type="file"]` etc.
still match (descendant selectors), which is why this reads as correct at a glance.

**Fix:** Make the form the flex container in Step B so the two DOMs match:

```html
<div class="resolve-upload-zone">
  {icon}
  <form method="post" enctype="multipart/form-data" action="{upload_action}">
    <label for="...">Choose an image</label>
    <p class="lightbox__replace-hint">...</p>
    <input type="file" ...><button type="submit">Upload</button>
  </form>
</div>
```

with `.resolve-upload-zone > form { display: contents; }` (or move the flex declarations onto
the form), and verify the rendered result rather than relying on the shared selector list.

---

### WR-08: `ADD_REJECTED_PREFIX` is mapped to the "enter an airline name" flash

**File:** `companion/app.py:1408-1410`

**Issue:**

```python
if result in (manual_resolutions.ADD_REJECTED_PREFIX,
              manual_resolutions.ADD_REJECTED_NAME_EMPTY):
    flash_key = FLASH_KEY_MANUAL_NAME_EMPTY
```

A prefix-shape rejection tells the operator *"Enter an airline name before saving."* — which is
false and unactionable, since the prefix comes from a hidden field they never typed. The
handler's own docstring calls this out as unreachable ("prefix shape was already proven by
step 2"), which is true today, but pairing an unreachable branch with a known-wrong message is
the worst of both: if it ever becomes reachable it lies, and the pairing hides that.

**Fix:** Route it to `FLASH_KEY_MANUAL_PREFIX_STALE` (the accurate outcome for a prefix that
no longer validates) or to `FLASH_KEY_MANUAL_SAVE_FAILED` alongside the other
should-not-happen results, and leave `FLASH_KEY_MANUAL_NAME_EMPTY` for
`ADD_REJECTED_NAME_EMPTY` alone.

---

### WR-09: `_manual_resolution_rows(state_dir, registry)` never uses `state_dir`

**File:** `companion/pages/airlines_page.py:922`

**Issue:** The parameter is accepted, threaded through from
`_manual_resolutions_section_html():1049`, documented nowhere in the docstring, and never
read — the function's only per-row work is `enrich.static_airline_name_for_prefix(prefix)`,
which takes no state dir. A dead parameter on a function whose sibling
(`unresolved_row_for_prefix(state_dir, prefix)`) *does* use it invites a future caller to
assume this one reads state too.

**Fix:** Drop it: `def _manual_resolution_rows(registry):` and update the single call site.

---

### WR-10: Same-key concurrent uploads collide on a shared temp path (exposure widened by D-09)

**File:** `companion/app.py:1287-1291`

**Issue:** The upload temp files are named `.{key}.{pid}.upload.tmp` /
`.{key}.{pid}.encoded.tmp`. Under `ThreadingHTTPServer` every worker shares one pid, so two
concurrent uploads for the same key write to the same two paths: their bytes interleave,
`validate_illustration_file()` may then validate a mixture, and the `finally` block of the
first thread to finish unlinks the second thread's in-flight temp file (its `os.replace()`
then raises and reports `illustration_replace_failed` for an upload that was fine). This is
pre-existing (quick task 260902-v26), but D-09 widens the reachable key space from the fixed
43-member vendored list to that list plus up to 200 operator-minted keys.

**Fix:** Include the thread identity, matching what WR-02 needs anyway:

```python
uniq = "%d.%d" % (os.getpid(), threading.get_ident())
raw_tmp_path = os.path.join(override_dir, ".%s.%s.upload.tmp" % (key, uniq))
encoded_tmp_path = os.path.join(override_dir, ".%s.%s.encoded.tmp" % (key, uniq))
```

---

### WR-11: The two planner-added failure flash keys are completely untested

**File:** `server/test_manual_resolutions.py` (20 `check()` calls) and `companion/test_companion_app.py`

**Issue:** `FLASH_MANUAL_SAVE_FAILED` and `FLASH_MANUAL_DELETE_FAILED` were added specifically
because *"`add_entry()` returns ADD_FAILED on an unwritable state dir and never raises"*
(`airlines_page.py:194-201`). No harness ever puts `add_entry()` or `delete_entry()` in front
of an unwritable state dir: grepping `test_manual_resolutions.py` for `chmod`, `ADD_FAILED`,
`unwritable` or `read-only` returns nothing. That is precisely why CR-01 shipped — the
untested claim was the false one.

**Fix:** Add two checks that make the contract executable:

```python
def _add_entry_on_unwritable_state_dir_returns_failed():
    with tempfile.TemporaryDirectory() as parent:
        os.chmod(parent, 0o500)
        try:
            result = m.add_entry(os.path.join(parent, "state"), "ABC", "Test Air")
        finally:
            os.chmod(parent, 0o700)
    if result != m.ADD_FAILED:
        return False, "expected ADD_FAILED for an uncreatable state dir, got %r" % (result,)
    return True, ""
```

plus the `delete_entry()` mirror and a `load_manual_resolutions(None)` case for WR-01.

---

### WR-12: Step B's success message says "Illustration replaced" for a first-ever illustration

**File:** `companion/app.py:212-213` (reached from `airlines_page.py:864-877`)

**Issue:** The Step B upload form posts to `/illustration/{key}.png`, whose success path
redirects with `FLASH_KEY_ILLUSTRATION_REPLACED`: *"Illustration replaced — will apply on the
frame's next scheduled refresh."* For a manual key there was never an original to replace —
the whole point of Step B is that `resolved_illustration_path(key, state_dir)` returned `None`.
13-CONTEXT.md's governing constraint is that the operator is never misled; this phase added
`FLASH_KEY_MANUAL_RESOLVED` explicitly to honour that for Step A and then reused the wrong
verb for Step B. (The "next scheduled refresh" half is also weaker than the
`FLASH_KEY_MANUAL_RESOLVED` latency wording adopted three lines below.)

**Fix:** Add a distinct `FLASH_KEY_ILLUSTRATION_ADDED` ("Illustration added — the frame will
pick it up next time it wakes and polls.") and have `_handle_illustration_replace()` choose
between the two based on whether `illustrations.resolved_illustration_path(key, state_dir)`
was `None` before the write.

---

### WR-13: `static_airline_name_for_prefix()`'s ASCII guarantee is not what the code enforces

**File:** `server/plane/enrich.py:643`

**Issue:**

```python
if not isinstance(prefix, str) or len(prefix) != 3 or not prefix.isalpha() or prefix != prefix.upper():
```

The docstring promises *"`None` for anything that is not exactly three uppercase ASCII
letters"*. `str.isalpha()` is `True` for any Unicode letter, so `"ÀÉÎ"` (three uppercase
non-ASCII letters) passes every clause and reaches `_ICAO_AIRLINE_PREFIXES.get()`. The lookup
then misses, so behaviour is currently correct by accident — but this function is D-06's
supersession oracle and its stated contract is what the next caller will rely on.

**Fix:** Enforce what is documented:

```python
_STATIC_PREFIX_RE = re.compile(r"^[A-Z]{3}\Z")
...
if not isinstance(prefix, str) or not _STATIC_PREFIX_RE.match(prefix):
    return None
return _ICAO_AIRLINE_PREFIXES.get(prefix)
```

This also reuses the same three-letter shape gate `_PREFIX_RE` and `_RESOLVE_PREFIX_RE`
already state, instead of a fourth hand-rolled variant.

---

_Reviewed: 2026-09-06_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
