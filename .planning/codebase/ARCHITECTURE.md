# Architecture summary

Source of the architecture block in `.claude/CLAUDE.md`. Only bullet lines are
carried into that block; the full document is `ARCHITECTURE.md` at the
repository root.

- The full architecture, the ADS-B to frame data flow, the persistent-state map and the deploy path are in `ARCHITECTURE.md` at the repository root; read it before changing a module boundary.
- Device: ESP-IDF firmware in `firmware/main/`, entry `app_main.c`, one wake, poll, display, deep-sleep cycle driven by `state_machine.c`.
- Poll process: `server/poll_loop.py` (systemd oneshot every 30 s) runs `server/fleet_cycle.py` then `server/poll_cycle.py` per frame: detect, enrich, render, write `panel.bin`.
- Device server: `stub-server/byos_server.py` serves the device protocol (`/device/v1/setup`, `/device/v1/display`, `/device/v1/log`, `/img/...`) on loopback behind Caddy.
- Companion: `companion/app.py` is the invited-user configuration web app (Auth0 sign-in, default-deny access, route table in `companion/routes.py`); it owns the writes of `fleet.db`.
- Persistent state: `fleet.db` and `history.db` (SQLite) plus JSON files under one state root, each frame in its own `devices/<id>/` directory.
- Backup: `deploy/backup/skypane_backup.py`, a nightly systemd oneshot of the state root.
- Deploy: manual `workflow_dispatch` in `.github/workflows/deploy.yml`, then `deploy/deploy.sh` and `deploy/activate.sh` (atomic release swap, rollback on a failed probe).
