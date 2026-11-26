# Phase 70: CI measurements and decisions

Outcomes and numbers only. No serial number, network name, token or key.

## Decision record

D-07 decision: request-path-splitting-plan (decided by the owner, 2026-11-26)

The owner chose to have the CI split by changed paths, in a separate plan (70-06b), instead of keeping the whole suite on every code change. The constraints of that plan are the ones already agreed: no test is skipped for a change to code, the browser tests still run on every change to code, the aggregate check "Lint, test, coverage, attribution" always reports, and the coverage and test-count gates are not weakened. The visibility flip waits for that plan.

Context given to the owner before the decision: 22 of the last 52 commits were docs-only and already skip the CI; 28 test files read `firmware/`; the gates require the executed-test floor and a skipped ceiling of zero; `hardware/cad` holds only 3D and note files that no code or test reads.

## Runner host

- Machine: laptop, Apple Silicon (M5 chip), 16 GB of memory, arm64 (no emulation needed for the tests).
- Uptime: on almost all the time, no detailed schedule; a laptop sleeps when the lid is closed, so the runner serves jobs only while the Mac is awake (see the runner README).
- Sizing agreed: 2 single-use runners, one VM each, about 5 GB per VM, instead of the 4 runners of the kit's default; expected wall-clock per full run about 25 to 35 minutes (to be measured).
- Free disk space: to be confirmed by the owner (at least 60 GB advised).
