# Phase 55 Discussion Log

Human reference only (audits). Date: 2026-10-30. Questions asked in French; answers recorded here.

| Area | Question | Options | Answer |
|---|---|---|---|
| Unassigned frame | Representation | pending_devices table / nullable owner / dummy user | pending_devices table |
| Unassigned frame | Who registers a new frame | console form / CLI only | console form (hash only) |
| Pairing code | Format | 8 char Crockford / 6 char / 6 digits | 8 char Crockford XXXX-XXXX |
| Pairing code | Validity and wake | 30 min + 5 min / 60 + 15 / 15 + 5 | code 30 min, wake 5 min |
| Reassign/retire | Config on reassign | wipe / keep / keep except secrets | wipe everything |
| Reassign/retire | Retired frame | retired image + 24 h / 401 / hard delete | retired image + 24 h |
| User view | Extra pages for users | calendar+rules+airlines, health, poll/interval/LED | calendar, rules, airlines; health without sources |
| Console | Extras | locations, per-frame settings | locations for admin AND users; per-frame settings from console |
| Locations | User scope | pick only / create own / admin only | users create their own locations |
| User health | Content | frame only / + one-line data | frame only |

Claude's defaults recorded for validation: CSRF token (D-20), last-admin guard (D-15), live-frame protection on reassign/retire (D-13/D-14), audit log without purge (D-19).
Scope note: user-created locations (D-18) exceed the literal AUTH-05 wording; included at the owner's explicit request.
