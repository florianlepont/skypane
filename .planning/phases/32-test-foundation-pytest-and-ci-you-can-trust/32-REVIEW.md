---
phase: 32-test-foundation-pytest-and-ci-you-can-trust
reviewed: 2026-09-23T00:00:00Z
depth: standard
files_reviewed: 34
files_reviewed_list:
  - .github/workflows/ci.yml
  - .github/workflows/firmware.yml
  - .gitignore
  - companion/test_browser_ux.py
  - companion/test_browser_ux_health_drawings.py
  - companion/test_browser_ux_helpers.py
  - companion/test_browser_ux_quiet_wake.py
  - companion/test_companion_app.py
  - companion/test_legacy_harness_shim.py
  - conftest.py
  - deploy/deploy.sh
  - deploy/provision.sh
  - pyproject.toml
  - scripts/lock-deps.sh
  - scripts/run-all-tests.sh
  - server/requirements-dev.in
  - server/requirements.in
  - server/test_calendar_rules.py
  - server/test_colour_rules.py
  - server/test_config_history.py
  - server/test_dither.py
  - server/test_enrich.py
  - server/test_illustrations.py
  - server/test_manual_resolutions.py
  - server/test_notify.py
  - server/test_panel_preview.py
  - server/test_pipeline_e2e.py
  - server/test_plane_detection.py
  - server/test_poll_loop.py
  - server/test_render.py
  - server/test_runway_config.py
  - stub-server/test_poll_cycle.py
  - test-support/sitecustomize.py
  - test-support/skypane_test_support.py
  - test-support/test_test_support.py
findings:
  critical: 2
  warning: 7
  info: 5
  total: 14
status: issues_found
---

# Phase 32: Code Review Report

**Reviewed:** 2026-09-23
**Depth:** standard
**Files Reviewed:** 34
**Status:** issues_found

## Narrative Findings (AI reviewer)

## Summary

I read all of the test-support code (`skypane_test_support.py`, `sitecustomize.py`, `test_test_support.py`), plus `conftest.py`, `ci.yml`, `firmware.yml`, `deploy.sh`, `run-all-tests.sh`, `lock-deps.sh`, `pyproject.toml` and the legacy shim. For the migrated test files, I checked the migration mechanically rather than line by line:
- AST scans for tuple or constant asserts, `return (bool, msg)` results that get thrown away, tests with no assertion, and tests whose only assertions sit inside loops over non-literal iterables.
- A comparison of every old `check()` name with the new test names and docstrings.
- A count of old failure paths against new assert/fail/raises sites.
- Hand-diffs of the grouped files (`test_poll_cycle.py`, `test_pipeline_e2e.py`, the pacing block of `test_poll_loop.py`, and the calendar ambiguity setup).

**Migration artifacts:** I found no transform artifact that silently weakens a test. There are:
- no tuple asserts;
- no left-over `return False, ...` inside a test body;
- no bool-returning helper whose result is discarded (`verify_panel_bytes`, `validate_display_response` and `_digest_verdict` are all asserted at every call site);
- no new `skip` or `xfail`.

Every loop-only-assert test I checked either loops over a literal, or has a sibling test that asserts the collection is non-empty. The grouped scenario tests keep every old step as an ordered assert. Their cost is reduced isolation: the first failure hides every later step. The one old check with no counterpart ("FIXTURE_ICS setup") became a module-level assert, which turns into a collection error — louder, not weaker.

**What I verified live:**
- **Proxy bypass:** it is real. With the guard installed and `HTTPS_PROXY=http://127.0.0.1:<port>`, `requests.get("https://api.adsbdb.com/...")` returned a real **HTTP 200**.
- **No current test leaks:** I ran the full pytest suite and all 9 legacy harnesses through a local logging proxy that refuses and records every CONNECT. It recorded zero CONNECTs, so no current test leaks today. The gap is latent, and GitHub-hosted CI (no proxy) is unaffected.
- **Subprocess coverage:** it is mostly lost. `byos_server.py` measures **50%** under the shipped config and **91%** with `sigterm = true`.
- **Subset runs:** `scripts/run-all-tests.sh <subset>` always exits 1 on the coverage gate, even when every test passes.

**CI deploy:** `cancel-in-progress: false` does protect an in-flight deploy. However, the stale-commit guard is wrong in the other direction. It skips a legitimate deploy whenever `main` has moved on to a commit that will never deploy itself (a docs-only push that `paths-ignore` filters out, or a push whose tests fail). The job still goes green.

## Critical Issues

### CR-01: The network guard is bypassed whenever an HTTP(S) proxy env var points at loopback

**Files:** `test-support/skypane_test_support.py:108-123` (`install_child_network_guard`), `test-support/skypane_test_support.py:310-337` (`child_env`), `conftest.py:421-436` (`_block_non_loopback_dns`)

**Issue:** The guard has two layers:
1. DNS lookups are allowed only for loopback names.
2. `connect()` is allowed only to `127.0.0.1`, `::1` and `localhost`.

`requests` and `urllib` read `HTTPS_PROXY`, `HTTP_PROXY` and `ALL_PROXY` (upper and lower case). When one of these points at a loopback proxy, the client:
- resolves only the proxy host (`127.0.0.1`), which passes the DNS guard;
- connects to `127.0.0.1:<port>`, which passes the connect guard;
- sends `CONNECT api.adsbdb.com:443`. The real hostname is resolved by the proxy, never locally.

Neither layer ever sees the real destination.

- **Reproduced:** with `install_child_network_guard()` active and the ambient `HTTPS_PROXY=http://127.0.0.1:40891`, `requests.get("https://api.adsbdb.com/v0/callsign/AFR1234")` printed `LEAKED status 200`. With the proxy vars unset, the same call raises `NetworkAccessBlocked`.
- **In-process tests:** the pytest process has the same hole, because the fixture only patches the resolvers.
- **Child processes:** `child_env()` copies `os.environ`, proxy vars included, into every child.

**Severity:** BLOCKER. This is the phase's headline hermeticity control (TST-03), and it fails open in exactly the environment this project is developed in (Claude Code sandboxes set `HTTPS_PROXY` to loopback), as well as on any corporate or proxied workstation.
- **Blast radius today:** zero. Across the full suite plus all legacy harnesses, the logging proxy recorded no CONNECT, and GitHub-hosted runners set no proxy.
- **Risk:** the next regression that escapes `FakeProviders` would silently hit adsb.fi, adsb.lol or adsbdb. Those services are rate-limited, and the calls are compliance-relevant (`COMPLIANCE.md`). The test would pass or fail depending on live data, instead of failing loudly.

**Fix (minimal):** strip proxy configuration everywhere the guard is installed, and add a self-test.
```python
# skypane_test_support.py
PROXY_ENV_VARS = ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY",
                  "http_proxy", "https_proxy", "all_proxy")

def strip_proxy_env(env=None):
    env = os.environ if env is None else env
    for var in PROXY_ENV_VARS:
        env.pop(var, None)
    return env

def install_child_network_guard():
    strip_proxy_env()                      # before any client reads it
    ...

def child_env(base=None, *, fake_providers=None, state_dir=None):
    env = strip_proxy_env(dict(base if base is not None else os.environ))
    ...
```
```python
# conftest.py - module import time, so every xdist worker is covered too
skypane_test_support.strip_proxy_env()
```
```python
# test_test_support.py
def test_loopback_proxy_cannot_tunnel_out(monkeypatch):
    monkeypatch.setenv("HTTPS_PROXY", "http://127.0.0.1:9")  # would tunnel if honoured
    with pytest.raises(NetworkAccessBlocked):
        requests.get("https://example.com", timeout=2)
```
(With the vars stripped at conftest import, the test must set the variable itself, then assert that the request is still blocked. The simplest belt-and-braces option is to also stop `requests` from reading proxy settings in the in-process fixture: `monkeypatch.setattr(requests.sessions.Session, "trust_env", False)`.)

### CR-02: The stale-deploy guard skips valid deploys when `main` moved to a commit that will never deploy itself, and the job still goes green

**File:** `.github/workflows/ci.yml:163-176` (interacting with `paths-ignore` at `51-64`)

**Issue:** The guard deploys only when `github.sha` is exactly the tip of `main`. But the tip can move to commits that never produce a deploy run of their own:
- **Docs-only pushes** (`**/*.md`, `.planning/**`, `.claude/**`, `LICENSE`): `paths-ignore` suppresses the whole workflow, so no test or deploy run exists for them. Under the GSD workflow, doc-only commits to `main` are routine.
- **Pushes whose `test` job fails:** `deploy` `needs: test`, so no deploy runs.

Walk-through:
1. Code commit X passes its tests, and its deploy waits for reviewer approval.
2. Someone pushes a README or `.planning` fix D.
3. The reviewer approves X.
4. `ls-remote` returns D, and D ≠ X, so every step is skipped with a `::notice::`. The job reports **success**.

Production never receives X, and nothing will deploy it until some later non-docs push goes green. The reviewer approved a deploy, saw green, and nothing shipped: a silent failure on the production path.

The guard's real intent is "a newer deployable commit exists". "Tip ≠ me" is only an approximation of that.

**Fix:** Treat the run as stale only when the newer tip changes something that actually ships:
```yaml
      - name: Check out repository
        uses: actions/checkout@... # v7.0.1
        with:
          fetch-depth: 0
      - name: Skip if a newer deployable commit exists on main
        id: fresh
        run: |
          set -euo pipefail
          latest="$(git ls-remote origin refs/heads/main | cut -f1)"
          [[ "${latest}" =~ ^[0-9a-f]{40}$ ]] || { echo "::error::could not read main tip"; exit 1; }
          if [ "${latest}" = "${GITHUB_SHA}" ]; then
            echo "stale=false" >> "$GITHUB_OUTPUT"; exit 0
          fi
          git fetch --quiet origin "${latest}"
          # Identical shipped tree -> deploying this sha == deploying tip.
          if git diff --quiet "${GITHUB_SHA}" "${latest}" -- \
               server stub-server companion adsb-test/runway3.json deploy; then
            echo "stale=false" >> "$GITHUB_OUTPUT"
          else
            echo "stale=true" >> "$GITHUB_OUTPUT"
            echo "::notice::Skipping deploy: ${latest} changes shipped files and will deploy itself."
          fi
```
The "newer tip failed its tests" case is still skipped by this version. That is acceptable, because production stays on the last approved code, but record it in the header comment.

## Warnings

### WR-01: A failing `git ls-remote` is silently treated as "stale", so the deploy is skipped and the job goes green

**File:** `.github/workflows/ci.yml:170-176`

**Issue:** GitHub's default `run` shell is `bash -e {0}` **without** `pipefail`. If `git ls-remote` fails (network blip, auth, rate limit), `cut` still exits 0 and `latest=""`. Since `"" != sha`, `stale=true` is set, every deploy step is skipped, and the run reports success. A broken deploy is indistinguishable from an intentional skip.

**Fix:** Add `set -o pipefail`, and validate `latest` as a 40-hex SHA before comparing it; exit 1 otherwise (see the snippet in CR-02). An error must fail the job, never skip it.

### WR-02: Subprocess coverage is lost for every SIGTERM-stopped server, so the 88% floor was measured under a broken premise

**File:** `pyproject.toml:95-117`, `154`

**Issue:** `patch = ["subprocess"]` starts coverage inside each child, but coverage.py only writes its data file at normal exit unless `sigterm = true` is set (the default is False; see `coverage/control.py:655`). Every long-lived child this suite starts is stopped with `proc.terminate()`, which sends SIGTERM:
- `stub-server/test_poll_cycle.py:293`;
- `server/test_pipeline_e2e.py:176`;
- the companion `Harness.stop()`;
- the legacy shim's `killpg(SIGKILL)` (always lost).

Those children therefore save nothing. Measured on `stub-server/test_poll_cycle.py` alone: **`byos_server.py` 50% as shipped vs 91% with `sigterm = true`**.

The header comment's claim that `byos_server.py` and `app.py` are "now measured in-scope" is largely untrue. The 88.11% baseline mostly reflects in-process imports, and the gate cannot catch regressions in request-handling code that is only reached over HTTP.

**Fix:**
```toml
[tool.coverage.run]
parallel = true
patch = ["subprocess"]
sigterm = true
```
Then re-measure on 3.14 as non-root and ratchet `fail_under` up to the new total, updating the derivation comment. (Where possible, also have the harness `stop()` methods send SIGINT, or wait for a clean shutdown.)

### WR-03: `FakeProviders.from_file()` checks `requests.exceptions` but reads the class from `requests`, so most requests exceptions crash the child at startup

**File:** `test-support/skypane_test_support.py:282-292`

**Issue:** The allow-list check uses `hasattr(requests.exceptions, error_name)`, but the class is then fetched with `getattr(requests, error_name)`. The top-level `requests` package re-exports only a handful of exceptions. Verified:
- `fail("adsbfi", requests.exceptions.SSLError(...))` → `AttributeError: module 'requests' has no attribute 'SSLError'`;
- `ProxyError` and `ChunkedEncodingError` fail the same way;
- `ReadTimeout` works only because it happens to be re-exported.

Because `sitecustomize.py` runs this at interpreter start, the child crashes before any test logic runs, with a confusing error. The allow-list is also looser than intended: `hasattr(requests.exceptions, "BaseHTTPError")` is True (an imported urllib3 name).

**Fix:**
```python
exc_cls = getattr(requests.exceptions, error_name, None)
if not (isinstance(exc_cls, type) and issubclass(exc_cls, requests.exceptions.RequestException)):
    raise ValueError("refusing to reconstruct %r" % (error_name,))
fake.fail(name, exc_cls(entry["message"]))
```
Also make `to_file()` reject (raise) a non-`RequestException` failure up front. Today it serialises one, and the child then refuses to start.

### WR-04: Browser harnesses pass vacuously through the shim when Chromium cannot launch

**Files:** `companion/test_legacy_harness_shim.py:279-287`; `companion/test_browser_ux.py:1211-1228` (same pattern in `test_browser_ux_health_drawings.py:~80-95` and `test_browser_ux_quiet_wake.py:~80-95`)

**Issue:** The shim asserts only `returncode == 0`. Each browser harness wraps `p.chromium.launch()` in `except Exception:` → print `SKIP ...` → `return 0`. The following all turn about 90+ browser UX checks per file into a green "passed" pytest result, with nothing in CI output beyond one buried stdout line:
- a missing headless shell (for example, a restored cache that does not match `--only-shell`);
- missing OS deps;
- a sandbox or permissions problem;
- any other launch error.

This phase changed the install step (`--only-shell` plus the new cache), which is exactly the kind of change that can trip this silently.

**Fix:** In the shim, map a harness-reported skip to a pytest skip, and let CI make that skip fatal:
```python
if returncode == 0 and re.search(r"(?m)^SKIP ", output):
    if os.environ.get("SKYPANE_REQUIRE_BROWSER") == "1":
        pytest.fail("%s skipped under SKYPANE_REQUIRE_BROWSER=1:\n%s" % (harness, last_lines))
    pytest.skip("%s: %s" % (harness, next(l for l in output.splitlines() if l.startswith("SKIP "))))
```
Also set `SKYPANE_REQUIRE_BROWSER: "1"` on the CI test step.

### WR-05: `byos_server_factory` leaks the server subprocess when startup fails

**File:** `server/test_pipeline_e2e.py:150-170`, `197-205`

**Issue:** `harness.start()` assigns `self.proc = Popen(...)` and then can raise, either on the "did not start listening within N s" timeout or on an early exit. Because `harnesses.append(harness)` only runs **after** `start()` returns, a failed start is never added to the teardown list. In the timeout case the process is still alive, so it is orphaned, holding its port and its `tmp_path` state.

The fixture docstring promises the opposite ("guarantees it is stopped at teardown, even if the test fails partway through starting a later one"). Also, if one `stop()` raises (second `wait(timeout=5)`), the remaining harnesses are not stopped.

**Fix:**
```python
harness = BYOSHarness(image_path, state_dir)
harnesses.append(harness)        # register BEFORE start
harness.start()
...
for harness in harnesses:
    try:
        harness.stop()
    except Exception:
        if harness.proc is not None:
            harness.proc.kill()
```

### WR-06: `paths-ignore` skips CI for Markdown that the test suite actually reads

**File:** `.github/workflows/ci.yml:51-64`

**Issue:** The header says ignoring `**/*.md` and `.planning/**` is "safe". But legacy harnesses run by this workflow open and assert on files under those globs:
- `companion/test_status_pages.py:8401-8404` reads `.planning/phases/06.6.3-.../06.6.3-CONTEXT.md` and asserts on its D-12 wording;
- `companion/test_config_page.py:8595-8598` and `8621-8624` read `20-UI-SPEC.md` and `21-UI-SPEC.md`.

A docs-only edit to those files can break the suite with no CI run. The breakage then surfaces on the next unrelated code push and gets attributed to it. Combined with CR-02, docs-only pushes also block deploys.

**Fix:** Either remove `.planning/**` (and the specific spec/context files) from `paths-ignore`, or add `!`-negations for the files that tests read. Better long term: stop having tests assert on planning prose.

### WR-07: Every subset invocation of `run-all-tests.sh` fails on the coverage gate, including the usage the script itself documents

**File:** `scripts/run-all-tests.sh:25` (usage `scripts/run-all-tests.sh -k dither -- -x`), `61`

**Issue:** The wrapper always passes `--cov`, and pytest-cov applies `fail_under = 88` to whatever ran. Verified: `JOBS=2 ./scripts/run-all-tests.sh server/test_dither.py` gives `6 passed`, then `FAIL Required test coverage of 88.0% not reached. Total coverage: 0.53%`, with **exit 1**. Any contributor following the documented `-k`/path usage sees a red run with all tests passing.

**Fix:** Apply the gate only to full runs. For example, when `$#` > 0, append `--cov-fail-under=0` (or `--no-cov`). Alternatively, document that the wrapper is full-suite only and that subsets should use `pytest` directly.

## Info

### IN-01: The DNS guard opt-out and scope are narrower than documented

**File:** `conftest.py:421-436`

**Issue:**
- **Opt-out:** pytest-socket also opts a test out via the `socket_enabled` fixture, but `_block_non_loopback_dns` checks only the `enable_socket` marker. The docstring says they share the "same marker".
- **Scope:** the fixture is function-scoped, so DNS lookups made during module- or session-scoped fixture setup, or at collection/import time, are not DNS-guarded. `connect()` is still guarded during setup, but not during collection.

**Fix:** Check `"socket_enabled" in request.fixturenames` too. For hard hermeticity, install the resolvers once in `pytest_configure` (session-wide), not per test.

### IN-02: `to_file()` redirects the parent instance's own call log into the child's log

**File:** `test-support/skypane_test_support.py:270-271`

**Issue:** `to_file()` sets `self.calls_log_path` on the parent's instance. Any later in-process `get()` then appends to the same JSONL file the parent uses to observe the child. The two sources become indistinguishable, which could make a "child called adsbfi once" assertion pass or fail for the wrong reason. It is also called twice in `test_fake_providers_cross_process` (explicitly and again inside `child_env`), truncating the log each time.

**Fix:** Compute the log path without mutating `self`, or tag each line with `os.getpid()`.

### IN-03: `_is_allowed_host` allows every IP literal, not just loopback

**File:** `test-support/skypane_test_support.py:60-69`

**Issue:** `ipaddress.ip_address()` succeeding returns True for `8.8.8.8` too. This is harmless, because literals need no DNS and `connect()` is separately restricted. But the name and the `NetworkAccessBlocked` docstring say "non-loopback". A reader could reuse `_is_allowed_host` as a connect check.

**Fix:** Rename it to `_needs_no_dns`, or check `.is_loopback` and document why non-loopback literals are allowed through.

### IN-04: The CI header comment overstates what `test`'s concurrency guarantees for `main`

**File:** `.github/workflows/ci.yml:23-25`, `77-83`

**Issue:** `cancel-in-progress: false` protects only a *running* `test` job. GitHub always cancels an older *pending* member of the same group when a newer one queues, including on `main`. That drops the older commit's deploy as well. The behaviour is fine, but "a push to `main` never does [cancel]" is inaccurate.

**Fix:** Reword the comment.

### IN-05: Legacy harnesses are red when the suite runs as root, and the shim has no `requires_non_root` equivalent

**File:** `companion/test_legacy_harness_shim.py:233-287`

**Issue:** In this (root) review environment, `test_companion_app` reported 318/320: the two read-only-state-dir checks, WR-11, fail because root ignores permission bits. `test_status_pages` reported 316/317. Both map to shim failures. Migrated tests handle this with `@requires_non_root`, but legacy harnesses have no equivalent, so running `./scripts/run-all-tests.sh` in a root container is red. (`test_poll_loop.py:531` also carries over a `hash()`-derived callsign, which is `PYTHONHASHSEED`-dependent. This is pre-existing and harmless today, but non-deterministic.)

**Fix:** Have root-sensitive harness checks self-skip under `os.geteuid() == 0` (the same convention as `requires_non_root`) until Phase 33 migrates them.

---

_Reviewed: 2026-09-23_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
