# Phase 35: Comment purge in English and dead code - Research

**Researched:** 2026-09-24 (orchestrator-inline, proportionate to a mechanical phase; no researcher fan-out)
**Confidence:** HIGH for inventory and pitfalls. The figures below are indicative: they were measured on `72f4088` (Phase 33 at 24/33). Plan 35-01 re-measures the authoritative baseline with the committed tool on the Phase-33-complete `main`.

## Inventory (rough scratch measurement, `72f4088`)

The measurement counts a line as a comment line when it holds a `#`/`//`/`/* */` comment or is part of a Python docstring. The history-ref pattern is broad (plan ids, D-/WR-/CFG-… ids, quick-task ids, `Phase N`).

| Group | Code lines | Comment lines | Ratio | History refs |
|-------|-----------:|--------------:|------:|-------------:|
| companion production (Python + JS + CSS) | 47 611 | 29 871 | 63 % | 3 287 |
| companion tests (41 files) | 54 247 | 14 301 | 26 % | 1 820 |
| server production | 14 897 | 8 289 | 56 % | 917 |
| server tests + fixtures | 15 868 | 3 117 | 20 % | 412 |
| stub-server (prod / tests) | 1 181 / 1 790 | 570 / 388 | 48 % / 22 % | 33 / 12 |
| deploy (prod / tests) | 2 156 / 2 669 | 721 / 265 | 33 % / 10 % | 66 / 28 |
| firmware (all) | 6 448 | 1 798 | 28 % | 60 |
| test-support | 1 865 | 364 | 20 % | 7 |
| .github, pyproject.toml, scripts, adsb-test, hardware, .gitignore | ~6 700 | ~800 | — | ~45 |
| **Total** | 156 219 | 60 528 | 39 % | 6 687 |

Heaviest single files (comment lines / total lines):

| File | Comment lines / total | Share |
|------|-----------------------|------:|
| `companion/static/style.css` | 6 842 / 10 690 (512 795 bytes on disk) | 64 % |
| `companion/pages/config_page.py` | 4 430 / 6 653 | 67 % |
| `companion/pages/health_page.py` | 3 192 / 4 676 | 68 % |
| `companion/layout.py` | 2 726 / 4 169 | 65 % |
| `companion/app.py` | 2 140 / 3 745 | 57 % |
| `companion/pages/airlines_page.py` | 1 652 / 2 504 | 66 % |
| `server/plane/render.py` | 1 528 / 2 933 | 52 % |
| `server/plane/calendar_rules.py` | 1 373 / 2 222 | 62 % |
| `companion/pages/history_page.py` | 1 116 / 1 822 | 61 % |
| `server/poll_loop.py` | 1 128 / 1 987 | 57 % |

JS: 17 files, 3 738 comment lines. `freshness.js` has 645, `value-controls.js` 608, `dirty-state.js` 472, `panel-lookup.js` 349.

Companion test comment lines by harness family:

| Family | Comment lines |
|--------|--------------:|
| browser_ux* | 5 179 |
| status_pages* | 2 914 |
| config_page* | 2 543 |
| companion_app* | 1 991 |
| view_pages* | 1 159 |
| everything else | ~500 |

## Dead-code candidates (HYG-05), status on `72f4088`

| Candidate | Production callers | Test callers | Note |
|-----------|--------------------|--------------|------|
| `health_page.health_severity` (def ~:2364) | none (only mentioned in comments in `app.py:1618-1627`, `pages/__init__.py:66-68`) | check at execution | `app.py` now reads `health_state["severity"]` |
| `health_page.anomaly_active` (def ~:2390) | none | `test_status_pages*.py`, `test_suite_guards.py` (mention) | TST-13 root-safety notes reference it |
| `draw.usable_pairs` (:294) | none | `companion/test_companion_app_02.py:1245-1277` | the test exists only for the dead function |
| `draw.label_grid` (:692) | none | none | also named in `.claude/skills/.../data-density.md` (out of scope, but note it) |
| comments about removed features (`app.py` ~3450/3514, `auth.py:63-70` the display-mode cookie) | — | — | delete the comment; keep any *why* still true |

Test callers live in several test files (`test_companion_app_02.py`, `test_status_pages.py`, `_01`, `_04`). So HYG-05 must run as a single plan that owns both the defs and those tests. It cannot run inside a parallel wave where another plan owns the same files. Re-run `git grep -nw <name>` at execution time, because Phase 33 may already have deleted test callers.

## Existing patterns to reuse

- `scripts/check-attribution.sh`: a CI guard run from `ci.yml`.
- `companion/test_suite_guards.py` (Phase 33, G1..G6): an AST-based meta-test that forbids tests from reading source or `__doc__`. This is the TST-12 precondition evidence for gate G-33.
- `testpaths` includes `test-support`, so the guard's tests go there and CI picks them up with no config change.
- The `ci.yml` lint job already runs `ruff check .` and `shellcheck` on `deploy/**/*.sh`. The new guard step goes next to them.
- `node` (22) and `cpp`/`gcc` are available locally. The CI Ubuntu runners have `cpp` and `node`, but the tool must not require node: the JS/CSS tokenizer is stdlib Python. `node --check file.js` is an optional extra local sanity check.

## Guard pattern research (HYG-06)

Whole-tree hit counts, excluding `.planning`, `.claude` and `*.md`:

| Pattern | Hits | Verdict |
|---------|-----:|---------|
| `\bD-\d{1,3}\b` | 2 882 | Include. Also the forms `D-A\d` and `D-\d{2}-\d{2}` (firmware uses `D-34-03`). |
| `\d{2}(\.\d+)*-\d{2}[a-z]?-(PLAN\|SUMMARY)` | 2 379 | Include, plus the `-CONTEXT/-RESEARCH/-REVIEW/-VERIFICATION/-UI-SPEC/-PATTERNS/-VALIDATION/-UAT` artifact names and `NN-REVIEW.md` forms. |
| `\b\d{6}-[a-z0-9]{3}\b` (quick-task ids) | 665 | Include. |
| `\bPhase \d+` | 456 | Include (capital P plus a number). |
| `\bT-\d{2}-\d{2}` (threat ids) | 380 | Include. |
| `\b(WR\|CR\|IN)-\d+\b` (review ids) | 131 | Include. |
| `\.planning/` | 40 | Include. |
| bare `NN-NN` (a plan id without a suffix) | 1 148 | **Do not include as-is.** It collides with ISO dates (`2026-09-23`), runway names (`runway-02-20.png`, `06-24`) and numeric ranges. Include it only in context (`\bNN(\.N)*-NN\b` followed by ` Task`, or preceded by `plan `/`Plan `), or leave it to the manual purge. |

Requirement-style ids `[A-Z]{2,6}-\d{1,3}`, by prefix:

| Prefix | Count |
|--------|------:|
| CFG | 1 367 |
| WR | 91 |
| UXA | 83 |
| SEC | 81 |
| UIR | 74 |
| TST | 63 |
| CR | 40 |
| FW | 26 |
| SEED | 20 |
| MR | 20 |
| UAT | 11 |
| PLANE | 9 |
| CP, DP | small |

Legitimate collisions: `SHA-256`, `UTF-8`, `HTTP-…`, `VPS-1`. So the guard uses an **explicit prefix allowlist** taken from REQUIREMENTS.md (current and milestone archives): CFG TST FW INT CMP SEC DEVICE HYG EFF ARC RER PLANE DOC VIS MSG, plus the historic UXA UIR MR CP DP SEED UAT QT and the review prefixes WR CR IN BL. Never use a generic `[A-Z]+-\d+`.

Scope of the scan: comments and docstrings only (never string literals or identifiers), in every tracked file with a known comment syntax. Excluded: `.planning/`, `.claude/`, `*.md`, `LICENSE`, `NOTICE`, `firmware/LICENSE`, `firmware/NOTICE`, and binary/data files (`*.png`, `*.json`, `*.csv`, fonts, `server/fixtures/**` data).

## Pitfalls

1. **`# CONFIG_X is not set` in `sdkconfig*` is configuration.** Stripping it changes the build. The same-code check and the ratio tool treat these lines as code.
2. **`__doc__` at runtime:** `companion/app.py:3695`, `deploy/backup/backup_gate.py:47`, `deploy/backup/skypane_backup.py:78` and `server/plane/illustrations.py:1135` feed argparse `--help`. Trimming history from them is allowed, but their module docstring is compared as code unless listed in `--allow`.
3. **A docstring as a function's only body:** deleting it is a syntax error. Shorten it, never delete it.
4. **Strings that look like comments:** `#` inside Python strings, `//` in JS URLs and regex literals, `/*` inside CSS strings or `url()`. The tokenizers must be string-aware. Python uses `tokenize`. The JS tokenizer needs a regex-literal heuristic (a `/` after an operator, `(`, `,`, `=`, `:`, `[`, `!`, `&`, `|`, `?`, `{`, `}`, `;`, `return`, or at line start).
5. **`firmware/tests/check_log_contract.sh` greps source text** (`grep 'fail_step_out ='`, `fail_and_sleep("…")`, `VENDOR.md` rows). Before editing, check that no grepped line is a comment. Run the script in the firmware wave.
6. **HTML comments inside Python template strings** are shipped markup (string literals), not source comments. Don't touch them here. The guard does not scan string literals.
7. **The Phase 32/33 ledgers reference test node ids.** Renaming tests would break them, so test names are unchanged.
8. **`ruff` select is `E4,E7,E9,F`.** Removing comments cannot trigger these, but an emptied block can (E9 syntax). The AST same-code check catches that first.
9. **A comment that justifies a pragma** (`# noqa: E402  # sys.path set above`): keep the pragma, and trim the justification to the *why*.
10. **Concurrent phases touch the same files.** Phase 36 (server, stub-server, byos), Phase 37-11 (byos) and Phase 34-11 (firmware) are all on these files. Merge `main` before each group, and run the same-code check against the merge base, not a stale ref.

## Validation Architecture

Proof per changed file, mechanical and cheap:

1. **same-code** (new subcommand of the guard tool), comparing `git show BASE:file` against the working tree:
   - `.py`: `ast.dump()` equal after removing every docstring node. A module that reads `__doc__` keeps its module docstring in the comparison.
   - `.c`/`.h`: `cpp -fpreprocessed -P -w` output equal after whitespace normalisation.
   - `.js`/`.css`: the token list equal after dropping comment tokens and whitespace.
   - `#`-comment formats (`.sh`, `.service`, `.timer`, `Caddyfile`, `*.env.example`, `.yml`, `.toml`, `CMakeLists.txt`, `Kconfig*`, `sdkconfig*`, `.gitignore`): the list of non-comment lines equal. In sdkconfig, `# CONFIG_… is not set` counts as code. In Kconfig, `help` text may change (it is documentation) but symbol lines may not.
   - For every language, the pragma multiset and the SPDX/copyright lines are equal.
   - Exit non-zero listing each differing file, except the paths passed with `--allow` (HYG-05 and `__doc__`).
2. **ratio**: per-file TSV (path, lines, comment lines, ratio, history hits, bytes). `35-COMMENT-RATIO.md` is generated from the before TSV and the after TSV.
3. **check**: the HYG-06 guard over tracked files. It honours `scripts/comment-history-pending.txt` until the last plan deletes it.
4. The full suite, ruff, shellcheck, and for firmware the host tests, the log contract, the production config check and the build.

Commands:

| Purpose | Command |
|---------|---------|
| Quick run | `python3 scripts/check_comment_history.py check && server/.venv/bin/python -m pytest test-support/test_check_comment_history.py -q` |
| Per group | `python3 scripts/check_comment_history.py same-code --base "$(git merge-base HEAD origin/main)" [--allow …]`, then `./scripts/run-all-tests.sh`, then `server/.venv/bin/ruff check .` |
| Firmware | `./firmware/tests/run_host_tests.sh && sh firmware/tests/check_log_contract.sh && sh firmware/tests/check_production_config.sh static && ./firmware/build.sh` (the build needs the IDF container. If Docker is unavailable locally, CI `firmware.yml` is the gate) |
