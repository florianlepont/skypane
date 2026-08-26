---
phase: quick-260826-vlq
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: false
requirements: [QT-VLQ-01, QT-VLQ-02, QT-VLQ-03, QT-VLQ-04]
files_modified:
  - .claude/CLAUDE.md
  - README.md
  - ARCHITECTURE.md
  - pyproject.toml
  - scripts/run-all-tests.sh
  - scripts/check-attribution.sh
  - server/README.md
  - server/plane/detect.py
  - server/plane/enrich.py
  - server/test_dither.py
  - server/test_illustrations.py
  - server/test_poll_loop.py
  - server/assets/icons/illustrations/HANDOFF.md
  - stub-server/VENDOR.md
  - stub-server/byos_server.py
  - adsb-test/query_aggregator.py
  - hardware/BOM.md
  - hardware/BATTERY-RUN.md
  - hardware/BRINGUP-LOG.md
  - hardware/logtools.py
  - .planning/PROJECT.md
  - .planning/ROADMAP.md
  - .planning/REQUIREMENTS.md
  - .planning/STATE.md
  - .planning/quick/260826-vlq-renommer-le-projet-de-ink-frame-vers-sky/260826-vlq-CONTEXT.md
  - firmware/CMakeLists.txt
  - firmware/build.sh
  - firmware/flash.sh
  - firmware/VENDOR.md
  - firmware/main/app_main.c
  - firmware/main/state_machine.c
  - firmware/main/nvs_schema.h
  - firmware/main/api_client.c
  - firmware/main/api_client.h
  - firmware/main/secrets.example.h
  - firmware/main/wifi.c
  - firmware/main/wifi.h
  - .github/workflows/firmware.yml
  - .github/workflows/ci.yml
  - .gitignore
  - deploy/.gitignore
  - deploy/Caddyfile
  - deploy/README.md
  - deploy/deploy.sh
  - deploy/provision.sh
  - deploy/skypane-byos.service
  - deploy/skypane-poll.service
  - deploy/skypane-poll.timer
  - deploy/skypane.env.example

user_setup: []

must_haves:
  truths:
    - "A newcomer reading README.md, ARCHITECTURE.md, or CLAUDE.md sees only the name SkyPane; no live document presents the project under its former name."
    - "firmware/build.sh produces a build artifact named after the new project and the ESP log tag / NVS namespace both carry the new name."
    - "The live OVH VPS runs systemd units under the new names, and the old-named units no longer exist on the box."
    - "The physical frame, which is NOT reflashed by this task, keeps getting HTTP 200 from the renamed server — its existing bearer token still validates."
    - "github.com/florianlepont/skypane resolves, the old URL redirects, and the local origin remote points at the new URL."
  artifacts:
    - deploy/skypane-byos.service
    - deploy/skypane-poll.service
    - deploy/skypane-poll.timer
    - deploy/skypane.env.example
    - firmware/build-ee02/skypane.bin
  key_links:
    - "The device's issued bearer token lives in byos_state.json inside the server state directory. Moving the application root without carrying that file forward permanently locks the device out (see T-VLQ-03)."
    - "firmware/CMakeLists.txt's project() name determines the build artifact filename, which .github/workflows/firmware.yml asserts on — both must change in the same commit."
    - "The systemd unit files reference environment variable names that live only in a hand-written, gitignored file on the VPS — renaming the variables in the units requires rewriting that file in the same cutover."
---

<objective>
Rename this project from its former name to **SkyPane** everywhere it is a live,
forward-looking reference: documentation, cosmetic code identifiers, the firmware
C sources, the deployment scripts and systemd units, the running production
services on the real OVH VPS, and the public GitHub repository.

Purpose: the project has a new name; every artifact a developer or a running
service reads should say so. The historical record (executed phase plans,
summaries, captured hardware logs) deliberately does not change.

Output: five atomic commits, a renamed and healthy production deployment, and a
renamed GitHub repository whose old URL redirects.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
@$HOME/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@.planning/PROJECT.md
@.planning/STATE.md
@.planning/quick/260826-vlq-renommer-le-projet-de-ink-frame-vers-sky/260826-vlq-CONTEXT.md
@deploy/README.md
@deploy/deploy.sh
@deploy/provision.sh
@firmware/VENDOR.md
</context>

<decision_map>
CONTEXT.md states its decisions under prose headings rather than numbered IDs.
This plan cites them as:

| ID | CONTEXT.md decision |
|----|---------------------|
| D-01 | *Convention de nommage* — keep the existing structure, change only the prefix; the firmware NVS namespace follows the same rule |
| D-02 | *Reflash firmware* — update and compile the firmware source only; the physical reflash is deliberately deferred to the developer |
| D-03 | *Downtime en production* — a few minutes of service interruption during the cutover is acceptable; no zero-downtime mechanism |
| D-04 | *Claude's Discretion* — update the local git remote after the GitHub rename; the local directory rename is the very last step, done by a human; casing follows each file's existing convention |
</decision_map>

<naming_rules>
Apply these substitutions. Casing follows each file's own convention (D-01, D-04).

| Former form | New form | Where |
|-------------|----------|-------|
| the two-word display name | `SkyPane` | prose, titles, header comments, systemd `Description=` |
| the lowercase one-word form | `skypane` | identifiers, service names, unix user, paths, log tags, NVS namespace, CMake project name |
| the lowercase hyphenated form | `skypane` | User-Agent strings, tempfile prefixes, repo slug |
| the C/env macro prefix `INK_` | `SKYPANE_` | firmware macros and VPS environment variables |

<!-- planner-discipline-allow: inkframe -->
<!-- planner-discipline-allow: ink-frame -->
<!-- planner-discipline-allow: Ink Frame -->
<!-- planner-discipline-allow: INK_ -->

**Out of scope — do not rewrite (historical record):**
- Everything under `.planning/phases/**` (executed PLANs, SUMMARYs, RESEARCH, CONTEXT, PATTERNS, VERIFICATION, SCRUB-RECORD).
- Everything under `.planning/research/**`.
- `hardware/logs/**` and `hardware/fixtures/**` — real captured serial output.
- Verbatim captured console excerpts *inside* `hardware/BRINGUP-LOG.md` (lines ~225-334) and `hardware/BACKOFF-OBSERVATION.md` — these are transcripts of runs that actually happened; only prose/titles around them may change.
- `.planning/STATE.md`'s Accumulated Context decision log and Session Continuity narrative — additive parentheticals only, zero deletions.

**Secrets hygiene (repo-wide rule for this whole plan):** the real VPS SSH
hostname and the real public host are treated as scrubbed literals in this repo
(established by the Phase 4 scrub passes). Refer to them as
`<vps-ssh-target>` and `<public-host>` in every file you write, including the
SUMMARY. Take the real values from the developer's SSH config / the
`DEPLOY_SSH_TARGET` GitHub secret / the orchestrator's own context at run time.
Never echo an environment file's *values* into the transcript — assert on key
names and counts only.
</naming_rules>

<tasks>

<task type="auto">
  <name>Task 1: Rename documentation and cosmetic code identifiers</name>
  <files>.claude/CLAUDE.md, README.md, ARCHITECTURE.md, pyproject.toml, scripts/run-all-tests.sh, scripts/check-attribution.sh, server/README.md, server/plane/detect.py, server/plane/enrich.py, server/test_dither.py, server/test_illustrations.py, server/test_poll_loop.py, server/assets/icons/illustrations/HANDOFF.md, stub-server/VENDOR.md, stub-server/byos_server.py, adsb-test/query_aggregator.py, hardware/BOM.md, hardware/BATTERY-RUN.md, hardware/BRINGUP-LOG.md, hardware/logtools.py, .planning/PROJECT.md, .planning/ROADMAP.md, .planning/REQUIREMENTS.md, .planning/STATE.md, .planning/quick/260826-vlq-renommer-le-projet-de-ink-frame-vers-sky/260826-vlq-CONTEXT.md</files>
  <action>
Apply the `<naming_rules>` table to every live document and to code identifiers
that carry no operational coupling. Nothing in this task changes runtime
behaviour; the test suite must stay green, which is the point of grouping them.

Documents — retitle and update prose: `.claude/CLAUDE.md` (the project name on
line 5), repo-root `README.md` (H1 plus the throwaway state-directory path in
the manual-poll example), repo-root `ARCHITECTURE.md` (the log-tag mention and
the whole deployment-topology block naming the two systemd units, the service
user, the env-file name and the secret's variable name — write these in their
post-rename form; Tasks 2 and 4 make reality match within this same session),
`pyproject.toml` / `scripts/run-all-tests.sh` / `scripts/check-attribution.sh`
header comments, `server/README.md` H1 and the two macro names it cross-references
(post-rename form, Task 2 makes them real),
`server/assets/icons/illustrations/HANDOFF.md`, `stub-server/VENDOR.md` (the
systemd-unit cross-reference in its local-modifications table),
`stub-server/byos_server.py`'s local-modifications docstring line only — every
other line of that file is vendored byte-for-byte and must not be touched.

`hardware/` documents: retitle `BOM.md`, `BATTERY-RUN.md` and `BRINGUP-LOG.md`,
and update `BATTERY-RUN.md`'s descriptive sentence. Do **not** touch the captured
console transcripts inside `BRINGUP-LOG.md` or the captured checker output in
`BACKOFF-OBSERVATION.md`. `hardware/logtools.py`: update its module docstring,
its argparse description, and the illustrative comment above the Log Line
Contract regexes. The regexes themselves never hardcode the tag — confirm this
by reading them before editing, and leave them unchanged so the historical
fixtures keep validating.

Code identifiers (cosmetic, no protocol coupling): the outbound User-Agent
strings in `server/plane/detect.py`, `server/plane/enrich.py` and
`adsb-test/query_aggregator.py`; the `tempfile.mkdtemp` prefixes in
`server/test_dither.py`, `server/test_illustrations.py` (two occurrences) and
`server/test_poll_loop.py`.

`.planning/` forward-looking docs: retitle `PROJECT.md`, `ROADMAP.md` and
`REQUIREMENTS.md`, update `ROADMAP.md`'s narrative paragraph, and update the two
GitHub URLs in `ROADMAP.md` to the new repo slug (Task 5 makes that URL real;
the old one will redirect regardless).

`.planning/STATE.md` — additive only. Leave the Accumulated Context decision
entries and every Session Continuity block byte-identical. In the two
Blockers/Concerns bullets that give a *forward-looking instruction* (the wake-interval
bullet naming the env file and its sleep variable, and the unvalidated-departure-threshold
bullet telling a future reader which journal unit to inspect), append a short
parenthetical giving the post-rename name. Do not rewrite the surrounding text.

`260826-vlq-CONTEXT.md` — this file currently contains the real VPS SSH hostname
in its Task Boundary section, which violates the repo's established scrub policy
before this directory is committed. Replace that literal with the placeholder
form already used in `deploy/README.md` (`ubuntu@vps-<id>.vps.ovh.net`). Change
nothing else in that file — it is a record of what the developer decided.
  </action>
  <verify>
    <automated>
      ruff check . &&
      scripts/run-all-tests.sh &&
      scripts/check-attribution.sh &&
      test "$(rg -ic 'inkframe|ink-frame|ink frame' README.md ARCHITECTURE.md .claude/CLAUDE.md pyproject.toml scripts/ server/ stub-server/ adsb-test/ .planning/PROJECT.md .planning/REQUIREMENTS.md | wc -l | tr -d ' ')" = "0" &&
      test "$(rg -c 'ovh\.net' .planning/quick/260826-vlq-renommer-le-projet-de-ink-frame-vers-sky/260826-vlq-CONTEXT.md)" = "1" &&
      ! rg -q 'vps-1440' .planning/quick/260826-vlq-renommer-le-projet-de-ink-frame-vers-sky/260826-vlq-CONTEXT.md &&
      git diff --numstat .planning/STATE.md | awk '{ if ($2 != 0) exit 1 }'
    </automated>
  </verify>
  <done>
All 9 test harnesses, ruff and the attribution checker pass unchanged. Zero
old-name occurrences remain in the listed live documents and source files. The
quick-task CONTEXT file carries the placeholder hostname form, not the real one.
`git diff --numstat` shows zero deleted lines in STATE.md (additive edits only).
`hardware/logs/`, `hardware/fixtures/`, `.planning/phases/` and
`.planning/research/` are untouched — confirm with `git status`.
  </done>
</task>

<task type="auto">
  <name>Task 2: Rename firmware C sources, build artifact, and macro prefix</name>
  <files>firmware/CMakeLists.txt, firmware/build.sh, firmware/flash.sh, firmware/VENDOR.md, firmware/main/app_main.c, firmware/main/state_machine.c, firmware/main/nvs_schema.h, firmware/main/api_client.c, firmware/main/api_client.h, firmware/main/secrets.example.h, firmware/main/wifi.c, firmware/main/wifi.h, .github/workflows/firmware.yml, .github/workflows/ci.yml</files>
  <action>
Rename the firmware per D-01 (structure unchanged, prefix swapped) and D-02
(source + compile only, no reflash).

**Build identity.** `firmware/CMakeLists.txt`'s `project()` name becomes the
lowercase new name. This changes the emitted binary's filename, so the three
places that name it must change in this same commit or CI breaks:
`firmware/build.sh`'s artifact echo, `firmware/flash.sh` (the explanatory comment
and the `APP_BIN` assignment), and `.github/workflows/firmware.yml`'s post-build
existence assertion. Also update the project-name header comment on line 1 of
both `.github/workflows/firmware.yml` and `.github/workflows/ci.yml`.

**Runtime identifiers.** The ESP log tag `TAG` in `firmware/main/app_main.c` and
`firmware/main/state_machine.c`; the NVS namespace macro value in
`firmware/main/nvs_schema.h`. The Log Line Contract's five line *shapes* are
frozen and must not change — only the tag that precedes them does. Update the
header comments in `app_main.c`, `nvs_schema.h`, `api_client.h` and
`secrets.example.h`.

**Macro prefix.** Rename the four credential macros in
`firmware/main/secrets.example.h` to the new prefix, and every read site:
`wifi.c` (SSID and password), `wifi.h` (two comments), `api_client.c` (the
API-base copy, the buffer-size comment, and two explanatory comments),
`api_client.h` (the header comment), `state_machine.c` (the setup-secret call
site). Update `firmware/VENDOR.md`'s rows describing the CMake project rename,
the credential-macro list, and the Log Line Contract tag.

**Local gitignored header.** `firmware/main/secrets.h` exists on this machine
and is gitignored — the build will not compile until its four `#define` names
match the new prefix. Rename the macro *names* in place and leave every macro
*value* byte-identical. This edit is deliberately not committed (the file is
ignored); say so in the SUMMARY. Never print the values.

**Behaviour note for the SUMMARY (D-02).** The physical device is on battery and
is not reflashed by this task. Until the developer reflashes it, the frame keeps
running the previous firmware image — old NVS namespace, old log tag, old macro
values — against the renamed server. That is expected and does not break the
device/server protocol, which is plain HTTPS over three endpoints and is not
coupled to the service names, the namespace, or the macro names. State this
explicitly in the SUMMARY together with the fact that the reflash is deferred to
the developer.

**Follow-on consequence to record:** once the developer *does* reflash, the new
NVS namespace starts empty, so the firmware's no-token branch runs the setup
call and the server issues a fresh bearer token. That path only works if the
firmware's setup-secret value still equals the server's BYOS secret value — both
values are preserved unchanged by this plan, so it does. Note it so a future
reader does not mistake the re-enrollment for a fault.

If Docker Desktop is not running, start it. If the container toolchain cannot be
reached at all, stop and report the task as blocked — do not mark it done on
inspection alone.
  </action>
  <verify>
    <automated>
      firmware/build.sh build &&
      test -f firmware/build-ee02/skypane.bin &&
      grep -q 'project(skypane)' firmware/CMakeLists.txt &&
      grep -q '"skypane"' firmware/main/nvs_schema.h &&
      grep -q 'SKYPANE_SETUP_SECRET' firmware/main/state_machine.c &&
      test "$(rg -v '^\s*[#/*]' -N firmware/main/*.c firmware/main/*.h firmware/CMakeLists.txt firmware/build.sh firmware/flash.sh | rg -ic 'inkframe|INK_')" = "0" &&
      test "$(rg -ic 'inkframe|ink-frame|ink frame' firmware/ .github/workflows/ | wc -l | tr -d ' ')" = "0"
    </automated>
  </verify>
  <done>
`firmware/build.sh build` completes with a zero exit status and emits
`firmware/build-ee02/skypane.bin`. The CMake project name, NVS namespace value
and log tag all carry the new name. No old-name or old-macro-prefix token
survives in any firmware source, build script, or workflow file. The local
gitignored credential header compiles against the renamed macros with its values
unchanged, and `git status` confirms it is still untracked/ignored. The SUMMARY
records the deferred reflash and the expected old-firmware/new-server interim.
  </done>
</task>

<task type="auto">
  <name>Task 3: Rename deploy unit files, scripts, and env template (local only)</name>
  <files>deploy/skypane-byos.service, deploy/skypane-poll.service, deploy/skypane-poll.timer, deploy/skypane.env.example, deploy/deploy.sh, deploy/provision.sh, deploy/Caddyfile, deploy/README.md, deploy/.gitignore, .gitignore</files>
  <action>
Rename the deployment artifacts in the repository. This task touches nothing
remote — it prepares exactly what Task 4 will install.

Use `git mv` for the four renamed files so history follows: the BYOS unit, the
poll service, the poll timer, and the env template. Then rewrite their contents
per `<naming_rules>`: `Description=` lines take the display name; `User=`/`Group=`,
`EnvironmentFile=`, `WorkingDirectory=`, `ExecStart=`, `ReadWritePaths=` and the
geofence path all take the new lowercase name in place of the old one, both in
the unix account name and in the `/opt/<name>` application root; the
`Unit=` line in the timer; every `${...}` environment reference takes the new
macro prefix.

`deploy/skypane.env.example`: rename all five variable keys to the new prefix,
update the state-directory default to the new application root, and update every
comment that names the env file, the unit files, or the firmware setup-secret
macro. Keep the placeholder values exactly as they are — this file carries
placeholders only.

`deploy/deploy.sh`: the header comment, `APP_ROOT`, all four `--rsync-path`
sudo-user invocations, both `--exclude` env-file patterns, the pip-install and
requirements-marker `sudo -u` calls, the ownership `chown`, the restart/start
systemctl invocations, and both journal-tail unit names and their echo labels.

`deploy/provision.sh`: the header comment, `APP_USER`, `APP_ROOT`, the three
`install -m 644` unit-file source and destination paths, the two `systemctl
enable` calls, the "enabled for boot" comment, and the four closing echo lines
that tell the operator which env file to write and which units to expect.

`deploy/Caddyfile`: header comment, the BYOS-unit cross-reference near the end of
the comment block, and the port-variable reference. The site block, the proxy
target and the log directive are unchanged — Task 4 deliberately does not touch
Caddy on the VPS, so its certificate and its installed config stay as they are.

`deploy/README.md`: every occurrence — the H1, the artifact table, the
provisioning walkthrough's `chown`/`chmod`/`cp`/`nano` command lines and paths,
the secret-variable names, the deploy-behaviour description, the health-check
`systemctl`/`journalctl` command lines, and the rollback and secrets-hygiene
sections. Keep the existing `<vps-ip>` / `vps-<id>.vps.ovh.net` placeholder forms
untouched.

Ignore rules: the repo-root `.gitignore` entry for the deploy env file and
`deploy/.gitignore`'s own entry and its explanatory comment both take the new
filename. There is no such file in this working tree (it lives only on the VPS),
so this is a defensive rule only.

Do not run `deploy.sh` or `provision.sh` in this task.
  </action>
  <verify>
    <automated>
      bash -n deploy/deploy.sh && bash -n deploy/provision.sh &&
      test -f deploy/skypane-byos.service && test -f deploy/skypane-poll.service &&
      test -f deploy/skypane-poll.timer && test -f deploy/skypane.env.example &&
      test "$(git ls-files deploy/ | rg -c 'inkframe' || true)" = "0" &&
      test "$(rg -ic 'inkframe|ink-frame|ink frame|INK_' deploy/ .gitignore | wc -l | tr -d ' ')" = "0" &&
      test "$(rg -c 'skypane' deploy/skypane-byos.service)" -ge 6 &&
      grep -q 'APP_USER="skypane"' deploy/provision.sh &&
      grep -q 'APP_ROOT="/opt/skypane"' deploy/deploy.sh
    </automated>
  </verify>
  <done>
The four deployment artifacts exist under their new names, tracked by git as
renames. Both shell scripts parse. No old-name or old-macro-prefix token remains
anywhere under `deploy/` or in either ignore file. Nothing has been sent to the
VPS yet.
  </done>
</task>

<task type="auto">
  <name>Task 4: Cut the live production VPS over to the new names</name>
  <files>(no repository files — this task operates on the live OVH VPS)</files>
  <action>
**This is the one genuinely risky task in this plan. It reconfigures the real
backend that a real, physically deployed frame depends on. It is not a sandbox.
Read the whole action before running a single command.**

Target: `<vps-ssh-target>` (login user with passwordless sudo). Per D-03 a few
minutes of downtime is acceptable, so a straight stop-rename-start cutover is
the chosen approach; do not build a zero-downtime mechanism.

**The failure mode that must not happen.** The device's issued bearer token is
stored server-side in `byos_state.json` inside the server's state directory. The
firmware only performs the enrollment/setup call when its NVS holds *no* token —
it never re-enrolls in response to an HTTP 401. The device holds a token now and,
per D-02, is not being reflashed and its NVS is not being erased. Therefore if
the cutover leaves that state file behind, the frame enters a permanent
401-then-backoff loop that no server-side fix can clear. Every step below is
ordered to carry that file forward.

**Step 0 — pre-flight, read only.** Record the current state of both units, that
the application root and its state directory exist, that the state file is
present, and the owner and mode of the hand-written environment file (use `stat`
with a format string — never `cat` that file). Capture the current active status
so you can compare afterwards. If the state file is absent, stop and report:
the plan's core assumption is wrong.

**Step 1 — quiesce.** Stop the poll timer, the poll service and the BYOS service,
then disable the BYOS service and the poll timer. Downtime starts here.

**Step 2 — rename the service account in place.** Use `usermod -l` and
`groupmod -n` to rename the existing account and group rather than creating new
ones. This keeps the UID and GID, so every file on disk stays correctly owned
with no recursive `chown` and no window where the state file is unreadable. Then
point the account's home directory at the new application root.

**Step 3 — move the application root.** A single `mv` from the old `/opt` path to
the new one. `mv` within a filesystem preserves ownership, modes and the entire
subtree, which is precisely how the state directory, the state file, the rendered
panel and the runway geofence config survive the rename.

**Step 4 — rewrite the environment file.** Rename it to the new filename inside
the moved application root, then rewrite its variable *keys* to the new prefix
with an in-place, anchored substitution, and rewrite the application-root path in
the state-directory value. Preserve every value byte-for-byte — in particular the
BYOS secret, which the device's existing token and the un-reflashed firmware's
setup secret both depend on. Verify by counting matching key names, never by
printing a line. Re-assert owner and mode match what Step 0 recorded.

**Step 5 — rebuild the virtualenv at the new path.** The moved virtualenv's
console-script shebangs still hardcode the old application root, which would make
the deploy script's pip invocation fail with a bad-interpreter error the next
time requirements change. Remove the moved virtualenv, recreate it at the new
path as the renamed service user, and delete the requirements-hash marker file so
the deploy script reinstalls the pinned requirements on its next run. This
installs only what is already pinned in `server/requirements.txt`, which prior
phases already audited — it is not a new-dependency event.

**Step 6 — install the new units, remove the old ones.** Copy the three renamed
unit files from this repository's `deploy/` directory to the VPS and install them
into the systemd system directory with mode 644, exactly as `provision.sh` does.
Delete the three old-named unit files from that directory. Reload the systemd
daemon, then enable the new BYOS service and the new poll timer. Leave Caddy
completely alone: its installed config and its Let's Encrypt certificate are keyed
to the public hostname, which does not change, and touching it would risk the
TLS termination for no benefit.

**Step 7 — deploy.** Run this repository's `deploy/deploy.sh` against
`<vps-ssh-target>` from the repository root on this machine. This is deliberate:
it exercises the whole rewritten script end to end, which is the real proof that
Task 3's edits are correct, rather than inspecting them.

**Step 8 — health gates.** All of the following must hold before this task is
done. Treat any failure as a rollback trigger:
  1. The new BYOS service reports active.
  2. The new poll timer reports active.
  3. Listing systemd unit files yields zero entries under the old name.
  4. The new poll unit's journal shows a real, completed poll cycle from after
     the cutover — not a startup line, an actual detect/render pass.
  5. **The decisive one:** the new BYOS unit's journal, restricted to the minutes
     since the cutover, shows the device's own display request answered with
     `200`, and shows no `401`. This is the direct evidence that the bearer token
     survived Step 3. Wait for at least one full device wake interval before
     concluding; the current interval is short, so this is a wait of well under a
     minute, but wait for the line rather than assuming.
  6. An unauthenticated request to the public host's display endpoint over HTTPS
     returns `401` — TLS and the auth gate both still work.
  7. The application port is not reachable from outside.

**Rollback, if any gate fails.** Reverse in order: stop and disable the new units,
remove them from the systemd directory, restore the three old-named unit files
from git (`git show HEAD~1:deploy/<old-name>` piped to the install path), `mv` the
application root back, rename the environment file back and revert its keys with
the inverse substitution, `usermod -l`/`groupmod -n` the account back, recreate
the virtualenv at the old path, `daemon-reload`, then enable and start the old
units. Confirm the device gets a `200` again before stopping. Report the failure
rather than retrying blindly.

Record in the SUMMARY: the exact cutover window, which gates passed with what
evidence, and confirmation that no environment-file value was printed at any
point.
  </action>
  <verify>
    <automated>
      ssh "$VPS" "systemctl is-active skypane-byos.service" | grep -qx active &&
      ssh "$VPS" "systemctl is-active skypane-poll.timer" | grep -qx active &&
      test "$(ssh "$VPS" "systemctl list-unit-files --no-legend | grep -c '^inkframe' || true")" = "0" &&
      test "$(ssh "$VPS" "ls /etc/systemd/system | grep -c '^inkframe' || true")" = "0" &&
      ssh "$VPS" "sudo journalctl -u skypane-poll --since '-5 min' --no-pager" | rg -q 'poll|detect|render' &&
      test "$(ssh "$VPS" "sudo journalctl -u skypane-byos --since '-5 min' --no-pager | grep -c ' 401 '" || true)" = "0" &&
      ssh "$VPS" "sudo journalctl -u skypane-byos --since '-5 min' --no-pager" | rg -q '200' &&
      test "$(curl -sS -o /dev/null -w '%{http_code}' "https://${PUBLIC_HOST}/device/v1/display")" = "401" &&
      ! nc -z -w 5 "${PUBLIC_HOST}" 8642
    </automated>
    <human-check>
Look at the physical frame. It should still be showing a rendered panel and
should refresh on its normal cycle. If it has gone blank or frozen on a stale
image, say so — that contradicts gate 5 and means rollback.
    </human-check>
  </verify>
  <done>
Both renamed units are active on the live VPS; no old-named unit file exists on
the box. A real poll cycle appears in the new poll unit's journal. The device's
own request is answered `200` with zero `401` responses since the cutover,
proving the bearer-token state survived the application-root move. TLS plus the
auth gate return `401` for an unauthenticated request and the application port is
externally unreachable. No environment-file value was printed. The developer has
confirmed the physical frame still refreshes.
  </done>
</task>

<task type="auto">
  <name>Task 5: Rename the GitHub repository, repoint origin, and push</name>
  <files>(no repository files — this task operates on GitHub and the local git remote)</files>
  <action>
Do this last, after Tasks 1-4 are committed and their gates have passed. The
public URL is the least reversible thing this plan changes and the thing other
people, clones and CI configurations may reference (D-04).

Rename the repository under the `florianlepont` owner to the new lowercase slug
using `gh repo rename`, run non-interactively from inside this repository. Then
repoint the local `origin` remote to the new SSH URL with `git remote set-url` —
GitHub redirects the old URL automatically, so this is hygiene rather than a
hard requirement, but do it (D-04).

Confirm the rename actually landed rather than assuming it: query the repository
and check the full name is the new one, and query the *old* path and confirm the
API resolves it to the new full name (that is the redirect, observed rather than
asserted).

Confirm the Phase 4 deployment machinery survived the rename, since a repo
rename carries environments and secrets but that should be verified, not
believed: list the repository environments and confirm the production
environment is still present with its required reviewer, and list the repository
secret names and confirm the three deployment secrets are still there. Names
only — never values.

Push `main` to the repointed remote. This triggers CI. The test job should go
green; the deploy job will queue behind the production environment's required
reviewer, which is the designed gate.

**One trap to handle deliberately.** STATE.md records a still-pending production
deployment from an earlier direct-to-main push (a docs-only commit) that was left
for the developer to approve. That deployment would check out `deploy/deploy.sh`
as it existed *before* this plan, so it would target the old application root
that no longer exists on the VPS and fail. Do not approve it. Reject or cancel
that stale pending deployment, and note in the SUMMARY that it was rejected
because the cutover made it invalid, not because anything is wrong with it.

For the deployment triggered by *this* push: leave the approval decision to the
developer. Report that it is pending and that approving it will re-run the
already-verified deploy script against the already-cut-over VPS, which is a
no-op-shaped repeat of Task 4 Step 7.
  </action>
  <verify>
    <automated>
      test "$(gh repo view --json nameWithOwner --jq .nameWithOwner)" = "florianlepont/skypane" &&
      test "$(gh api repos/florianlepont/ink-frame --jq .full_name)" = "florianlepont/skypane" &&
      git remote get-url origin | grep -q 'florianlepont/skypane' &&
      gh api repos/florianlepont/skypane/environments --jq '.environments[].name' | grep -qx production &&
      test "$(gh secret list --json name --jq '.[].name' | grep -c '^DEPLOY_')" = "3" &&
      git status --porcelain --branch | grep -q 'main\.\.\.origin/main' &&
      test -z "$(git log origin/main..HEAD --oneline)"
    </automated>
  </verify>
  <done>
`gh repo view` reports the new owner/name. The old repository path resolves to
the new full name through GitHub's redirect. The local `origin` remote points at
the new SSH URL. The production environment and all three deployment secrets
survived the rename. All local commits are pushed and `main` tracks
`origin/main` with nothing ahead. The stale pre-rename pending deployment has
been rejected, and the newly triggered one is reported as awaiting the
developer's own approval.
  </done>
</task>

</tasks>

<explicit_exclusions>
**The local directory rename is NOT a task in this plan and no executor may
attempt it.**

Renaming `/Users/florian/Projects/ink-frame` to `/Users/florian/Projects/skypane`
changes the working directory out from under the running session and would break
execution mid-flight. Per D-04 it is a manual final step performed by the
orchestrator (or the developer) *after* every commit in this plan is pushed and
Task 5's gates have passed. When it happens, the current session must be
restarted from the new path.

Also deliberately excluded, per `<naming_rules>`:
- `.planning/phases/**` and `.planning/research/**` — the historical record.
- `hardware/logs/**`, `hardware/fixtures/**`, and captured console excerpts inside
  `hardware/BRINGUP-LOG.md` and `hardware/BACKOFF-OBSERVATION.md`.
- `COMPLIANCE.md` and `LICENSE` — grepped clean; neither contains the former name.
- The physical device reflash (D-02) — deferred to the developer.
- Caddy's installed configuration and certificate on the VPS — the public
  hostname does not change, so there is nothing to rename and touching it would
  risk TLS for no gain.
</explicit_exclusions>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| laptop → production VPS (SSH) | Every Task 4 command crosses into the live backend of a physically deployed device |
| device → server (HTTPS) | The frame's bearer token is validated server-side against state that Task 4 relocates |
| local repo → public GitHub | Task 5 makes the renamed repository publicly addressable; Phase 4's scrub policy still applies |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-VLQ-01 | Denial of Service | device bearer token in the server state file | critical | mitigate | Task 4 Step 3 moves the application root with a single `mv` so the state subtree is carried forward intact; Step 2 renames the account in place so the UID is preserved and ownership never breaks; gate 5 proves a `200` for a real device request before the task is done, and any failure triggers the documented rollback |
| T-VLQ-02 | Information Disclosure | BYOS secret in the hand-written VPS environment file | high | mitigate | Task 4 Step 4 rewrites keys with an in-place anchored substitution and never reads the file to stdout; verification counts key names only; Step 0/4 assert owner and mode 600 are unchanged |
| T-VLQ-03 | Information Disclosure | real VPS hostname / public host re-entering git | high | mitigate | `<naming_rules>` secrets-hygiene rule mandates placeholder forms in every written file including the SUMMARY; Task 1 redacts the real hostname already present in the quick-task CONTEXT file before it is committed |
| T-VLQ-04 | Tampering | stale pre-rename pending production deployment | medium | mitigate | Task 5 rejects it explicitly rather than approving it — its checked-out deploy script targets an application root that no longer exists |
| T-VLQ-05 | Elevation of Privilege | CI deployment secrets and the production reviewer gate across the repo rename | medium | mitigate | Task 5 verifies the production environment and all three deployment secrets still exist after the rename, by name, before pushing |
| T-VLQ-06 | Tampering | firmware credential header on this machine | low | accept | `firmware/main/secrets.h` is gitignored; Task 2 renames only its macro names, leaves values byte-identical, never prints them, and the change is deliberately never committed |
| T-VLQ-SC | Tampering | package-manager installs | low | accept | No new dependency is introduced. Task 4 Step 5's `pip install` reinstalls only the already-pinned, previously-audited `server/requirements.txt`; no Package Legitimacy Gate entry is required |
</threat_model>

<verification>
Run after all five tasks:

1. `ruff check .` — clean.
2. `scripts/run-all-tests.sh` — all 9 harnesses pass, coverage threshold met.
3. `scripts/check-attribution.sh` — passes.
4. `firmware/build.sh build` — succeeds, emits `firmware/build-ee02/skypane.bin`.
5. `rg -il 'inkframe|ink-frame|ink frame' --hidden -g '!.git/'` returns **only**
   paths under `.planning/phases/`, `.planning/research/`, `hardware/logs/`,
   `hardware/fixtures/`, and the two hardware documents' captured-transcript
   sections. Any other hit is a miss — fix it.
6. `git status` is clean and `git log --oneline -5` shows five commits, one per task.
7. On the VPS: both renamed units active, no old-named unit file present, device
   answered `200`.
8. `gh repo view --json nameWithOwner` reports the new slug.
</verification>

<success_criteria>
- Every live document, cosmetic identifier, firmware source, and deployment
  artifact carries the new name; the historical record is byte-identical.
- The firmware compiles and emits a correctly-named artifact; the reflash is
  documented as deliberately deferred, with the interim old-firmware/new-server
  behaviour explained.
- The production VPS runs the renamed units, and the physical frame — which was
  not reflashed — is still being served successfully.
- The GitHub repository is renamed, the old URL redirects, the local remote is
  repointed, and all work is pushed.
- The local directory rename is left for a human, unattempted.
</success_criteria>

<output>
Create `.planning/quick/260826-vlq-renommer-le-projet-de-ink-frame-vers-sky/260826-vlq-SUMMARY.md` when done.

The SUMMARY must record, at minimum:
- The deferred firmware reflash and why the un-reflashed device is fine (D-02).
- The production cutover window, each health gate and the evidence for it, and
  explicit confirmation that the device's bearer token survived.
- That no environment-file value and no real hostname was written anywhere.
- That the stale pending deployment was rejected, and that the new one awaits
  the developer.
- That the local directory rename remains outstanding and requires a session
  restart from the new path.
</output>
