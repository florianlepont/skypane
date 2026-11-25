# Self-hosted CI runner on the owner's Mac

CI runs on the runner named by the repository variable `CI_RUNS_ON`. Unset,
every job runs on GitHub-hosted `ubuntu-latest`. This folder is the kit that
lets the same jobs run for free on a Mac, in single-use runners inside Linux
VMs. Nothing here installs or registers anything by itself; the steps below
are the owner's.

| File | Purpose |
|------|---------|
| `skypane-runner-loop.sh` | Host-side loop: one just-in-time runner per iteration, one job each |
| `com.skypane.ci-runner.plist.example` | launchd agent template, one copy per runner slot |
| `lima-skypane-ci.yaml` | The Linux VM definition (no host mounts, nothing forwarded) |

## Isolation statement

- The repository is private, on a personal account with no collaborators, and
  fork pull requests are off. Branches pushed by the owner's sessions and
  Dependabot pull requests are the only code that executes on this runner.
- Each job runs in a Linux VM with no host mounts (`mounts: []`), no
  forwarded port or ssh agent, and no macOS Docker socket (Docker runs inside
  the VM only). Jobs run as the unprivileged `runner` user.
- The VM holds no production secret, no deploy key and no signing key. The
  workflow `GITHUB_TOKEN` is `contents: read`. The deploy workflow runs on
  GitHub-hosted runners only.
- Runners are single-use (just-in-time registration): one job, then the
  runner is gone and its work folder is wiped.
- The admin token that registers runners lives only in the macOS Keychain on
  the host. It reaches GitHub through curl's standard input and is never put
  on a command line or in the VM's environment.
- Residual risk: a job can use the VM's CPU and reach the internet from it.
  On Apple Silicon the tests run on arm64 while production is x86_64; the
  dependency lock carries aarch64 wheels, so the install is unchanged.
- Dependabot's "run on self-hosted runners" setting must stay off.

## Concurrency

A CI run starts 8 jobs that do work (5 browser shards, 2 non-browser shards and
`static`) and the aggregate `test` job, which only waits. The launcher runs N = 4 parallel
runners, four launchd instances of the loop (`SKYPANE_RUNNER_INDEX` 1 to 4,
runner names `skypane-mac-<index>-<epoch>`), each with its own VM
`skypane-ci-<index>`. Four runners start a run's shards in two waves; this
trades VM memory against wall-clock time. Each VM is defined with 2 CPUs and
6 GiB (an estimate, not measured), so four need about 24 GiB of Mac memory.
Change N, and the VM sizes, after reading the wall-clock figures in the phase
measurements file.

Queue effect: with N = 4, two overlapping runs queue. The production deploy
requires CI to be green for the commit, so a deploy started while a push run
is still queued has to wait for that run or fails clearly. Deploy when no CI
run is queued.

## Exposure window and when to flip

The self-hosted runner can be live while the repository is still public. The
mitigations are the fork-pull-request job guard in `ci.yml` (a pull request
from a fork never reaches the runner), single-use runners, the isolated VM,
and one setting you make: Settings, Actions, General, "Fork pull request
workflows from outside collaborators" set to "Require approval for all
outside collaborators". The variable `CI_RUNS_ON` is set only after those
checks. Until then anyone can open a fork pull request, and the guard keeps
it off the runner.

## One-time install (owner)

1. Install Lima (`brew install lima`).
2. Per slot N in 1..4: `limactl start --name=skypane-ci-N deploy/runner/lima-skypane-ci.yaml`.
3. In each VM, as the `runner` user, download the pinned `actions/runner`
   tarball for the VM's architecture from the runner release page and verify
   its published SHA-256 from the same release page before unpacking into
   `/home/runner/actions-runner`. Do not run `config.sh`: runners register
   just in time.
4. Create a fine-grained token limited to this repository with
   "Administration: read and write" ONLY, and store it by typing it at the
   prompt: `security add-generic-password -s skypane-runner-pat -a skypane -w`.
5. Copy `com.skypane.ci-runner.plist.example` once per slot into
   `~/Library/LaunchAgents/`, replace the placeholders, create
   `~/Library/Logs/skypane-ci-runner`, then `launchctl load` each plist.
6. Check the runners show as idle under Settings, Actions, Runners.
7. Only then switch: `gh variable set CI_RUNS_ON --body '["self-hosted","skypane-ci"]'`.

Keep the Mac awake while it should serve jobs (`caffeinate -s`, or the Energy
settings). A sleeping Mac leaves jobs queued, and GitHub fails a job that has
been queued for over 24 hours.

## Fallback to GitHub-hosted runners

`gh variable delete CI_RUNS_ON` puts every job back on `ubuntu-latest`; the
steps that need sudo or apt run only there. A hosted run of a private
repository uses 2 vCPUs and bills minutes against a 2,000-minute monthly
allowance, so use the fallback deliberately.

## Cost watch

Self-hosted runners are free today. GitHub announced a $0.002 per minute
charge for them from 1 March 2026 and postponed it with no new date. Check the
GitHub Actions changelog before relying on this, and again before any
visibility change.

## Maintenance

- Runner updates: the runner binary may update itself when it starts; refresh
  the tarball in each VM now and then and verify its checksum again.
- Rotate or revoke the token: create a new one, replace the Keychain entry
  (`security add-generic-password -U -s skypane-runner-pat -a skypane -w`),
  then delete the old token in GitHub. The loop reads the Keychain on every
  iteration, so no restart is needed.
- Stop serving: `launchctl unload` each plist, or `gh variable delete CI_RUNS_ON`.
