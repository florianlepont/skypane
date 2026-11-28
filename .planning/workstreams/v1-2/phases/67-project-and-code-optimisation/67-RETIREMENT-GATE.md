# Phase 67 Retirement Gate (plan 18)

Owner checklist before old "rollback" data is retired. Short English; the owner reads French, so each item has a one-line French gloss.

## What this is and why

1. Phase 67 wants to remove old copies of data that were kept only so the previous release could be put back.
2. Removing them means the previous release can no longer run on today's data. Recovery would be the nightly backup.
3. Nobody here can see the real server, so nothing is removed on a guess: you run a few read-only commands and paste the result.
4. Each item below (G1 to G6) gets one decision from you: APPROVED, NOT APPROVED, or KEEP.
5. Later plans (19 to 22) read this file and do only what is marked APPROVED. Deploy stays manual and yours.

## Rules for pasting (public repository)

- Paste only counts and the words the command printed.
- Never paste values, tokens, secrets, hashes, hostnames, IP addresses, e-mail addresses or personal data. This repository is public.
- A device address (MAC) counts as a value: if a line contains one, write the line without it (for example `add device <removed>`).
- No command in this document writes anything. Each one only reads (a `--dry-run`, a `report`, an `ls`/`find` listing, or a SQLite file opened read-only).
- All commands run on the VPS, as the service user, like the other commands in `deploy/README.md`. `<STATE_DIR>` stands for the production state directory (the folder that holds `fleet.db`).
- The two Python module commands (`fleet_migrate`, `sqlite_migrations`) must be run from the current release directory. The `sh -c 'cd ... && exec ...'` form below does that.

## Order to run

1. Run the **report** command (section "Step 0") first. It shows which databases exist and their versions.
2. Run the **G1** commands (dry-run of the migration, then the count check). The dry-run also answers G2.
3. Run the **G2** listing.
4. Run the **G3** count.
5. G4 needs no command (you decided KEEP). G5 and G6 need only your decision.
6. Paste each result into its "Pasted output" cell, set each decision cell, and reply.

If a command fails with `invalid choice: 'report'` or `unrecognized arguments`, the deployed release is older than the one that added that command. Paste only that error line and stop: the item stays NOT APPROVED until a release with the command is deployed.

## Step 0: report (all databases, read-only)

```bash
sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec /opt/skypane/venv/bin/python3 -m server.sqlite_migrations report --state-dir <STATE_DIR>'
```

What it prints: one line per database, for example `fleet.db ok current=4 target=4 pending=0`, then `history.db ...` and one `devices/<id>/history.db ...` line per frame. It opens every file read-only and prints versions, step names and counts only. Exit status 0 means nothing pending; 1 means a step is pending; 2 means a file could not be read.

- Expected for this phase: `fleet.db ok current=4 target=4 pending=0`.
- If any line says `unreadable`, or fleet.db says `newer`, stop and tell the developer before going on.

Pasted output (Step 0):

```
No module named server.sqlite_migrations
```

The production release predates the migration module, so the report command is not available yet (2026-11-28). It will be run after the next deploy. This is not a blocker for G1 to G3.

---

## G1 Identity mirror (miroir d'identité : devices.json et byos_state.json)

*Français : on arrête de lire les anciens fichiers d'identité des cadres ; seule fleet.db fait foi.*

**Retired**

- The device server no longer reads or writes `devices.json` and `byos_state.json`.
- The `devices_cli` tool no longer mirrors changes into those two files.
- After this the device server reads `fleet.db` only.

**NOT retired**

- The two legacy files are not deleted: an owner-run tool moves them aside (quarantine), never removes them.
- `fleet_migrate` keeps its one-time, expand-only import of those files as a tool.
- `live_frame_macs.json` is unaffected.

**What stops working afterwards (rollback consequence)**

- If `fleet.db` is unreadable, the device server refuses enrolment and wake requests. It no longer falls back to the legacy files.
- The previous release can no longer be put back on this identity data. Recovery is the nightly backup.

**Commands (read-only)**

1. Dry-run of the import. It must report that fleet.db already holds every legacy frame, secret and token:

```bash
sudo -u skypane /bin/sh -c 'cd /opt/skypane/current && exec /opt/skypane/venv/bin/python3 -m server.fleet_migrate --state-dir <STATE_DIR> --dry-run'
```

2. Count comparison (counts only, nothing else is printed):

```bash
sudo -u skypane /opt/skypane/venv/bin/python3 -I -c "
import json, sqlite3, sys
legacy = json.load(open(sys.argv[1] + '/devices.json'))
tokens = json.load(open(sys.argv[1] + '/byos_state.json'))
db = sqlite3.connect('file:' + sys.argv[1] + '/fleet.db?mode=ro', uri=True)
n = lambda sql: db.execute(sql).fetchone()[0]
print('legacy devices:', len(legacy['devices']), ' legacy tokens:', len(tokens['tokens']))
print('fleet devices:', n('SELECT COUNT(*) FROM devices'), ' fleet pending:', n('SELECT COUNT(*) FROM pending_devices'), ' fleet devices with token:', n('SELECT COUNT(*) FROM devices WHERE token IS NOT NULL'))
" <STATE_DIR>
```

**SAFE**

- Command 1 prints `nothing to do` as its first line, and no line starting with `add device`, `update secret from legacy`, `update token from legacy`, `upgrade fleet.db schema` or `would mark fleet.db migrated`. Lines saying `skip device ...: already a pending frame` are fine (that frame is handled by the pairing flow). A line `skipped N token(s) for unregistered device(s)` is fine (those tokens belong to removed frames).
- Command 2: `legacy devices` is less than or equal to `fleet devices` plus `fleet pending`.

**NOT SAFE**

- Command 1 prints any `add device`, `update secret from legacy`, `update token from legacy`, `upgrade fleet.db schema` or `would mark fleet.db migrated` line, or exits with `error: ...`. This means fleet.db is missing something the legacy files still hold.
- Command 2: `legacy devices` is greater than `fleet devices` plus `fleet pending`.
- Either command cannot read a file.

| Owner decision G1 | Pasted output |
|---|---|
| **APPROVED** (owner, 2026-11-28; both checks SAFE; the deploy remains manual and is done by the owner). | Command 1:<br>`nothing to do`<br>`skipped 1 token(s) for unregistered device(s)`<br>`airline default types: nothing to do`<br>`airline default types: nothing to do`<br>(no add, update, upgrade or mark line, no error line)<br>Command 2:<br>`legacy devices: 3  legacy tokens: 3`<br>`fleet devices: 2  fleet pending: 1  fleet devices with token: 2`<br>(3 <= 2 + 1 holds) |

---

## G2 Per-frame registry and artwork copies (copies par cadre des registres et des images)

*Français : on retire les copies par cadre des noms de compagnies et des images, déjà fusionnées à la racine.*

**Retired**

- Per-frame files `devices/<id>/manual_resolutions.json`, `airline_name_overrides.json`, `airline_default_types.json` and the folder `devices/<id>/illustration_overrides/`.
- The code that merged them into the fleet root (`fleet_registries` and `fleet_artwork` merge functions) and their entries in the backup list.

**NOT retired**

- The fleet-root registries and the fleet-root artwork (these are the live data).
- The per-frame files are moved aside by an owner-run tool, never deleted.

**What stops working afterwards (rollback consequence)**

- The previous release, which still reads the per-frame copies, would see them missing. Names and pictures edited only in a per-frame copy would be lost to it. Recovery is the nightly backup.

**Commands (read-only)**

1. The dry-run from G1 (command 1) already prints the merge lines. Re-read its output for lines starting `airline names:` and `artwork:`.
2. Listing of what exists (names, sizes and counts only):

```bash
sudo -u skypane /bin/sh -c 'cd <STATE_DIR> && find devices -mindepth 2 -maxdepth 2 \( -name manual_resolutions.json -o -name airline_name_overrides.json -o -name airline_default_types.json \) -printf "%s bytes  %p\n"; echo "pictures in per-frame illustration_overrides:"; find devices -mindepth 3 -path "*/illustration_overrides/*" -type f | wc -l; echo "markers:"; ls -l airline_registry_migration.json illustration_migration.json 2>&1'
```

**SAFE**

- The dry-run lines say `airline names: nothing to do` and `artwork: nothing to do`, or print no `airline names:` / `artwork:` lines at all (no per-frame copies exist).
- No line says `would merge`.
- If the listing shows per-frame files or pictures, both marker files (`airline_registry_migration.json`, `illustration_migration.json`) are listed. If the listing shows no per-frame files and no pictures, the markers may be missing (nothing was ever merged): that is fine.

**NOT SAFE**

- Any dry-run line contains `would merge`.
- Per-frame files or pictures exist and a marker file is reported as `No such file or directory`.

| Owner decision G2 | Pasted output |
|---|---|
| **APPROVED** (owner, 2026-11-28; SAFE, nothing exists to retire in production; the deploy remains manual and is done by the owner). | The dry-run printed no `airline names:` or `artwork:` line and no `would merge` line.<br>Listing: no per-frame registry file listed (none of the three files under `devices/*`); pictures in per-frame illustration_overrides: 0; markers: both marker files absent (legitimate, no per-frame copies exist). |

---

## G3 legacy-admin session principal (identité de session "legacy-admin")

*Français : on retire l'ancien type de session administrateur à mot de passe partagé, supprimé le 2026-10-30.*

**Retired**

- The value `legacy-admin` for the session principal, and the database rule that allows it. The `sessions` table is rebuilt (fleet.db schema 5).
- Any `legacy-admin` rows are expired sessions and are deleted by that rebuild.

**NOT retired**

- Normal user sessions (principal `user`) are untouched. Nothing in production code creates a `legacy-admin` session today.

**What stops working afterwards (rollback consequence)**

- The previous release refuses a fleet.db at schema 5 (it stops with "newer than supported"). You accept that rollback for fleet.db is over. Recovery is the nightly backup.

**Command (read-only)**

```bash
sudo -u skypane /opt/skypane/venv/bin/python3 -I -c "
import sqlite3, sys
db = sqlite3.connect('file:' + sys.argv[1] + '/fleet.db?mode=ro', uri=True)
rows = db.execute('SELECT principal, COUNT(*), COALESCE(SUM(expires_at > CAST(strftime(\"%s\", \"now\") AS INTEGER)), 0) FROM sessions GROUP BY principal').fetchall()
print('principal, total, still-valid:', rows if rows else 'no sessions')
" <STATE_DIR>
```

It prints one tuple per principal: the principal word, how many rows, and how many are still valid. (It adds the "still valid" count to the agreed query `SELECT principal, COUNT(*) FROM sessions GROUP BY principal;`; the first two numbers are the same.) No session identifier is printed.

**SAFE**

- Output is `no sessions`, or only `user` lines, or a `legacy-admin` line whose still-valid count is `0` (all expired; the migration deletes them; say in your reply that you accept this).

**NOT SAFE**

- A `legacy-admin` line with a still-valid count above `0` (someone could still be signed in that way).
- The command fails.

| Owner decision G3 | Pasted output |
|---|---|
| **APPROVED** (owner, 2026-11-28; SAFE; G6 is APPROVED, so the condition that G3 waits for G6 is satisfied; the deploy remains manual and is done by the owner). | One row: principal `user`, total 8, still-valid 8. No `legacy-admin` row. |

---

## G4 wake_epochs table (table wake_epochs : historique des changements d'intervalle de réveil)

*Français : décision prise : on GARDE la table.*

**Retired**

- Nothing. The owner chose KEEP.

**Kept**

- The `wake_epochs` table, its writer and its create statement stay. history.db is not changed (no schema 2). Plan 22 skips this item.
- Revisit only if the link between battery life and wake interval is abandoned.

**What stops working afterwards (rollback consequence)**

- Nothing changes.

**Command**

- None needed. (Optional and read-only if you are curious: `SELECT COUNT(*), MIN(ts), MAX(ts) FROM wake_epochs;` on `history.db`. The `report` command does not list this table until a drop step exists.)

| Owner decision G4 | Pasted output |
|---|---|
| **KEEP** (owner, 2026-11-27). Final. | Not needed. |

---

## G5 Leftovers needing no data check (restes sans données)

*Français : petits restes de code sans effet sur les données ; décision seulement.*

**Retired**

- `META_LAST_POLL_TRIGGER`: nothing writes it any more. If a stored row exists it is simply ignored.
- Three unused `fleet_db` helpers: `delete_location_if_unused`, `count_locations_owned`, `location_usage_counts`. They are not called and have no schema effect.

**NOT retired**

- Any table, column or row. The `meta` table stays.

**What stops working afterwards (rollback consequence)**

- Nothing. The previous release still runs on the same data.

**Command**

- None. Nothing here touches data.

**SAFE**: always (code only). **NOT SAFE**: not applicable.

| Owner decision G5 | Pasted output |
|---|---|
| **APPROVED** (owner, 2026-11-28; the deploy remains manual and is done by the owner). | Not needed. |

---

## G6 Rollback statement (fin de la période de retour arrière)

*Français : je confirme que l'on ne remettra plus la version précédente sur l'état actuel ; la restauration passe par la sauvegarde de nuit.*

**Statement for the owner to confirm**

After G1 to G3 are deployed (G4 is KEEP, G5 changes no data), the previous release cannot be restored on top of the current state. Recovery means restoring the nightly backup. In particular:

- G1: the device server no longer falls back to the legacy identity files.
- G2 (if approved): per-frame registry and picture copies are moved aside.
- G3: fleet.db becomes schema 5 and the previous release refuses it.

**Command**: none.

| Owner decision G6 | Owner confirmation and date |
|---|---|
| **APPROVED** (owner, 2026-11-28). G3 was blocked until this said APPROVED; it now does. | I confirm the rollback period of fleet.db is over (2026-11-28). After the schema 5 deploy the previous release cannot open fleet.db and recovery means restoring the nightly backup. The deploy remains manual and is done by the owner. |

---

## How the executor uses this document

- Plans 19 to 22 read this file first, in their first action, before touching any code.
- Plan 19 needs G1 APPROVED. Plan 20 needs G2 APPROVED. Plan 21 needs G3 APPROVED and G6 APPROVED. Plan 22 needs G5 APPROVED for its first task; its wake_epochs task is skipped because G4 is KEEP.
- "Approved in principle, waiting for result" is not APPROVED. A plan whose item is not APPROVED stops, writes a one-line SUMMARY ("skipped: <item> not approved") and reports. It never retires on a guess.
- If a pasted result contradicts the SAFE description above, the item is set to NOT APPROVED with the reason, even if the owner leaned towards approving. The executor never overrides an item the owner did not approve.
- The executor never reads or touches production data. It reads only what is pasted here, and removes any value, token, hash, hostname or address before committing the owner's answers.
- Nothing is deployed by the executor. Deploy stays manual and owner-run.
