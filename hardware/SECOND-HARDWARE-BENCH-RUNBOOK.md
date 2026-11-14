# Second hardware: bench runbook

How the evaluation unit (Seeed XIAO ePaper EE04 with the 7.3 inch Spectra 6 panel,
800x480) is flashed, provisioned, updated over the air and paired on a bench, with
the commands that were actually run. Results are in
[SECOND-HARDWARE-VALIDATION.md](SECOND-HARDWARE-VALIDATION.md).

Commands are written for macOS and zsh. A line that ends in a `#` comment is not
valid in an interactive zsh, so none carries one.

## Rules

- Never plug the live frame into the bench computer and never run these scripts
  against it. Check the serial port first: only the EE04 should appear.
- Everything runs against a throwaway server state directory, never against the
  production server or its registry.
- The bench signing key stays outside the repository and is deleted when the
  session ends. It is never the release key.
- No battery is connected for the first power-up; use USB-C only.

## Before powering the board

- Jumper cap on the two positions next to the buttons (`50 PIN` and `GND`); the
  `24 PIN` pin stays free. A cap in the other place can blank or damage the panel.
- The 50-pin extension cable seated in the 50-pin connector (the long one) and the
  panel tail seated in its small connector, both latches closed flat. The gold
  contacts face the contacts of the slot; the cable is inserted straight and to the
  stop.
- Power switch on ON.

## One-time setup

```bash
python3 -m venv ~/skypane-bench/venv
~/skypane-bench/venv/bin/pip install -r server/requirements.txt
mkdir -p ~/skypane-bench/server-state ~/skypane-bench/images
espsecure.py generate_signing_key --version 2 --scheme rsa3072 ~/skypane-bench/bench-key.pem
export SKYPANE_SIM_HARDWARE=1
~/skypane-bench/venv/bin/python3 -m server.fleet_migrate --state-dir ~/skypane-bench/server-state --owner-email bench@example.invalid
head -c 960000 /dev/zero > ~/skypane-bench/live-placeholder.bin
```

`SKYPANE_SIM_HARDWARE=1` enables the gated hardware type. Without it the server
refuses the unit. The placeholder file is required by the server's command line and
is not used for the unit, which receives its own image.

## Build from a clean copy

`build.sh` refuses a release-style build when the working tree has untracked files
(for example logs under `hardware/logs/`). Build from a clean copy of the commit
instead, which also leaves those files untouched:

```bash
git worktree add --detach ~/skypane-bench/worktree main
cd ~/skypane-bench/worktree
```

A bench image with a version such as `fw-v1.0.6-bench1` is built from a local tag.
Keep **one** `fw-v1.0.*` tag on the commit at a time, otherwise the version is
ambiguous:

```bash
git tag fw-v1.0.6
SKYPANE_BOARD=second SKYPANE_PROFILE=dev SKYPANE_RELEASE_TAG=fw-v1.0.6 SKYPANE_VERSION_LABEL=bench1 firmware/build.sh
```

A plain dev build (no tag, no label) gives `fw-v1.0.X-N-g<hash>-dev` and is the base
image. Delete a local tag before building a base image from the same commit.

## Sign

```bash
espsecure.py sign_data --version 2 --keyfile ~/skypane-bench/bench-key.pem --output ~/skypane-bench/images/<name>.bin firmware/build-second-dev/skypane.bin
```

The deprecation warnings about `espsecure.py` and `sign_data` are harmless. For the
cable flash, sign into a copy and copy the signed file over
`firmware/build-second-dev/skypane.bin`, because `flash-second.sh` flashes that path
and verifies its signature.

## Cable flash and provisioning

```bash
export SKYPANE_PROFILE=dev
export SKYPANE_BENCH_PUBKEY=~/skypane-bench/bench-key.pem
firmware/flash-second.sh /dev/cu.usbmodem1101
```

The script ends with `SUCCESS` and the MAC. Provision the Wi-Fi, the server address
and a fresh enrolment secret into the secret partition (the password is asked
without echo; the network must be 2.4 GHz):

```bash
firmware/provision.sh /dev/cu.usbmodem1101 --wifi-ssid "<network name>" --api-base http://<bench computer address>:8642 --allow-http-base
```

It prints the SHA-256 of the secret. Register the unit with that value:

```bash
~/skypane-bench/venv/bin/python3 stub-server/fleet_cli.py --state-dir ~/skypane-bench/server-state devices add --mac <mac> --secret-sha256 <hash> --owner-email bench@example.invalid --hardware-type seeed-ee04-7in3-spectra6 --state-path auto
```

The commands the script prints for a registry line target the older registry; use
this one. Then run the bench server:

```bash
SKYPANE_SIM_HARDWARE=1 ~/skypane-bench/venv/bin/python3 stub-server/byos_server.py --image ~/skypane-bench/live-placeholder.bin --port 8642 --sleep 120 --state-dir ~/skypane-bench/server-state
```

`--sleep 120` makes the unit wake every two minutes. Plain http works only because
the dev profile allows it; a production image requires https.

The unit's serial port disappears while it deep-sleeps. Provisioning therefore has
to start right after unplugging and replugging the USB cable (or a RESET), while the
port is visible. After provisioning the chip stays in its bootloader; press RESET.

## What the unit sends and what to read

Each wake the server prints `telemetry: X-Fw-Version=... X-Boot-Reason=...
X-Battery-Mv=...` and, after an update attempt, `X-Ota-Result=<token>;<version>`. The
`GET /fw/<hash>.bin` line is printed when the transfer ends. The full picture is in
`~/skypane-bench/server-state/firmware/device_report.json`.

## OTA test series

Order and results are in the validation record. Rules that cost time on the bench:

- **One schedule at a time, and a finished one must be cleared.** The bench server does
  not close a schedule by itself (production does, in its poll loop). After a result
  such as `installed`, run the reconcile, or the next schedule answers `busy`:

  ```bash
  ~/skypane-bench/venv/bin/python3 -c 'import os; from server import firmware_registry as f; print(f.apply_reconcile(os.path.expanduser("~/skypane-bench/server-state"), hardware_type="seeed-ee04-7in3-spectra6"))'
  ```

  A schedule that ended in a failure counts attempts and stays `scheduled`, so it also
  answers `busy`. The simple reset is to stop the server, delete
  `~/skypane-bench/server-state/firmware` (bench only), publish and schedule again,
  and start the server.
- **Publish and schedule.**

  ```bash
  ~/skypane-bench/venv/bin/python3 -m server.firmware_cli --state-dir ~/skypane-bench/server-state import-bench --file ~/skypane-bench/images/<name>.bin --version <version> --hardware-type seeed-ee04-7in3-spectra6 --allow-foreign-key
  ~/skypane-bench/venv/bin/python3 -c 'import os; from server import firmware_registry as f; print(f.schedule_release(os.path.expanduser("~/skypane-bench/server-state"), "<version>", "<version the unit runs>", hardware_type="seeed-ee04-7in3-spectra6"))'
  ```

  The answers are `added <version>` and `scheduled`.
- **The image's own version must equal the version given to `import-bench`.** A file
  built earlier with another version is refused for that reason before its signature
  is looked at, which proves nothing about the signature.
- **A trial image must be confirmed before the next offer.** After an install the unit
  reports `trial;<version>` and, at the next wake, `installed;<version>`. Until then
  it refuses any new offer.
- **Battery floor.** The unit refuses an OTA at 3500 mV or less, before it checks the
  floor. Without a battery the reading floats; if it falls under 3500, replug the USB
  or connect a battery, or the result is `deferred-battery`.
- **Wrong signature.** Sign the same kind of image with a second throwaway key
  (`espsecure.py generate_signing_key ...`) and offer a higher version. Expected: the
  unit keeps its version and reports `fail-image;<version>`.
- **Unsigned image.** Run `import-bench` into an empty throwaway state directory with
  the unsigned binary of the matching version. Expected: `signature: image is not
  signed`, exit 1.
- **Floor refusal.** Build a dev image with a raised floor, install it, then offer a
  version below that floor but above the server's (`fw-v1.0.0`):

  ```bash
  SKYPANE_BOARD=second SKYPANE_PROFILE=dev SKYPANE_BENCH_FLOOR=fw-v1.0.8 SKYPANE_RELEASE_TAG=fw-v1.0.9 SKYPANE_VERSION_LABEL=bench4 firmware/build.sh
  ```

  Then an image `fw-v1.0.7-bench5`. Expected: no download and no updating screen, and
  `fail-floor;fw-v1.0.7-bench5`, the version unchanged. `SKYPANE_BENCH_FLOOR` is
  refused for the production profile.
- **Wrong hardware.** Not done on the panel, by the owner's decision: the live frame's
  image shares the chip and project name with the unit's and could drive the 13.3 inch
  panel driver on the 7.3 inch panel. The server side is shown in a scratch state
  directory: import a signed legacy-type build with `import-bench` (no
  `--hardware-type`), schedule it with `schedule_release(..., hardware_type="xiao-ee02-13in3-spectra6")`,
  register the unit as the evaluation type and poll as it. Every answer carries
  `firmware: null`, and the legacy `registry.json` keeps the same SHA-256.

## Pairing test

Run on the unit against a throwaway fleet database. First clear any enrolment of the
unit as a device (`devices remove --mac <mac>`), then register it as pending:

```bash
~/skypane-bench/venv/bin/python3 stub-server/fleet_cli.py --state-dir ~/skypane-bench/server-state devices register-pending --mac <mac> --secret-sha256 <hash> --hardware seeed-ee04-7in3-spectra6
~/skypane-bench/venv/bin/python3 stub-server/fleet_cli.py --state-dir ~/skypane-bench/server-state devices pending-list
```

At its next wake (within five minutes) the unit shows a pairing code on the panel.
Claim it by typing the code in any case, with or without the hyphen, in a short
script that does what the Fleet page does:

```bash
~/skypane-bench/venv/bin/python3 - <<'EOF'
import os
from server import fleet_db, fleet_ops
state = os.path.expanduser("~/skypane-bench/server-state")
conn = fleet_db.connect(state)
owner = fleet_db.get_user_by_email(conn, "bench@example.invalid")
actor = fleet_db.AuditActor(None, "bench", None)
print(fleet_ops.claim_pairing_code(conn, state, "<code shown on the panel>", int(owner["id"]), actor))
EOF
```

Retire and re-activate with the ids that the commands print (`d_...` for a claimed
frame, `p_...` for a pending or retired one). Stop the bench server first, as these two
commands wipe a directory without the busy guard that the console has:

```bash
~/skypane-bench/venv/bin/python3 stub-server/fleet_cli.py --state-dir ~/skypane-bench/server-state devices retire --id <d_id>
~/skypane-bench/venv/bin/python3 stub-server/fleet_cli.py --state-dir ~/skypane-bench/server-state devices reactivate --id <p_id>
```

A claimed frame that is not the live frame stays on its last image until a poll
writes one; the bench server serves the retired and the pairing frames only.

## End of the session

- Stop the bench server and delete the state directory if nothing is left to keep.
- `git worktree remove --force ~/skypane-bench/worktree` and delete the local
  `fw-v1.0.*` tags (`git tag -d ...`).
- Delete `~/skypane-bench/bench-key.pem` and the second throwaway key, and the images.
- Disconnect the unit, or leave it unpowered and unflashed for the next session.
