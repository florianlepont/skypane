# Phase 48: Fleet Data Model, Roles and Live-Frame Migration - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-28
**Phase:** 48-fleet-data-model-roles-and-live-frame-migration
**Areas discussed:** Live-frame migration safety, Hardware profile definition, Users/roles/locations model, Freeze list/backup/restore

---

## Live-frame migration safety
| Question | Options | Chosen |
|---|---|---|
| Auth source after migration | fleet.db + devices.json kept valid / fleet.db only / devices.json authoritative | fleet.db + devices.json kept valid |
| Trigger | CLI step in deploy / auto at start / manual | CLI step in deploy (backup + dry-run) |
| fleet.db missing or corrupt | fall back to devices.json / refuse all | fall back to devices.json |
| Proof of no change | real-state snapshot test / fake data only | real-state snapshot test |
**Notes:** User first asked which migration was meant; explained (devices.json + state files to fleet.db), then accepted recommendations.

## Hardware profile definition
| Question | Chosen |
|---|---|
| Where profiles live | code registry |
| Simulated types | two: same geometry + 800x480 landscape |

## Users, roles, locations
| Question | Chosen |
|---|---|
| User creation / first admin | CLI, owner = first admin |
| Location | own table linked to a device |

## Freeze list, backup, restore
| Question | Chosen |
|---|---|
| Backup | sqlite online backup in archive |
| Freeze list | written doc + failing test |

## Claude's Discretion
Schema details, module names, CLI verbs, plan split.

## Deferred Ideas
Web UI for users/devices (54-55); registry rewrite (49); per-device dirs (51).
