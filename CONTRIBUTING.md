# Contributing

Thanks for your interest in SkyPane! It's a personal project, so replies
may take a few days, but issues and pull requests are welcome.

## Before you start

- For anything bigger than a small fix, please open an issue first so we
  can agree on the approach.
- Run `./scripts/run-all-tests.sh` and `server/.venv/bin/ruff check .`
  before opening a pull request; CI runs the same commands.
- Security problems go through private reporting, not issues — see
  [`SECURITY.md`](./SECURITY.md).

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
