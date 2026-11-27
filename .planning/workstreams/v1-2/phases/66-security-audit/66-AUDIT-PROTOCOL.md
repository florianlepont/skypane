# Security Audit Protocol

Working rules for every audit plan of this phase. Each plan reads this document first (66-AUDIT-PROTOCOL).

## Severity scale

- **Critical**: an unauthenticated party can take over the platform, its data or its devices at scale.
- **High**: a party without the right role can read or change other users' data, or defeat an integrity or signing control.
- **Medium**: a weakness that needs extra conditions (an existing account, local access, unusual configuration) before it has real impact.
- **Low**: a hardening gap with limited impact on its own.
- **Informational**: an observation or best-practice note with no direct impact.

## Two layers

- **Public-safe layer**: the section files and the final audit document in the repository. Safe to be read by anyone.
- **Held-back layer**: `$HOME/.skypane-audit-held/held-findings.md`. It lives outside the repository tree, is never committed and is never referenced by content from any repository file. It holds every unfixed or undeployed high or critical item.

## What the repository may contain

- Area name, method, and the files and routes read, as generic scope.
- Result: "no finding" or "medium/low recorded", with category, location and recommendation for each medium or low item.
- Never exploit steps. Never the value of a secret, token, key or personal data.
- In doubt, keep it out of the repository and tell the owner.

## Reporting to the owner

- High or critical: chat only, short French message, file and line only.
- Secrets or personal data: file and line, never the value.

## Method limits

- Read code and configuration; run the existing local tests; the pytest-socket guard stays on.
- No request of any kind to the production host. A specific test needs the owner's explicit written confirmation for that test.
- Read-only checks only.

## Fix rules

- Each fix is a small separate change with its own test.
- High or critical fixes are local commits on a local branch with a neutral message such as "maintenance change", and are not pushed until the owner says so in chat.
- Medium or low fixes go on a draft pull request.
- Never approve or run a production deploy from a session.
- Must not break: golden hashes of the legacy render, the freeze test of the stub server, the live frame, the access rules of the sign-in, admin console and co-management phases, English and French parity.
- Open pull requests are checked before touching a file.

## Section result status

Every section file uses exactly one Result value, `no finding` or `medium/low recorded`. The consolidation sets the values of all sections in one change, and the audit document repeats them, so no section stands out from the others.

## Push rule

No commit of this phase is pushed before the consolidation step of the final plan completes.

## Findings during audit plans

A weakness found while auditing is never fixed, patched or committed in an audit plan. It goes to the held-back file and to the owner in chat, and is fixed only in the dedicated fix plan. SUMMARY, STATE and deviation notes stay generic: no finding, severity or area differential.
