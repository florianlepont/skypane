# Phase 60: Device Co-Management - Context

**Gathered:** 2026-11-01
**Status:** Ready for planning

<domain>
## Phase Boundary

A frame keeps exactly one primary owner (`devices.owner_user_id`) and can also have co-managers. A co-manager views and changes the frame's settings like the owner, but cannot retire, reassign or remove it, and cannot remove the owner. The owner and an admin add and remove co-managers among already-invited users; a co-manager cannot add others. A user who is neither owner nor co-manager still gets a 404. Every add and remove is audited. Requirement: AUTH-08.

Out of scope: any production deploy, Phase 47 files and `hardware/`, Phase 55 planning lines, Phase 58 files, view-as-user (AUTH-07), notifications to co-managers.
</domain>

<decisions>
## Implementation Decisions

### Where co-managers are managed
- **D-01:** A "Co-managers" card on the frame's own page. Owner and admin get add/remove controls; a co-manager sees it read-only. The admin console may link to it but needs no separate add flow.

### Self-removal
- **D-02:** A co-manager can leave a frame ("Leave this frame" button). It is audited as a removal and is the only removal a co-manager can perform; it never touches anyone else.

### Reassignment
- **D-03:** When an admin reassigns the owner to a user who is already a co-manager, that co-manager row is deleted in the same transaction and the removal is audited. Other co-managers are kept. A frame owner is never also a co-manager.

### Locations
- **D-04:** A co-manager sees and assigns only the frame owner's locations (existing rule "a location of another owner is refused"). They create and edit no location on the owner's behalf. No relaxation of `fleet_db` location ownership.

### Eligible candidates
- **D-05:** Any invited, non-disabled user, including one who has not signed in yet; admins are eligible. Excluded: the owner and users already co-managers. Disabled users keep their rows but cannot sign in.

### Visibility
- **D-06:** A co-manager sees the owner's and all co-managers' e-mail addresses on the frame page (read-only).

### Orly frame
- **D-07:** The live Orly frame is managed like any other: it may have co-managers. This adds rows to a new table only; owner, MAC, secret, token, file paths, image and wake interval stay byte for byte, and `stub-server/test_phase47_freeze.py` stays green.

### Adding a co-manager
- **D-08:** A non-admin owner adds a co-manager by typing the e-mail address. Any address that is not an invited, active, eligible user (or is the owner or already a co-manager) gets one generic refusal, so the form never reveals who is invited. An admin may be offered the list of eligible users.

### Claude's Discretion
- Schema shape (migration v4, expand-only new table with a uniqueness constraint and no row for the owner), function names, audit action names and detail text, wording and French strings, card layout within the sketch-findings design system, Users-page frame counts, behaviour on user demotion or disabling.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/workstreams/v1-2/ROADMAP.md` (Phase 60) and `REQUIREMENTS.md` (AUTH-08)
- `.planning/workstreams/v1-2/phases/55-frame-pairing-admin-console-and-reduced-user-view/55-HANDOFF.md` §B — hooks for this phase (read only, do not edit)
- `.claude/CLAUDE.md` — conventions
- `companion/access.py`, `companion/routes.py`, `companion/route_types.py`, `companion/device_scope.py`, `companion/app.py::_effective_access`
- `server/fleet_db.py` (migrations v1–v3, `get_device_owner`, `assign_owner`, location ownership), `server/fleet_ops.py`, `companion/audit.py`, `companion/console_lifecycle.py`
- `companion/test_access_matrix.py`, `test-support/matrix_rows_*.py`, `stub-server/test_phase47_freeze.py`
</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `access.authorized_device_id(principal, device_id, owner_lookup)`: single ownership gate; `decide()` calls it for every `OWNER_DEVICE` route.
- Console route modules with CSRF POSTs and flash messages (`console_users.py`, `console_lifecycle.py`).
- `audit.actor_for`, append-only `audit_log`.

### Established Patterns
- Migrations are expand-only, indexed in `fleet_db.MIGRATIONS`; v3 is Phase 55's, add v4.
- Retire, reactivate, reassign and fleet console routes are `ADMIN_ONLY`: co-managers are excluded by construction.
- Two readers of ownership: `_effective_access` gate and `device_scope.load_devices_for`.

### Integration Points
- Frame page cards, Account frames list (mark shared frames), access matrix rows and `UNPREFIXED_OUTCOMES`.
</code_context>

<specifics>
## Specific Ideas

No specific requirements beyond the decisions above.
</specifics>

<deferred>
## Deferred Ideas

- Notifying a user when added as co-manager.
- Per-co-manager permission levels.
</deferred>
