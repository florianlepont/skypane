# Contributing

Thanks for your interest in SkyPane! It's a personal project, so replies
may take a few days, but issues and pull requests are welcome.

## Before you start

- For anything bigger than a small fix, please open an issue first so we
  can agree on the approach.
- Set up `server/.venv` on Python 3.14 and install the dev dependencies
  with hashes enforced:
  ```bash
  python3 -m venv server/.venv
  server/.venv/bin/pip install --require-hashes -r server/requirements-dev.txt
  ```
- Run `./scripts/run-all-tests.sh` and `server/.venv/bin/ruff check .`
  before opening a pull request; CI runs the same commands. To run a
  subset, use pytest directly:
  `server/.venv/bin/python3 -m pytest <path> -k <expr>`.
- CI runs these jobs in parallel: static checks (ruff, mypy, guards,
  shellcheck, systemd scoring, attribution), the non-browser tests in
  shards, and the browser tests in shards. One aggregate check named
  `Lint, test, coverage, attribution` needs all of them, combines their
  coverage data, applies the coverage floor from `pyproject.toml` to the
  combined result and checks the JUnit totals; it is the check the
  production `deploy` job waits for. A bare `./scripts/run-all-tests.sh`
  still runs the whole suite with the coverage gate, as before.
- To run part of the suite the way a CI shard does, set
  `SKYPANE_TEST_GROUP` (`core` or `browser`), optionally
  `SKYPANE_TEST_SHARD=INDEX/COUNT` (0-based) and `SKYPANE_JUNIT_XML=path`.
  A partial run selects whole test files, writes coverage data only and
  never enforces the floor. `scripts/ci_shards.py check` fails if any test
  file would run in no shard.
- To change how many shards run, edit the matching `shard` list in
  `.github/workflows/ci.yml` and the `BROWSER_SHARDS` / `CORE_SHARDS`
  values at the top of that file (the aggregate check fails if they
  disagree). Shards are balanced from measured per-file times: refresh
  `scripts/ci_shard_weights.json` with `scripts/ci_shards.py weights
  <junit files>` (JUnit files come from the artifacts of a CI run).
  `scripts/ci_run_timing.py jobs <run id>` prints a run's job and step
  times.
- Tests must not touch the network — pytest-socket fails any test that
  opens a non-loopback socket. Use the `fake_providers` fixture in place
  of a real ADS-B/adsbdb call, and write only under `tmp_path`.
- Companion tests start the app with the `app_server` / `make_app_server`
  fixtures (`companion/conftest.py`) and use the helpers in
  `test-support/companion_app_server.py` and
  `test-support/companion_markup.py` to fetch and parse what it serves.
- Tests assert behaviour: rendered HTML, the served CSS or JS parsed
  structurally, or a real browser. They never read source files,
  comments or `.planning/`; `companion/test_suite_guards.py` enforces
  this.
- Dependency changes go in `server/requirements*.in`, then regenerate the
  hash-locked `.txt` files with `scripts/lock-deps.sh`.
- Security problems go through private reporting, not issues — see
  [`SECURITY.md`](./SECURITY.md).

## Code language and comments

- Code, identifiers, comments, docstrings, docs and commit messages are in
  English. The companion UI stays bilingual: English/French strings live in
  `companion/i18n_fr/` and every user-facing string literal — leave those
  alone.
- A comment says what the code does when that is not obvious, and why:
  invariants, security invariants, units, or a pointer to a spec.
- Don't put a plan, ticket, decision, review or phase ID in a comment; that
  history belongs in git and `.planning/`, not the code.
- `scripts/check_comment_history.py check` enforces this in CI, scanning
  every tracked code file.

## Licence of contributions

SkyPane is licensed under the AGPL-3.0, and its author also offers it
under a separate commercial licence (see [`README.md`](./README.md#licence)).
For that to stay possible, the author needs to be able to include
your contribution in both.

By submitting a contribution (a pull request, a patch, or code in an
issue), you agree that:

1. your contribution is licensed under the AGPL-3.0, like the rest of the
   project, **and**
2. you grant Florian Lepont a perpetual, worldwide, non-exclusive,
   royalty-free, irrevocable licence to use, modify, sublicense and
   distribute your contribution under other licence terms, including
   commercial ones; and
3. you wrote the contribution yourself, or otherwise have the right to
   submit it under these terms.

You keep the copyright on your contribution. If you don't agree to point
2, that's fine; just say so in your pull request and it will not be merged,
but the idea may still be implemented independently.

Contributions to `firmware/` are an exception: that directory is
Apache-2.0 (see `firmware/NOTICE`), and contributions to it are accepted
under Apache-2.0 only.
