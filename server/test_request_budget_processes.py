"""The request budget holds across real, overlapping processes."""
from __future__ import annotations

import os
import subprocess
import sys


REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SPACING_S = 0.15
# A timestamp is printed just after the ledger stamps the request.
TOLERANCE_S = 0.06

WORKER = """
import sys, time
sys.path.insert(0, {repo!r})
from server import request_budget
ledger = request_budget.RequestLedger(sys.argv[1], spacing_s={spacing})
for _ in range(int(sys.argv[2])):
    if ledger.acquire("adsbfi"):
        print(repr(time.time()), flush=True)
"""

PAUSER = """
import sys
sys.path.insert(0, {repo!r})
from server import request_budget
request_budget.RequestLedger(sys.argv[1]).report_failure("adsbfi")
"""

PROBE = """
import sys
sys.path.insert(0, {repo!r})
from server import request_budget
ledger = request_budget.RequestLedger(sys.argv[1], spacing_s={spacing})
print(ledger.acquire("adsbfi"), ledger.acquire("adsblol"), flush=True)
"""


def _spawn(code, *args):
    source = code.format(repo=REPO_ROOT, spacing=SPACING_S)
    return subprocess.Popen(
        [sys.executable, "-c", source, *args],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=REPO_ROOT)


def _finish(proc):
    out, err = proc.communicate(timeout=60)
    assert proc.returncode == 0, err
    return out.split()


def test_three_processes_never_start_requests_closer_than_the_spacing(tmp_path):
    procs = [_spawn(WORKER, str(tmp_path), "6") for _ in range(3)]
    stamps = sorted(float(value) for proc in procs for value in _finish(proc))
    assert len(stamps) == 18
    gaps = [b - a for a, b in zip(stamps, stamps[1:])]
    assert min(gaps) >= SPACING_S - TOLERANCE_S


def test_a_pause_set_by_one_process_is_honoured_by_another(tmp_path):
    _finish(_spawn(PAUSER, str(tmp_path)))
    probe = _finish(_spawn(PROBE, str(tmp_path)))
    assert probe == ["False", "True"]


def test_a_pause_set_while_others_are_acquiring_stops_further_requests(tmp_path):
    workers = [_spawn(WORKER, str(tmp_path), "4") for _ in range(2)]
    _finish(_spawn(PAUSER, str(tmp_path)))
    for worker in workers:
        _finish(worker)
    assert _finish(_spawn(PROBE, str(tmp_path))) == ["False", "True"]
