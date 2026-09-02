---
phase: 05-low-battery-indicator
plan: 260902-fwx
type: execute
mode: quick
wave: 1
depends_on: []
files_modified:
  - hardware/logtools.py
  - hardware/fixtures/battery-history-db.jsonl
  - hardware/BATTERY-RUN.md
  - .planning/phases/05-low-battery-indicator/05-01-PLAN.md
autonomous: true
requirements: [DEVICE-05]

must_haves:
  truths:
    - "The DEVICE-05 discharge run's PRIMARY observation channel is `history.db`'s `device_health` table, which Phase 6's already-shipped `skypane-poll.timer` -> `poll_loop.run_once()` -> `history_db.ingest_caddy_battery_log()` pipeline has been filling every 30 seconds in production since plan 06-11 — from Caddy's durable rolled JSON access log, with keep-forever retention (D-13)."
    - "Not one line of the analysis changes. The new subcommand emits the identical bracketed `[ISO-8601] ... X-Battery-Mv: N` shape `check-battery` already parses, so every coverage, gap, millivolt-drop, depletion and boot-reconciliation gate is reused byte-for-byte and the three original battery fixtures earn exactly their original verdicts."
    - "Unlike the journald channel, this one cannot lose the record: `device_health` is never pruned, and `record_device_health()`'s `INSERT OR IGNORE` against `UNIQUE(ts, battery_mv)` makes a re-read of an overlapping range idempotent by construction. Regenerating the whole window is therefore always safe, and no rotation-triggered repair path exists or is needed."
    - "The daily check-in stops being load-bearing. It is downgraded from required-or-you-lose-the-record to optional-for-visibility, because nothing between check-ins is at risk any more. A run with zero check-ins still yields a complete, gateable record."
    - "Every part of the protocol that is about measurement validity survives byte-for-byte: the 0.95 coverage floor, the 3-interval gap ceiling, the 100 mV drop floor, the 3400 mV depletion cutoff, the 21-day ceiling, and the rated-capacity-divided-by-counted-cycles formula — proven by comparing the whole pre-registered section against its committed self, not by review."
    - "`SKYPANE_SLEEP_S` is untouched and its reasoning is untouched. It is the device's own measured wake cadence — the subject of the measurement and the divisor every gate uses — and has nothing to do with which channel observes it."
    - "The journald bridge is not removed. `from-journal`, its fixture and its selftest case all survive intact as the documented fallback for the case where `history.db` is unreachable."
  artifacts:
    - path: "hardware/logtools.py"
      provides: "from-history-db subcommand: device_health JSON-Lines rows to the bracketed timestamp format check-battery parses, plus the canonical read-only SSH query it consumes"
      exports: ["from-history-db"]
    - path: "hardware/fixtures/battery-history-db.jsonl"
      provides: "battery-good.log's telemetry re-rendered as realistic device_health JSON-Lines rows, plus non-row noise and a null-battery row the converter must drop"
      contains: "battery_mv"
    - path: "hardware/BATTERY-RUN.md"
      provides: "The pre-registered protocol, amended a second time to the history.db observation channel, with the first amendment left byte-for-byte intact"
      contains: "## Protocol Amendment"
    - path: ".planning/phases/05-low-battery-indicator/05-01-PLAN.md"
      provides: "Tasks 2 and 3 re-scoped to the history.db channel with the check-in downgraded to optional; every physical step, threshold, resume-signal and gate attribute untouched"
      contains: "from-history-db"
  key_links:
    - from: "hardware/logtools.py from-history-db"
      to: "hardware/logtools.py parse_timestamp"
      via: "converted lines must satisfy the existing bracketed-timestamp parser, verified by calling it before emitting"
      pattern: "TS_RE"
    - from: "hardware/logtools.py from-history-db"
      to: "server/history_db.py record_device_health"
      via: "the converter renders exactly the five columns the production writer inserts, proven by a round-trip through the real schema rather than against a hand-written fixture alone"
      pattern: "device_health"
    - from: "hardware/BATTERY-RUN.md ### Observation channel"
      to: "server/history_db.py D-13 keep-forever retention"
      via: "the claim that a check-in is no longer needed for data preservation rests on device_health never being pruned"
      pattern: "keep-forever"
---

<objective>
Quick task 260827-vq3 amended `hardware/BATTERY-RUN.md`'s pre-registered protocol once, moving the DEVICE-05 discharge run's observation channel off a laptop-run stub and onto journald-tailing the production `skypane-byos.service`. That removed the Mac-availability constraint and was the right call at the time.

It is no longer the best available channel, and the better one was already running when that amendment was written. Phase 6's plan 06-11 shipped `server/history_db.py`'s `device_health` table, fed every 30 seconds by `skypane-poll.timer` -> `poll_loop.run_once()` -> `history_db.ingest_caddy_battery_log()` (`server/history_db.py:551` call path), which tails Caddy's durable rolled JSON access log (`SKYPANE_CADDY_ACCESS_LOG`, `deploy/Caddyfile`) and inserts every `X-Battery-Mv` reading through `record_device_health()` (`server/history_db.py:201`). It is strictly better than journald for this measurement on three counts, and every one of them is a property journald does not have:

**Retention.** `device_health` is explicitly keep-forever (D-13, `server/history_db.py:18`) — it is never pruned. journald has a bounded window, and the first amendment had to build a whole rotation-repair path around that fact: regenerate rather than append, commit after every check-in so git holds the earlier content, compare the regenerated first line against the recorded first poll, and concatenate the recovered log paths if they ever diverge. None of that machinery is needed here. That is not a simplification of the protocol; it is the removal of a mitigation whose threat no longer exists.

**Idempotence by construction.** `record_device_health()` inserts with `INSERT OR IGNORE` against a `UNIQUE(ts, battery_mv)` constraint, so a re-read of an overlapping range cannot double-count. The first amendment's duplicated-poll hazard — which inflated the observed count and therefore coverage, the one number a reader would trust least to be wrong — is structurally absent.

**Continuity.** Ingestion runs on the server's own 30-second cadence, independent of the device's sleep interval, and it is already running in production today with no setup step of any kind.

The consequence that actually changes the developer's life is the third one combined with the first: the daily check-in stops being load-bearing. Under the journald channel a missed check-in risked losing the earliest part of the record to rotation. Under this channel nothing between check-ins is at risk, so the check-in is downgraded to what it should always have been — optional, useful for progress visibility and for catching a stalled run early, never for data preservation.

The bridge itself is small, and deliberately so: `device_health` rows carry a `ts` and a `battery_mv` alongside the three other allowlisted telemetry headers, and rendering them back into the exact `[ISO-8601]   telemetry: ... X-Battery-Mv=N` line the vendored server prints means `check-battery`'s parser, its four thresholds, its gap arithmetic, its depletion gate and its boot reconciliation are all reused with zero edits. Unlike the first amendment, this one needs no timezone-awareness fixes either — 260827-vq3 already made `--status` and the mixed-awareness rejection offset-safe, and `device_health` timestamps carry an offset for the same reason converted journal ones do.

Nothing about measurement validity moves. The four thresholds, the 21-day ceiling, the D-07 division and every physical pack-handling step stay exactly as pre-registered, and this plan proves that mechanically by diffing the pre-registered section against its own committed self rather than by asserting it. `SKYPANE_SLEEP_S` also stays exactly as it is: it is the device's own wake cadence, the subject of the measurement and the divisor every gate uses, and it has nothing whatever to do with which channel does the observing.

Purpose: give DEVICE-05 an observation channel that cannot lose the record, and stop the daily check-in from pretending to be a safety mechanism.
Output: a `from-history-db` bridge proven both against a committed fixture and by a round-trip through the real `device_health` schema, a second dated amendment to the pre-registered protocol, and 05-01's two hardware tasks re-scoped to the channel that is already running.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/STATE.md
@hardware/logtools.py
@hardware/BATTERY-RUN.md
@.planning/phases/05-low-battery-indicator/05-01-PLAN.md
@.planning/quick/260827-vq3-adapt-phase-5-s-battery-discharge-run-pr/260827-vq3-PLAN.md
@.planning/quick/260827-vq3-adapt-phase-5-s-battery-discharge-run-pr/260827-vq3-SUMMARY.md
@server/history_db.py
@deploy/skypane.env.example
@deploy/README.md
</context>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Bridge history.db's device_health rows into the format check-battery already parses, and prove it twice — against a committed fixture and through the real schema</name>
  <files>hardware/logtools.py, hardware/fixtures/battery-history-db.jsonl</files>
  <read_first>
    - `hardware/logtools.py` in full. Specifically: `TS_RE` and `parse_timestamp()` (line 98, 143 — the bracketed-timestamp contract the output must satisfy); `JOURNAL_RE` (line 109) and `normalize_journal_timestamp()` (line 153 — reused verbatim by this task, see below); `cmd_from_journal()` (line 589 — the exact house shape this new subcommand mirrors: iterate paths-or-stdin, drop unmatched lines, validate before emitting, one stderr summary); `BATTERY_MV_RE` (line 127) and `load_battery_polls()` (line 366), which must not change in what they match; `_telemetry_messages()` (line 712) and `cmd_selftest()` (line 731 — the case list and the battery-journal block this task extends); `build_parser()` (line 814); and the six-module standard-library allowlist stated in the module docstring (line 56).
    - `hardware/fixtures/battery-good.log` — the exact byte shape of an accepted battery fixture: a bracketed naive timestamp, then two leading spaces, then `telemetry:` and the four headers in the order `X-Fw-Version`, `X-Boot-Reason`, `X-Rssi`, `X-Battery-Mv`. 31 lines, hourly, 4150 mV falling to 3150 mV.
    - `hardware/fixtures/battery-journal.log` — the precedent this fixture mirrors: real upstream output re-rendered by hand, with non-telemetry noise interleaved so the drop path is exercised rather than assumed.
    - `server/history_db.py` — `init_schema()`'s `device_health` table (line 123: columns `id`, `ts`, `battery_mv`, `fw_version`, `boot_reason`, `rssi`, and the `UNIQUE(ts, battery_mv)` constraint at line 132); `connect()`'s WAL + `busy_timeout=5000` pragmas (line 146) and the Pitfall-9 concurrency note at line 21; `record_device_health()` (line 201); `_TELEMETRY_HEADER_ALLOWLIST` (line 79) for the exact header names and their order; `tail_caddy_battery_log()`'s `ts` handling (line 351) — a string `ts` is used as-is, a float/int epoch becomes `datetime.fromtimestamp(ts, tz=utc).isoformat(timespec='seconds')` (so `+00:00`), and an absent one falls back to `utc_now_iso()`; and the D-13 keep-forever retention note at line 18. **Read this file only. Do not modify it** — this task is an external consumer of `history.db`, not a participant in how data gets into it.
    - `deploy/skypane.env.example` — `SKYPANE_STATE_DIR=/opt/skypane/state` (line 35) and `SKYPANE_CADDY_ACCESS_LOG` (line 71), which together fix the production path `/opt/skypane/state/history.db`.
  </read_first>
  <behavior>
    - Given a JSON-Lines row carrying `ts`, `battery_mv`, `fw_version`, `boot_reason` and `rssi`, the emitted line is accepted by the existing `parse_timestamp()` and its message is byte-identical (after stripping) to the corresponding message in `battery-good.log`.
    - Given a row whose `ts` ends in `Z`, the emitted timestamp carries an explicit `+00:00` offset and parses on Python releases before 3.11.
    - Given a row whose `battery_mv` is null, nothing is emitted and the dropped count increases by one — a row with no reading must never become a phantom poll.
    - Given a line that is not JSON at all, or is JSON but not an object, or is an object with no `ts`, nothing is emitted and the dropped count increases by one.
    - Given a row carrying extra keys the query did not ask for (for example `id`), those keys are ignored rather than rendered into the message.
    - Given the converted output of `battery-history-db.jsonl`, `check-battery` with `--interval-s 3600 --min-days 1 --capacity-mah 3000 --expect-depleted` exits 0 — the same verdict the same content already earns as `battery-good.log`.
    - Given rows written by the real `record_device_health()` into a real `init_schema()` database and read back through the documented read-only query, the converted output equals `battery-good.log`'s messages — so the committed fixture is proven faithful to what production actually writes, not merely internally consistent.
    - Given the converted output concatenated with `battery-good.log`, the gated run fails with the existing mixed-awareness reason rather than raising.
  </behavior>
  <action>
    Add a `from-history-db` subcommand to `hardware/logtools.py`. Import nothing beyond the six modules the file already allows — `argparse`, `datetime`, `os`, `re`, `subprocess`, `sys` — plus `json`, which is standard library and is the one addition this task legitimately needs to parse its input. Update the AST allowlist in the verify command below and the module docstring's stated allowlist to name seven modules instead of six, and update no other part of that scan: an eighth module, or any module outside the standard library, must fail this task rather than merely be noticed. Do not import `sqlite3` into `logtools.py` — the database lives on the VPS and is read over SSH by the query half, never opened by this file.

    **Input contract: JSON Lines, one `device_health` row per line.** Choose this over a single JSON array deliberately and say why in the code comment: a line-at-a-time parser degrades to "drop that one line and count it" when anything unexpected arrives on the pipe (an SSH banner, a truncated final line, a warning the remote shell emitted), whereas a whole-stdin array parse fails totally on the same input. It also mirrors `cmd_from_journal()`'s existing shape exactly, so the two converters read as siblings.

    Implement `cmd_from_history_db(args)` next to `cmd_from_journal()`, following its structure line for line: an `iter_lines()` helper that reads the positional paths concatenated in the order given, or stdin when none are given; a `dropped` counter; converted lines written to stdout only; and after the last line a single summary written to **stderr** beginning `from-history-db: dropped` and naming the count, so a redirect of stdout into the run log stays clean and a silently truncated conversion still reads as visible.

    For each line: strip it, skip it silently when empty, then `json.loads` it inside a `try` — a `ValueError` drops the line and increments the count. Require the result to be a dict; anything else drops. Require `ts` to be a non-empty string; otherwise drop. Require `battery_mv` to be coercible to `int` inside a `try` — null, absent, or uncoercible drops the line and counts it. That last case is a real production shape, not a hypothetical: `tail_caddy_battery_log()` yields `battery_mv=None` whenever the header is absent or non-integer, and such a row carries no measurement at all.

    Normalize the timestamp by calling the existing `normalize_journal_timestamp()` unchanged. Its two normalizations — a trailing `Z` becomes `+00:00`, and a colon-less four-digit offset gains a colon — are exactly what this channel needs too, and no third normalization is required. Extend only that function's docstring to name both callers rather than journald alone; change nothing about what it computes.

    Render the message as two leading spaces, then `telemetry:`, then one space-separated `Name=value` token for each of `X-Fw-Version`, `X-Boot-Reason`, `X-Rssi` and `X-Battery-Mv` in that exact order — the order of `_TELEMETRY_HEADER_ALLOWLIST` in `server/history_db.py`, which is also the order `battery-good.log` already carries. Map them from the row's `fw_version`, `boot_reason`, `rssi` and `battery_mv` keys respectively. Omit a token entirely when its value is `None` or the empty string, rather than rendering an empty one. Ignore every key not in that map, so a `SELECT *` that also returns `id` produces the same message a five-column select does. The two leading spaces are not cosmetic: they are what `stub-server/byos_server.py`'s `print("  telemetry:", ...)` produces and what `battery-good.log` records, and reproducing them is what makes the message-equality assertion in the verify meaningful.

    Emit an opening bracket, the normalized timestamp, a closing bracket, one space, then the rendered message. Before emitting, call the existing `parse_timestamp()` on the assembled line and drop it if that returns None — the durable record must never contain a line this script itself cannot vouch for.

    Write a module-level comment block above the subcommand recording the two things a future reader most needs and cannot infer from the code:

    First, **the canonical remote query**, which is the other half of this pipeline and lives on the VPS rather than in this file. It opens `/opt/skypane/state/history.db` through Python's standard-library `sqlite3` module — not the `sqlite3` CLI binary, which is not assumed to be installed on the VPS — as `sqlite3.connect('file:<path>?mode=ro', uri=True)`, sets `PRAGMA busy_timeout=5000` to match the discipline `history_db.connect()` uses for its own connections, sets `row_factory = sqlite3.Row`, and iterates `SELECT ts, battery_mv, fw_version, boot_reason, rssi FROM device_health WHERE ts >= ? ORDER BY ts` printing `json.dumps(dict(row))` per row. State the reasoning for the read-only URI: the 30-second ingest oneshot is writing to this database continuously, and a read-only connection cannot create, modify or recover its WAL, so an external reader cannot corrupt the store or lock out the writer. The `busy_timeout` is there so a read that lands mid-commit waits briefly instead of raising "database is locked".

    Second, **why regenerating the whole window is unconditionally safe here.** `device_health` has keep-forever retention (D-13, `server/history_db.py:18`) and is never pruned, and `record_device_health()` inserts with `INSERT OR IGNORE` against `UNIQUE(ts, battery_mv)`, so re-reading an overlapping range cannot double-count. Neither of the two hazards the journald bridge had to defend against — an earliest-entries rotation that shortens the window, and duplicated polls from appending overlapping reads — can occur on this channel. State plainly that no rotation-triggered repair path is needed or provided here, and that this is a genuine simplification relative to `from-journal` rather than an omission.

    Leave `cmd_from_journal()`, `JOURNAL_RE`, `hardware/fixtures/battery-journal.log` and the selftest's battery-journal case fully intact. This subcommand is additive: `from-journal` remains the documented fallback for the case where `history.db` is unreachable, and deleting or weakening it would remove the only channel that still works when the database does not.

    Make exactly one further wording change and no others: `check_timestamps_and_min_polls()`'s no-timestamps failure reason and `load_battery_polls()`'s docstring both enumerate the ways a timestamp can go missing and currently name two conversion paths; add the third. Change no threshold, no computation, and no check's pass/fail condition anywhere — the verify below re-asserts the four `check-battery` defaults literally and re-runs all three original battery fixtures for exactly their original verdicts, so an accidental edit to the analysis fails this task.

    Register the subcommand in `build_parser()` immediately after `from-journal`, with a `logs` positional taking `nargs="*"` and help text matching the `from-journal` entry's shape, and dispatch it in `main()`. Add a `from-history-db` entry to the module docstring's subcommand table between `from-journal` and `check-battery`, naming it as the primary channel and `from-journal` as the fallback, and update the `check-battery` entry so its "stamped locally, or converted from journald" phrasing names all three sources. Update the `selftest` entry to say it now covers eight fixtures rather than seven.

    Write the fixture `hardware/fixtures/battery-history-db.jsonl`. Use the `.jsonl` extension rather than `.log` on purpose: the file is JSON Lines, not a bracketed log, and `05-01-PLAN.md` Task 1's acceptance criteria include a `hardware/fixtures/battery-*.log` glob that expects every matched file to be bracketed line-for-line. Its content is `battery-good.log`'s telemetry re-rendered as the `device_health` rows the real ingest pipeline would have written: the same 31 readings in the same order with the same `X-Fw-Version`, `X-Boot-Reason`, `X-Rssi` and `X-Battery-Mv` values, each as a JSON object with `ts`, `battery_mv`, `fw_version`, `boot_reason` and `rssi` keys. Give the timestamps the same wall-clock instants `battery-good.log` uses with an explicit `+00:00` offset — that is what `tail_caddy_battery_log()` produces from Caddy's epoch `ts` — so the span, the hourly spacing and therefore every gate's arithmetic are identical. Write exactly one of those rows with a `Z` suffix instead of `+00:00`, so the fixture exercises that normalization branch while `battery-journal.log` continues to exercise the colon-less one; the two offsets denote the same zone, so the spacing is unaffected.

    Interleave four lines that must all be dropped and counted, each a shape this pipeline can genuinely see: one blank line; one line that is not JSON at all, shaped like a warning a remote shell might emit onto the pipe; one line that is valid JSON but not an object; and one otherwise-complete row whose `battery_mv` is `null`. That last one is the important one — it proves a reading-less row cannot become a phantom poll and quietly inflate the observed count.

    Extend `cmd_selftest()` with the eighth case. The existing battery-journal block already does exactly the work needed — convert a fixture in a subprocess, write it to a temporary path built from the OS temporary directory and the current process id, run `check-battery` over it with `battery_common` plus `--expect-depleted`, require exit 0, additionally require `_telemetry_messages()` of the converted output to equal `_telemetry_messages()` of `battery-good.log`, and remove the temporary file. Factor that block into a small local helper taking the subcommand name and the fixture filename, then call it twice: once for `from-journal` with `battery-journal.log` and once for `from-history-db` with `battery-history-db.jsonl`. Print each result in the same PASS/FAIL house style, naming `battery-journal` and `battery-history-db` respectively so a grep can see both. Keep `battery_common` at `--interval-s 3600 --min-days 1 --capacity-mah 3000`, matching what `battery-good.log` is already judged under. Selftest still exits zero only when every case matches its required outcome.
  </action>
  <verify>
    <automated>python3 -c "import ast,sys; t=ast.parse(open('hardware/logtools.py').read()); m={(n.module or '').split('.')[0] for n in ast.walk(t) if isinstance(n,ast.ImportFrom)}|{a.name.split('.')[0] for n in ast.walk(t) if isinstance(n,ast.Import) for a in n.names}; extra=m-{'argparse','datetime','json','os','re','subprocess','sys'}; sys.exit('non-stdlib or unexpected imports: %s'%sorted(extra) if extra else 0)" && test -s hardware/fixtures/battery-history-db.jsonl && T=$(mktemp) && python3 hardware/logtools.py from-history-db hardware/fixtures/battery-history-db.jsonl > "$T" 2> "$T.err" && test -s "$T" && [ "$(grep -c '^\[' "$T")" -eq "$(wc -l < "$T" | tr -d ' ')" ] && grep -q 'from-history-db: dropped' "$T.err" && grep -qF ']   telemetry: X-Fw-Version=' "$T" && B="--interval-s 3600 --min-days 1 --capacity-mah 3000" && python3 hardware/logtools.py check-battery "$T" $B --expect-depleted && python3 hardware/logtools.py check-battery "$T" $B --status && python3 -c "
import sys
def msgs(p, only_telemetry):
    out=[]
    for l in open(p, errors='replace'):
        if not l.startswith('['):
            continue
        m=l.split('] ',1)[1].strip()
        if only_telemetry and 'X-Battery-Mv' not in m:
            continue
        out.append(m)
    return out
a=msgs(sys.argv[1], True); b=msgs('hardware/fixtures/battery-good.log', False)
sys.exit('converted telemetry messages differ from battery-good.log (%d vs %d)' % (len(a), len(b)) if a != b else 0)
" "$T" && cat hardware/fixtures/battery-good.log "$T" > "$T.mixed" && ! python3 hardware/logtools.py check-battery "$T.mixed" $B && python3 -c "
import importlib.util, json, os, re, sqlite3, subprocess, sys, tempfile
spec = importlib.util.spec_from_file_location('history_db', 'server/history_db.py')
hdb = importlib.util.module_from_spec(spec); spec.loader.exec_module(hdb)
tmp = tempfile.mkdtemp()
conn = hdb.connect(tmp)
for line in open('hardware/fixtures/battery-good.log'):
    m = re.match(r'^\[([^\]]+)\] (.*)', line.rstrip())
    if not m:
        continue
    f = dict(p.split('=', 1) for p in m.group(2).split() if '=' in p)
    hdb.record_device_health(conn, m.group(1) + '+00:00',
        battery_mv=int(f['X-Battery-Mv']), fw_version=f['X-Fw-Version'],
        boot_reason=f['X-Boot-Reason'], rssi=f['X-Rssi'])
conn.close()
ro = sqlite3.connect('file:' + os.path.join(tmp, 'history.db') + '?mode=ro', uri=True)
ro.execute('PRAGMA busy_timeout=5000')
ro.row_factory = sqlite3.Row
rows = ro.execute('SELECT ts, battery_mv, fw_version, boot_reason, rssi FROM device_health WHERE ts >= ? ORDER BY ts', ('2026-08-01T00:00:00+00:00',)).fetchall()
payload = ''.join(json.dumps(dict(r)) + chr(10) for r in rows)
proc = subprocess.run([sys.executable, 'hardware/logtools.py', 'from-history-db'], input=payload, capture_output=True, text=True)
got = [l.split('] ', 1)[1].strip() for l in proc.stdout.splitlines() if l.startswith('[')]
want = [l.split('] ', 1)[1].strip() for l in open('hardware/fixtures/battery-good.log') if l.startswith('[')]
sys.exit('round-trip through the real device_health schema differs from battery-good.log (%d rows vs %d)' % (len(got), len(want)) if got != want else 0)
" && python3 hardware/logtools.py selftest && python3 hardware/logtools.py selftest | grep -q 'battery-history-db' && python3 hardware/logtools.py selftest | grep -q 'battery-journal' && python3 hardware/logtools.py from-journal hardware/fixtures/battery-journal.log > /dev/null 2>&1 && grep -qF '"--min-coverage", type=float, default=0.95,' hardware/logtools.py && grep -qF '"--max-gap-intervals", type=float, default=3,' hardware/logtools.py && grep -qF '"--min-mv-drop", type=int, default=100,' hardware/logtools.py && grep -qF '"--cutoff-mv", type=int, default=3400,' hardware/logtools.py && python3 hardware/logtools.py check-backoff hardware/fixtures/backoff-good.log --expect-persist --expect-reset && python3 hardware/logtools.py check-battery hardware/fixtures/battery-good.log $B --expect-depleted && ! python3 hardware/logtools.py check-battery hardware/fixtures/battery-gap.log $B --expect-depleted && ! python3 hardware/logtools.py check-battery hardware/fixtures/battery-flat-mv.log $B --expect-depleted && rm -f "$T" "$T.err" "$T.mixed" && echo "history.db bridge proven on a committed fixture and round-tripped through the real device_health schema; every prior gate still holds"</automated>
  </verify>
  <acceptance_criteria>
    - `python3 hardware/logtools.py from-history-db hardware/fixtures/battery-history-db.jsonl` writes only bracketed-timestamp lines to stdout, writes a `from-history-db: dropped` count to stderr, and exits 0.
    - Every telemetry message in that converted output, stripped, equals the corresponding stripped message in `hardware/fixtures/battery-good.log`, in the same order and count — and each emitted line carries the two leading spaces before `telemetry:` that the vendored server prints.
    - The round-trip check passes: rows written through the real `server/history_db.py` `init_schema()` + `record_device_health()` and read back through the documented read-only URI and SQL convert to exactly `battery-good.log`'s messages. This is what proves the committed fixture faithful to production rather than merely self-consistent.
    - `check-battery` over the converted output with `--interval-s 3600 --min-days 1 --capacity-mah 3000 --expect-depleted` exits 0, and the same command with `--status` also exits 0.
    - `check-battery` over `battery-good.log` concatenated with the converted output exits non-zero with the existing mixed-awareness FAIL reason, rather than raising a traceback.
    - `python3 hardware/logtools.py selftest` exits 0 and its output names all eight fixtures, including both `battery-journal` and `battery-history-db`.
    - `from-journal` still converts `battery-journal.log` successfully — the fallback channel is intact, not replaced.
    - The three original battery fixtures earn exactly their original verdicts (`battery-good.log` accepted, `battery-gap.log` and `battery-flat-mv.log` rejected), `check-backoff` still accepts `backoff-good.log` with both expectation flags, and the four `check-battery` defaults still read literally 0.95, 3, 100 and 3400 in `build_parser()`.
    - `hardware/logtools.py` imports nothing outside `argparse`, `datetime`, `json`, `os`, `re`, `subprocess`, `sys` — `json` being the single stdlib addition this task needs, and `sqlite3` deliberately not among them.
    - `server/history_db.py` and `stub-server/byos_server.py` are unmodified (D-03): this task reads `history.db` from the outside and changes nothing about how data gets into it.
  </acceptance_criteria>
  <done>The table that production has been filling every thirty seconds since Phase 6 now speaks the format the checker written in Phase 1 already reads, and that is proven twice — once against a fixture a human wrote, and once against rows the production writer itself produced.</done>
</task>

<task type="auto">
  <name>Task 2: Amend the pre-registered protocol a second time, and prove mechanically that nothing about validity moved</name>
  <files>hardware/BATTERY-RUN.md</files>
  <read_first>
    - `hardware/BATTERY-RUN.md` in full — all ten existing headings. In particular: the `**Server sleep value:**` paragraph (lines 24-40), the thresholds table (lines 45-50), the 21-day ceiling, the D-07 division, the both-outcomes paragraph, the `**Physical preconditions this amendment does not touch.**` paragraph (lines 68-76), the `### Observation channel` subsection (lines 78-106) and the existing `## Protocol Amendment` section (lines 108-126). Everything from `## Run Protocol (pre-registered)` down to `### Observation channel` must survive this edit byte-for-byte, and so must the whole of the existing amendment; the verify below asserts both against their committed selves.
    - `server/history_db.py` lines 14-25 (the D-13 keep-forever retention note and the Pitfall-9 WAL/busy_timeout concurrency note), line 123-135 (`device_health` schema and its `UNIQUE(ts, battery_mv)` constraint), line 201 (`record_device_health()`'s `INSERT OR IGNORE`), and lines 372-406 (`ingest_caddy_battery_log()`).
    - `deploy/skypane.env.example` — `SKYPANE_SLEEP_S` (line 29, currently 30), `SKYPANE_STATE_DIR` (line 35), `SKYPANE_CADDY_ACCESS_LOG` (line 71).
    - `deploy/README.md` `## Reading logs` (line 199) — the `ssh root@<vps-ip> ...` idiom this document's commands follow, and `ssh root@<vps-ip> systemctl is-active skypane-poll.timer` (line 162), the check that confirms the ingest timer is running.
    - `hardware/logtools.py` `from-history-db` as landed by Task 1 — the exact subcommand name, its JSON-Lines stdin contract and the canonical remote query recorded in its comment block, all of which this document quotes.
  </read_first>
  <action>
    Amend `hardware/BATTERY-RUN.md` in three places and nowhere else.

    **First, rewrite the `### Observation channel` subsection.** Everything above it — the D-07 method paragraph, the pack rated capacity, the `**Server sleep value:**` paragraph, the thresholds table, the ceiling, the division, the both-outcomes paragraph and the physical-preconditions paragraph — stays byte-for-byte. Do not retype it, do not reflow it, do not adjust its wording.

    Restructure the subsection into a primary path and a fallback path.

    The primary path is `history.db`'s `device_health` table at `/opt/skypane/state/history.db` on the VPS. Say what fills it and on what cadence: `skypane-poll.timer` runs `poll_loop.run_once()` every 30 seconds, which calls `history_db.ingest_caddy_battery_log()`, which tails Caddy's durable rolled JSON access log (`SKYPANE_CADDY_ACCESS_LOG`, `/opt/skypane/state/caddy-access.log`) and inserts every `X-Battery-Mv` reading via `record_device_health()`. State that this has been running in production since Phase 6's plan 06-11 and that this protocol neither starts it nor configures it — there is no setup step for the observation channel at all.

    Then state the three properties that make it the right channel, each with the concrete mechanism rather than the adjective. Retention: `device_health` is keep-forever by design (D-13, `server/history_db.py:18`) and is never pruned. Idempotence: `record_device_health()` inserts with `INSERT OR IGNORE` against a `UNIQUE(ts, battery_mv)` constraint, so re-reading an overlapping range cannot double-count. Continuity: ingestion runs on the server's own 30-second cadence, independent of whatever sleep interval the device is on.

    Give the record-generation command: the remote half opens the database read-only through Python's standard-library `sqlite3` module (not the `sqlite3` CLI binary, which is not assumed present on the VPS) as `sqlite3.connect('file:/opt/skypane/state/history.db?mode=ro', uri=True)`, sets `PRAGMA busy_timeout=5000`, and prints one JSON object per row from `SELECT ts, battery_mv, fw_version, boot_reason, rssi FROM device_health WHERE ts >= ? ORDER BY ts` bounded by the recorded disconnect time; the local half pipes that into `python3 hardware/logtools.py from-history-db`, redirected over `hardware/logs/battery-run-server.log`. Record two pieces of reasoning a reader cannot recover from the command itself. The read-only URI is there because the 30-second ingest oneshot is writing to this database continuously and an external reader must be incapable of corrupting the store or locking out the writer; the `busy_timeout` matches the discipline `history_db.connect()` already applies to its own connections. And write the command so it survives SSH's two levels of shell parsing — a remote command is joined and re-parsed by the remote shell, so a `python3 -c` one-liner carrying quotes and semicolons breaks in ways that are tedious to debug at the start of a three-week run; feed the query script to `python3 -` on the remote's stdin via a quoted here-document instead, and pass the disconnect timestamp as a positional argument, which is safe because an ISO-8601 timestamp contains no whitespace or shell metacharacters.

    State plainly that regenerating the whole window every time is unconditionally safe on this channel, and that consequently there is no rotation-repair path here and none is needed — neither of the journald channel's two hazards, an earliest-entries rotation that silently shortens the window and duplicated polls from appending overlapping reads, can occur against a keep-forever table with a uniqueness constraint on the insert.

    The fallback path keeps the journald mechanism documented, not deleted: if `history.db` is ever unavailable — the file missing, the timer stopped, the ingest pipeline broken — the same record can be produced by piping `journalctl -u skypane-byos.service --since '<disconnect time>' -o short-iso --no-pager` over SSH into `python3 hardware/logtools.py from-journal`. Carry its two caveats with it, since they apply to it and not to the primary path: journald's retention window is bounded, so the regenerated file can start later than the run did, and the repair for that is the committed history of the log plus `check-battery`'s existing acceptance of several concatenated paths. Note that both converters emit the identical bracketed format, so `check-battery` and every threshold behave the same whichever produced the file, and record that the fallback is proven on `hardware/fixtures/battery-journal.log` exactly as the primary is proven on `hardware/fixtures/battery-history-db.jsonl`.

    **Second, add a new `## Protocol Amendment` heading directly below the existing one and above `## Daily Check-Ins`.** Use the same heading text and the same internal pattern as the first, so the document reads as a running amendment log rather than as two differently-shaped records. Leave the first amendment's heading and body untouched — a pre-registration whose earlier records get retitled or reworded is no longer a record. Its first line is `**Date:** 2026-09-02.` Immediately after, state that this is the second amendment to this protocol, that the first (dated 2026-08-27) is recorded above, and that this one supersedes it only where stated below.

    Record, in the first amendment's order:

    That this amendment, like the first, was made before the battery pack was ever connected to the board and before any measurement existed — no threshold could have been chosen with the answer already in hand.

    **What changed:** the primary observation channel only. It moves from tailing journald for `skypane-byos.service` to reading `history.db`'s `device_health` table. Give the reason as the three mechanisms, not as a preference: keep-forever retention against journald's bounded window, `INSERT OR IGNORE` idempotence against the duplicate-poll hazard, and continuous 30-second ingestion independent of the device's own poll cadence — on a pipeline that is already running in production with no setup step.

    **What also changed, as a consequence:** the daily check-in is downgraded from required to optional. Say why explicitly, because this is the one part of the protocol a reader could mistake for a relaxation of rigour: under journald, a missed check-in genuinely risked losing the earliest part of the record to rotation, so the check-in was a data-preservation mechanism. Under a keep-forever table it preserves nothing, because nothing between check-ins is at risk. A check-in is now purely for progress visibility and for catching a stalled run early — never for data preservation — and a run with no check-ins at all still yields a complete, gateable record.

    **What did not change:** the four validity thresholds (0.95 coverage, 3 maximum gap intervals, 100 mV minimum drop, 3400 mV depletion cutoff), the 21-day ceiling, the exact D-07 division, and every physical handling step for the pack — full charge, polarity re-check, protection-circuit confirmation, and the reading of `boot_count=` off the wake line before the cable comes out.

    **And, separately and emphatically, `SKYPANE_SLEEP_S` did not change and neither did the reasoning behind it.** It stays at the pre-registered 300 for the run and is restored to the production value afterwards, exactly as the first amendment set out. Say why it is called out here rather than left implicit: it is the device's own measured wake cadence, which is the subject of this measurement and the divisor every coverage and gap figure is computed against, and it has nothing whatever to do with which channel does the observing. An amendment to the ingestion path that quietly moved the divisor would invalidate the run while every gate still reported PASS.

    Close by recording that the journald path is retained as a documented fallback rather than removed, and that `hardware/logtools.py`'s `from-journal` subcommand, its fixture and its selftest case all remain in place and passing.

    **Third, update the one-line notes under two later headings, and nothing else.** `## Daily Check-Ins` becomes an optional progress record: say that rows are produced from the `from-history-db` command, that they are collected for visibility rather than for preservation, and that a missing row for a given day does not invalidate the run because the record is regenerated from `device_health` and not accumulated from these rows. `## Run Conditions` gains, alongside everything it already promises: whether `history.db` was reachable throughout and whether the journald fallback was needed at any point; and its journald-retention item becomes conditional on the fallback having been used. Keep every other item it promises — the public host, the sleep value in force and restored, service continuity, network outages, charge and recharge times, the pack's post-depletion condition — exactly as written. Leave `## Measured Inputs`, `## Verdict`, `## Cycle Count Reconciliation`, `## Discharge Trend`, `## What This Figure Does Not Cover` and `## Checker Output` untouched.
  </action>
  <verify>
    <automated>test -f hardware/BATTERY-RUN.md && for h in "## Run Protocol (pre-registered)" "### Observation channel" "## Protocol Amendment" "## Daily Check-Ins" "## Measured Inputs" "## Verdict" "## Cycle Count Reconciliation" "## Discharge Trend" "## What This Figure Does Not Cover" "## Checker Output" "## Run Conditions"; do grep -qF "$h" hardware/BATTERY-RUN.md || { echo "MISSING SECTION: $h"; exit 1; }; done; [ "$(grep -c '^## Protocol Amendment' hardware/BATTERY-RUN.md)" -eq 2 ] && grep -qF '**Date:** 2026-08-27' hardware/BATTERY-RUN.md && grep -qF '**Date:** 2026-09-02' hardware/BATTERY-RUN.md && for t in 'D-07' 'D-13' 'device_health' 'history.db' 'from-history-db' 'skypane-poll.timer' 'ingest_caddy_battery_log' 'record_device_health' 'INSERT OR IGNORE' 'keep-forever' 'Caddy' 'mode=ro' 'busy_timeout' 'journalctl' 'skypane-byos' 'from-journal' 'SKYPANE_SLEEP_S' 'interval_s' '21 day' 'protection circuit' 'battery-run-server.log' 'never for data preservation'; do grep -qF -- "$t" hardware/BATTERY-RUN.md || { echo "MISSING TOKEN: $t"; exit 1; }; done; grep -qF '| `--min-coverage` | 0.95 |' hardware/BATTERY-RUN.md && grep -qF '| `--max-gap-intervals` | 3 |' hardware/BATTERY-RUN.md && grep -qF '| `--min-mv-drop` | 100 mV |' hardware/BATTERY-RUN.md && grep -qF '| `--cutoff-mv` | 3400 mV |' hardware/BATTERY-RUN.md && grep -qF '3000 mAh' hardware/BATTERY-RUN.md && python3 -c "
import subprocess, sys
head = subprocess.run(['git','show','HEAD:hardware/BATTERY-RUN.md'], capture_output=True, text=True).stdout
now = open('hardware/BATTERY-RUN.md').read()
if not head:
    sys.exit('could not read the committed BATTERY-RUN.md from HEAD')
if '2026-09-02' in head:
    print('second amendment already committed; skipping the against-HEAD comparison')
    raise SystemExit(0)
AMEND = chr(35)*2 + ' Protocol Amendment'
PROTO = chr(35)*2 + ' Run Protocol (pre-registered)'
OBS   = chr(35)*3 + ' Observation channel'
DAILY = chr(35)*2 + ' Daily Check-Ins'
def span(text, start, end, label, start_from=0):
    i = text.find(start, start_from)
    if i < 0:
        sys.exit('could not locate the start of %s' % label)
    j = text.find(end, i + len(start))
    if j < 0:
        sys.exit('could not locate the end of %s' % label)
    return text[i:j].rstrip()
if span(head, PROTO, OBS, 'the pre-registered section in HEAD') != span(now, PROTO, OBS, 'the pre-registered section'):
    sys.exit('the pre-registered section above ### Observation channel is not byte-identical to its committed self - a threshold, the ceiling, the division or a physical precondition moved')
first_head = span(head, AMEND, DAILY, 'the first amendment in HEAD')
first_now  = span(now,  AMEND, AMEND, 'the first amendment', now.find(AMEND))
if first_head != first_now:
    sys.exit('the first Protocol Amendment (2026-08-27) is not byte-identical to its committed self - an existing pre-registration record was edited')
print('pre-registered section and the first amendment are byte-identical to HEAD')
" && echo "protocol amended a second time to the history.db channel; thresholds, ceiling, division, pack handling and the first amendment all provably intact"</automated>
  </verify>
  <acceptance_criteria>
    - `hardware/BATTERY-RUN.md` carries exactly two `## Protocol Amendment` headings, dated 2026-08-27 and 2026-09-02, the second placed below the first and above `## Daily Check-Ins`.
    - Everything from `## Run Protocol (pre-registered)` down to `### Observation channel` is byte-identical to its committed self, asserted by diff rather than by eye — so the four thresholds, the 21-day ceiling, the D-07 division, the 3000 mAh capacity, the both-outcomes paragraph, the physical-preconditions paragraph and the `**Server sleep value:**` paragraph are all demonstrably unmoved.
    - The first amendment's section is byte-identical to its committed self: an earlier pre-registration record was extended, not rewritten.
    - `### Observation channel` names `history.db`, `device_health`, `skypane-poll.timer`, `ingest_caddy_battery_log`, `record_device_health`, `INSERT OR IGNORE`, keep-forever retention (D-13), Caddy's access log, the read-only `mode=ro` URI and `busy_timeout`, and states that regenerating the whole window is unconditionally safe with no repair path needed.
    - The journald path survives as an explicitly documented fallback: `journalctl`, `skypane-byos` and `from-journal` all still appear, with their bounded-retention caveat attached to the fallback rather than to the primary path.
    - The second amendment states the date, that it predates the battery ever being connected, what changed (the primary channel), what changed as a consequence (the check-in downgraded to optional, with the phrase `never for data preservation`), what did not change (the four thresholds, the ceiling, the division, every physical step), and that `SKYPANE_SLEEP_S` and its reasoning are untouched because the divisor is the subject of the measurement, not part of the ingestion path.
    - `## Daily Check-Ins` describes an optional progress record whose absence does not invalidate the run, and `## Run Conditions` additionally promises whether `history.db` was reachable and whether the fallback was needed, while keeping every item it already promised.
  </acceptance_criteria>
  <done>The pre-registered document now records two amendments, says which sentence each one moved and why, and can prove — by diff against its own history, not by assertion — that neither of them touched a number the run is judged by.</done>
</task>

<task type="auto">
  <name>Task 3: Re-scope 05-01's two hardware tasks to the channel that cannot lose the record, and stop the check-in pretending to be a safety mechanism</name>
  <files>.planning/phases/05-low-battery-indicator/05-01-PLAN.md</files>
  <read_first>
    - `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` in full, and especially the complete task blocks for Task 2 (line 179) and Task 3 (line 246). Task 1 of that plan is already executed and must not be touched. Note the exact attributes on their two opening tags — `type="checkpoint:human-action" gate="blocking-human"` and `type="checkpoint:human-verify" gate="blocking"` — and both resume-signal bodies (lines 222 and 291), all four of which must survive this edit character for character.
    - `hardware/BATTERY-RUN.md` as amended by Task 2 of this plan — the rewritten `### Observation channel` subsection is where the canonical commands now live, and the second `## Protocol Amendment` is what these tasks now execute.
    - `hardware/logtools.py` `from-history-db` as landed by Task 1 of this plan, and `from-journal` which remains the fallback.
    - `server/history_db.py` — `device_health`'s columns and `UNIQUE(ts, battery_mv)` constraint (line 123), `record_device_health()` (line 201), `_TELEMETRY_HEADER_ALLOWLIST` and the T-06-01-03 note that only those four header names are ever extracted (line 74), and the D-13 keep-forever note (line 18).
    - `deploy/README.md` line 162 (`systemctl is-active skypane-poll.timer`) and `## Reading logs` (line 199) — the SSH idioms the preflight and fallback steps use.
    - Lines 320-341 of the plan, the `## Artifacts this phase produces (this plan)` table — two of its rows still describe a LAN address and LAN stability, left over from before the first amendment.
  </read_first>
  <action>
    Edit `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` so its Tasks 2 and 3 observe the run through `history.db`. Do not renumber the tasks, do not change either task's `type` or `gate` attributes, do not alter either `<resume-signal>`, and do not touch Task 1, which has already been executed. Change only the observation-channel mechanism and the commands that operate it — nothing about the pack, nothing about a threshold, nothing about `SKYPANE_SLEEP_S`.

    Start with the surrounding frame.

    In `<objective>`, the paragraph naming the two silent-failure modes currently attributes the second to the first amendment and lists journald rotation among the residual interruption risks. Extend it: the primary channel is now `history.db`'s `device_health` table, filled continuously by `skypane-poll.timer` from Caddy's access log with keep-forever retention, so the rotation risk is gone and the residual risks reduce to the frame losing home Wi-Fi or internet and the server or host going down. Keep the paragraph's conclusion exactly as it stands — both are still visible as missing polls in the record, and a checker written before the battery was connected still rejects them — and keep the phantom-power half of the paragraph untouched.

    In `must_haves.artifacts`, the `hardware/logs/battery-run-server.log` entry describes journald-converted telemetry; it is now `device_health` rows read out of `history.db` and converted by `from-history-db`. Update the description only; leave the path and the `contains` value alone.

    In the `## Artifacts this phase produces (this plan)` table, update three rows. The `hardware/logs/battery-run-server.log` row's note gains its new provenance. The `## Daily Check-Ins` row still promises a LAN address as a column and still says one row per day; make it one optional row per check-in with the service-active column the first amendment introduced. The `## Run Conditions` row still promises LAN stability; make it the public host, service continuity and channel availability. Those two are leftovers the first amendment missed, and they are wrong today regardless of this change. Replace those two promises outright — do not keep either phrase anywhere in the file, including inside a parenthetical or a "formerly" note, because the verify below asserts case-insensitively that neither survives.

    In `<threat_model>`, update the fourth trust-boundary row, which names the journald record as the source of the committed evidence log — it is now `device_health`, a keep-forever table, which is precisely why the row's own description of a rotating buffer no longer applies. Rewrite that description to name what is actually true: the evidence is regenerated on demand from a store that is never pruned, so the residual exposure is reachability of the database rather than loss of its contents. Update `T-05-01-02`'s mitigation to name the new channel among its three fronts, keeping its severity, its disposition, and its closing sentence forbidding the relaxation of a pre-registered threshold. Add one sentence to `T-05-01-06`'s mitigation recording that the history.db channel carries a structurally stronger disclosure guarantee than journald did: `history_db.tail_caddy_battery_log()` extracts header values only by name from a fixed four-entry allowlist and never copies the header map wholesale (T-06-01-03), so a credential cannot reach `device_health` even if Caddy stopped redacting. Keep the required secrets scan anyway — a guarantee and a check are not substitutes.

    Now Task 2 of that plan, `Charge the pack, pull the cable, and let it run for days`.

    In its `<read_first>`, add `server/history_db.py` (the `device_health` schema, `record_device_health()`, `ingest_caddy_battery_log()` and the D-13 keep-forever note), `deploy/skypane.env.example`'s `SKYPANE_STATE_DIR` and `SKYPANE_CADDY_ACCESS_LOG`, and `hardware/logtools.py`'s `from-history-db`. Keep the `deploy/README.md`, `deploy/skypane-byos.service` and `from-journal` entries, re-labelling them as the fallback channel's references. Point the `hardware/BATTERY-RUN.md` entry at both `## Protocol Amendment` sections and at `### Observation channel`, which is where the canonical commands now live. Keep the `hardware/BOM.md`, `hardware/BRINGUP-LOG.md`, `hardware/BACKOFF-OBSERVATION.md`, `firmware/VENDOR.md` and `deploy/skypane.env.example` `SKYPANE_SLEEP_S` entries exactly as they are.

    In its `<what-built>`, add that the observation channel is now the `device_health` ingestion pipeline Phase 6's plan 06-11 shipped, which has been recording this device's battery telemetry continuously since it landed.

    In its `<how-to-verify>`, rewrite the channel steps and leave every pack step alone. Specifically:

    Step 1 becomes the history.db preflight: confirm over SSH that `skypane-poll.timer` is active, that `skypane-byos.service` is active (the device still needs a server to answer it), and that `/opt/skypane/state/history.db` exists and `device_health` is currently receiving rows — running the documented query with a `since` of an hour ago and seeing rows come back is the check. Keep the note that no machine of the developer's has to stay awake, hold an address, or stay running for any part of the run.

    Step 2 currently gates the run on journald retention covering 21 days. Re-scope it rather than delete it: `device_health` is keep-forever, so retention no longer gates anything on the primary path; note journald's window only as a caveat that applies if the fallback is ever used, and say plainly that the primary record cannot be aged out.

    Step 3 — setting `SKYPANE_SLEEP_S` to the pre-registered 300, restarting the unit, confirming the frame's next response carries that sleep value, writing it into `## Measured Inputs` as `interval_s`, and noting the public host — stays exactly as written. Do not edit one word of it. It is the divisor every gate uses and it is the subject of the measurement, not part of the ingestion path.

    Steps 4 and 5 — full charge with USB connected, the final polarity check against the BOM, the charge duration, and the integrated-protection-circuit confirmation with its stop condition — stay completely unchanged. These are the two steps in the plan that can destroy hardware or start a fire, and this edit has no business anywhere near them.

    Step 6 becomes: create or truncate `hardware/logs/battery-run-server.log` by running the `from-history-db` conversion once against the current window, confirming the pipeline works end to end before it becomes the working copy of the record.

    Step 7 confirms the frame is reaching the production host. Make the primary form a query of `device_health` for the most recent row and a check that it is fresh; keep the journalctl follow form as the fallback. Note the ingestion latency so a developer does not misread it as a fault: a poll appears in `device_health` within roughly one ingest cycle of arriving, so allow a minute or two rather than expecting it instantly.

    Step 8 — reading `boot_count=` off the wake line with USB still connected, with both its reasons — stays exactly as written.

    Steps 9 and 11 — the cable coming out with the wall-clock note, and the instruction never to reconnect — stay verbatim.

    Step 10 waits for a poll to arrive with the cable physically out and in hand. Keep the step and its whole justification; change only where it is observed, which is now a new `device_health` row (or the journal, as fallback), and carry the same ingestion-latency note.

    Step 12, the check-in, changes the most. Reframe it as **optional**, and say why in the step itself rather than only in the protocol: `device_health` is keep-forever and ingested continuously, so nothing between check-ins is at risk and a check-in preserves nothing — it exists to show progress and to catch a stalled run early, and a run with no check-ins at all still yields a complete, gateable record. Give the command as the `from-history-db` pipe redirected over `hardware/logs/battery-run-server.log`, followed by the same `check-battery --status` call with the recorded `interval_s` and the rated capacity. Keep the columns the first amendment settled on — date and time, elapsed days, observed poll count, coverage, latest millivolts, age of the last poll, and whether `skypane-byos.service` is still active and whether it has restarted. Drop the journald-rotation instructions that belonged to the old channel: the file is regenerated from a store that never prunes, so committing it is a convenience rather than a repair path, and there is no first-line comparison to make.

    Step 13, the two numbers to watch, keeps both numbers and both thresholds; adjust only the diagnosis of a fallen coverage figure so it names what can actually cause one now — an outage between the frame and the server, or the service or host having gone down.

    Steps 14 and 15 keep their endings. Step 15's durable-record sentence changes: the durable record is `device_health` on the VPS, which is keep-forever and regenerable at any time, and the committed log plus the check-in table are its local mirror rather than the only copy. That is the sentence that makes it safe to walk away for three weeks.

    Leave `<resume-signal>` exactly as written.

    In its `<action>`, replace the journald regeneration with a final `from-history-db` regeneration over the whole run window. Keep the recorded `interval_s` usage exactly as it is — do not reintroduce a literal value anywhere. Keep the entire do-not-adjust-the-threshold paragraph and all three diagnoses verbatim, adjusting only any clause that attributes a gap to the old channel's rotation. Keep the check-in-table backfill instruction but soften it to whatever rows the developer chose to collect, since collecting them is now optional. Keep the secrets and bearer-token scan before committing, and keep the recorded facts including `interval_s` and `capacity_mah` being written into `## Measured Inputs`.

    Leave its `<verify>` block exactly as it stands — it reads the log file and extracts `capacity_mah` and `interval_s` from `## Measured Inputs`, and none of that depends on which converter produced the file. Confirm that by inspection rather than editing it.

    In its `<acceptance_criteria>`, keep every item and change exactly two. The daily-check-in-row criterion currently requires one row per calendar day of the run; make it one row per check-in actually performed, and state that an absent row does not invalidate the run because the record is regenerated from `device_health` rather than accumulated from those rows. Add one criterion: `hardware/logs/battery-run-server.log` was produced by `from-history-db` from `device_health`, or, if the fallback was used at any point, that fact is recorded in `## Run Conditions`. Leave the battery-only-proof criterion, the protection-circuit criterion, the opening-boot-count criterion, the coverage/gap/drop criterion with its thresholds, the recorded-`interval_s` criterion and the secrets-scan criterion untouched.

    Now Task 3 of that plan, `Read the closing boot counter off the device, compute the figure, and record what it does not cover`.

    Its device-side half is entirely unaffected and stays as written: reconnecting USB, the fresh stamped capture into `hardware/logs/battery-postmortem.log`, reading `boot_count=` off the first wake line, noting the wake reason, the recharge-and-inspect step with its swollen-or-hot stop condition, and the confirm-before-approving step. Change only these:

    Step 1 confirms the device has stopped by checking that no new polls arrived for at least an hour; point it at a fresh `from-history-db` regeneration rather than a journald one, and note that because ingestion is continuous the absence of new rows is a stronger signal here than the absence of new journal lines was.

    Step 5 reads the poll that follows the post-mortem boot; keep its unconditional framing and add that the post-mortem poll also lands in `device_health` within roughly one ingest cycle, so it can be confirmed from either channel.

    In its `<action>`, replace the journald regeneration reference with the history.db one and change nothing else about the analysis: the recorded `interval_s` stays, the boot-count adjustment for the post-mortem wake stays, the `--expect-depleted` condition stays, and all six section write-ups including the hash-skip limits section and the verbatim checker output stay as written. In the `## Run Conditions` instruction, add whether `history.db` was reachable throughout and whether the journald fallback was needed, and make the journald-retention item conditional on the fallback having been used; keep every other item — the public host, the sleep value in force and restored, service continuity, network outages, charge and recharge times, the pack's condition, the post-mortem wake reason, the clean-poll-without-reflash item — exactly as they are. Keep the instruction to restore `SKYPANE_SLEEP_S` to its production value and restart the unit, and to record that it was restored.

    Leave its verify block, its resume-signal, and everything below the closing tasks tag — the verification, success-criteria and output sections — untouched.

    In its `<acceptance_criteria>`, change only the `## Run Conditions` item, adding the channel-availability requirement alongside the public host and service continuity it already requires, and keeping the pack condition and recharge outcome.
  </action>
  <verify>
    <automated>P=.planning/phases/05-low-battery-indicator/05-01-PLAN.md && test -f "$P" && [ "$(grep -c '<'"task " "$P")" -eq 3 ] && grep -qF '</'"tasks>" "$P" && for t in 'from-history-db' 'device_health' 'history.db' 'keep-forever' 'skypane-poll.timer' 'journalctl' 'from-journal' 'skypane-byos' 'SKYPANE_SLEEP_S' 'interval_s'; do grep -qF -- "$t" "$P" || { echo "MISSING TOKEN: $t"; exit 1; }; done; for t in 'protection circuit' 'boot_count=' '21 elapsed days' 'polarity' 'hash_skip' 'D-07' 'battery-run-server.log' 'battery-postmortem.log' '0.95' '100 mV' 'secrets.h' 'SKYPANE_SLEEP_S=300'; do grep -qF -- "$t" "$P" || { echo "PHYSICAL/THRESHOLD STEP LOST: $t"; exit 1; }; done; grep -qF 'type="checkpoint:human-action" gate="blocking-human"' "$P" && grep -qF 'type="checkpoint:human-verify" gate="blocking"' "$P" && grep -qF 'with the date and time the cable came out, the opening boot count you wrote down' "$P" && grep -qF 'with the closing boot count you read off the first wake line, or paste the lines you actually saw' "$P" && python3 -c "
import re, sys
t = open('.planning/phases/05-low-battery-indicator/05-01-PLAN.md').read()
blocks = re.findall(chr(60) + r'task\b.*?' + chr(60) + '/task' + chr(62), t, re.S)
if len(blocks) != 3:
    sys.exit('expected 3 task blocks, found %d' % len(blocks))
for i in (1, 2):
    for tok in ('from-history-db', 'device_health', 'interval_s'):
        if tok not in blocks[i]:
            sys.exit('task %d does not mention %s' % (i + 1, tok))
for tok in ('protection circuit', 'boot_count=', 'polarity', 'SKYPANE_SLEEP_S=300'):
    if tok not in blocks[1]:
        sys.exit('task 2 lost a physical or divisor step: %s' % tok)
if 'INTERVAL_S' not in blocks[2]:
    sys.exit('task 3 verify no longer reads interval_s back from Measured Inputs')
for i, needle in ((1, 'capacity_mah'), (2, 'boot_count_end')):
    if needle not in blocks[i]:
        sys.exit('task %d lost its Measured Inputs contract: %s' % (i + 1, needle))
verify2 = re.search(r'<verify>.*?</verify>', blocks[1], re.S).group(0)
if 'INTERVAL=' not in verify2 or 'CAP=' not in verify2:
    sys.exit('task 2 verify no longer extracts both capacity_mah and interval_s from ## Measured Inputs')
low = t.lower()
if 'lan address' in low or 'lan stability' in low:
    sys.exit('a stale LAN-address artifact-table row survived the re-scope')
print('05-01 tasks 2 and 3 re-scoped to history.db; physical steps, thresholds, divisor, gate attributes and resume-signals intact')
" && python3 hardware/logtools.py selftest && echo "plan re-scoped and the checker it depends on still self-tests clean"</automated>
  </verify>
  <acceptance_criteria>
    - `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` still contains exactly three task blocks, with Task 1 unmodified.
    - Both remaining task blocks mention `from-history-db`, `device_health` and `interval_s`; the file still names `journalctl`, `from-journal` and `skypane-byos`, because the fallback is documented rather than removed.
    - Both task opening tags still carry their original `type` and `gate` attributes — `checkpoint:human-action` / `blocking-human` and `checkpoint:human-verify` / `blocking` — and both resume-signal bodies still match their original text, asserted by literal grep rather than by eye.
    - Task 2's block still contains its integrated-protection-circuit confirmation, its polarity re-check, its `boot_count=` readout before the cable comes out, and the literal `SKYPANE_SLEEP_S=300` — the divisor and every pack-handling step survived structurally, not by review.
    - The 21-day ceiling, the 0.95 coverage floor, the 100 mV drop floor, the `hash_skip` limits requirement, the D-07 division and the `secrets.h` scan all still appear in the file.
    - Task 2's `<verify>` still extracts both `capacity_mah` and `interval_s` from `## Measured Inputs`; Task 3's `<verify>` still reads `INTERVAL_S` back and is otherwise unedited.
    - The check-in step and its acceptance criterion describe an optional progress record whose absence does not invalidate the run, and say why: the record is regenerated from a keep-forever table rather than accumulated from those rows.
    - The `<objective>` interruption paragraph, the `battery-run-server.log` artifact description, the fourth trust-boundary row, `T-05-01-02`, `T-05-01-06` and three rows of the artifacts table all describe the history.db channel, and no stale LAN-address or LAN-stability promise survives anywhere in the file.
    - `python3 hardware/logtools.py selftest` still exits 0, confirming this documentation task broke nothing in the tool the plan depends on.
  </acceptance_criteria>
  <done>The plan that will actually be executed on hardware now reads from the store that has been recording this device since Phase 6, and the daily check-in has stopped claiming to protect something that was never at risk.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| external SSH reader -> a live production SQLite store | The run reads `history.db` while the 30-second ingest oneshot is writing to it; a careless reader can corrupt the store or lock out the writer |
| `device_health` rows -> the committed run log | The DEVICE-05 evidence is now derived from a production table this protocol does not own and cannot audit line by line |
| amended pre-registration -> the DEVICE-05 claim | This is the second edit to a document whose entire value rests on having been written before the answer was known |
| hand-written fixture -> the claim that the converter is correct | A fixture invented by the same person who wrote the converter proves only self-consistency |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-FWX-01 | Tampering | An external reader corrupting or locking `history.db` while the ingest oneshot writes to it | high | mitigate | The documented query opens the database through the read-only URI `file:<path>?mode=ro` with `uri=True`, which cannot create the file, modify it, or recover its WAL, and sets `PRAGMA busy_timeout=5000` to match the discipline `history_db.connect()` applies to its own connections (Pitfall 9, `server/history_db.py:21`), so a read landing mid-commit waits briefly instead of raising. Task 1's round-trip verify exercises exactly that connection form against a real `init_schema()` database. `server/history_db.py` and `stub-server/byos_server.py` are not modified at all (D-03). |
| T-FWX-02 | Repudiation | Editing a document explicitly labelled pre-registered, for the second time | high | mitigate | Task 2 adds a second dated `## Protocol Amendment` rather than rewriting the first, and its verify proves mechanically — by diffing against the committed copy in HEAD — both that the whole pre-registered section above `### Observation channel` is byte-identical and that the first amendment's section is byte-identical. An edit that moved a threshold, the ceiling, the division or a physical precondition fails the task rather than shipping. |
| T-FWX-03 | Tampering | A hand-written fixture that does not match what production actually writes | high | mitigate | Task 1 does not rely on the fixture alone. Its verify builds a throwaway database with the real `server/history_db.init_schema()`, inserts `battery-good.log`'s telemetry through the real `record_device_health()`, reads it back through the documented read-only URI and the documented SQL, converts it, and requires the result to equal `battery-good.log`'s messages. The committed fixture is thereby proven faithful to the production writer, not merely internally consistent. |
| T-FWX-04 | Tampering | A reading-less `device_health` row becoming a phantom poll | medium | mitigate | `tail_caddy_battery_log()` genuinely yields `battery_mv=None` when the header is absent or non-integer, and such a row carries no measurement. The converter drops any row whose `battery_mv` is not coercible to `int` and counts it in the stderr summary, and the fixture contains exactly such a row so the drop path is exercised rather than assumed. A phantom poll would inflate the observed count and therefore coverage — the direction that makes a damaged run read as a healthy one. |
| T-FWX-05 | Tampering | The divisor moving under cover of an ingestion-channel change | high | mitigate | `SKYPANE_SLEEP_S` is called out explicitly in the second amendment as unchanged and unrelated, with the reasoning stated: it is the device's own wake cadence, the subject of the measurement and the divisor every coverage and gap figure is computed against. Task 3's verify requires the literal `SKYPANE_SLEEP_S=300` to survive inside 05-01's Task 2 block, and requires both plan tasks to still route the recorded `interval_s` rather than any literal. |
| T-FWX-06 | Denial of Service | `history.db` unavailable mid-run with the journald path already deleted | medium | mitigate | The journald bridge is retained in full: `from-journal`, `hardware/fixtures/battery-journal.log` and its selftest case all stay, Task 1's verify re-runs the converter and requires the selftest to still name `battery-journal`, and Task 2 documents the fallback command with its bounded-retention caveat attached. Both converters emit the identical bracketed format, so every threshold behaves the same whichever produced the file. |
| T-FWX-07 | Information Disclosure | Production telemetry derived from a web-server access log committed to git | low | mitigate | `history_db.tail_caddy_battery_log()` extracts header values only by name from the fixed four-entry `_TELEMETRY_HEADER_ALLOWLIST` and never copies the header map wholesale (T-06-01-03), so `Authorization` and `Cookie` cannot reach `device_health` even if Caddy stopped redacting them. That is structurally stronger than the journald channel's guarantee. 05-01's existing requirement to scan each capture against `firmware/main/secrets.h` and for the issued bearer token before committing is preserved unchanged, because a structural guarantee and a check are not substitutes. |
| T-FWX-SC | Tampering | npm/pip/cargo installs | n/a | accept | This plan installs no packages. `from-history-db` adds exactly one import, `json`, which is standard library; `sqlite3` is deliberately not imported into `hardware/logtools.py` at all, since the database lives on the VPS and is read over SSH. Plan 01-07's AST import scan is re-run in Task 1's verify against a seven-module allowlist, so an eighth module or any non-stdlib module fails the task. |
</threat_model>

<verification>
- `python3 hardware/logtools.py selftest` exits 0 and covers eight fixtures, the seven it already covered plus `battery-history-db`.
- Converting `hardware/fixtures/battery-history-db.jsonl` yields telemetry messages byte-identical to `hardware/fixtures/battery-good.log`'s, and the converted file earns the same accepted verdict under the same flags.
- Rows written by the real `record_device_health()` into a real `init_schema()` database, read back through the documented read-only URI and SQL, convert to exactly `battery-good.log`'s messages.
- The three original battery fixtures and the backoff fixtures earn exactly their original verdicts; `from-journal` still converts its own fixture; the four `check-battery` defaults still read 0.95, 3, 100 and 3400 in `build_parser()`; and the AST import scan reports only the seven allowed stdlib modules.
- `hardware/BATTERY-RUN.md` carries two dated `## Protocol Amendment` sections, and both the pre-registered section above `### Observation channel` and the first amendment are byte-identical to their committed selves.
- `.planning/phases/05-low-battery-indicator/05-01-PLAN.md` contains three task blocks with their original `type`/`gate` attributes and `<resume-signal>` bodies, mentions the history.db channel throughout Tasks 2 and 3, retains every physical battery step, every threshold and the literal `SKYPANE_SLEEP_S=300`, and carries no surviving LAN-address promise.
- `server/history_db.py` and `stub-server/byos_server.py` are unmodified.
</verification>

<success_criteria>
- The DEVICE-05 discharge run is observed through a store that cannot lose its earliest entries, cannot double-count a re-read, and has been filling itself in production since Phase 6 with no setup step.
- Not one line of the analysis changed: `BATTERY_MV_RE`, `load_battery_polls`, `compute_battery_stats` and every threshold check compute what they computed before, and the new bridge is proven by routing content the checker already accepts through it and getting the same verdict.
- Every threshold, the ceiling, the division, every physical pack-handling step and `SKYPANE_SLEEP_S` are demonstrably unchanged — proven by diffing the pre-registered section against its own committed self, not by review.
- The daily check-in is honestly labelled: optional, for visibility, never for data preservation — and the run is safe to leave entirely alone for three weeks.
- The journald channel survives as a working, tested fallback rather than being replaced, so a `history.db` outage degrades the run instead of ending it.
- A reader of `hardware/BATTERY-RUN.md` can see that the protocol has now been amended twice, when, why, and precisely which sentence each amendment moved.
</success_criteria>

<output>
Create `.planning/quick/260902-fwx-second-protocol-amendment-device-05-batt/260902-fwx-SUMMARY.md` when done.
</output>
