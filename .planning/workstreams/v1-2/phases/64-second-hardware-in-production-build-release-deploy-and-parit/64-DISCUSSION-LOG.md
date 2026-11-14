# Phase 64: Second Hardware in Production - Discussion Log

> **Audit trail only.** Decisions are in 64-CONTEXT.md.

**Date:** 2026-11-14
**Areas discussed:** Production gate, release ordering, provision.sh guard

## Production gate
| Option | Selected |
|--------|----------|
| Dedicated switch (closed by default) | ✓ |
| Flip profile `gated` flag | |

**Notes:** Owner first did not understand the question; it was restated simply, then confirmed "second verrou à part".

## Release ordering
| Option | Selected |
|--------|----------|
| After the Phase 57 release | ✓ |
| Before the Phase 57 release | |

## provision.sh guard
| Option | Selected |
|--------|----------|
| Typed (MAC + typed confirmation) | ✓ |
| By port | |
