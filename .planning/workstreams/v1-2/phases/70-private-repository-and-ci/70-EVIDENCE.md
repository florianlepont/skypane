# Phase 70: Evidence (owner checkpoints)

Names, run numbers and decisions only. No secret value, key material or fingerprint is recorded here.

## Manual deploy proof

Date: 2026-11-25. Everything below was done by the owner on his Mac and in GitHub; sessions did not read, set, rotate or delete any secret.

### Where the secrets live (names only)

| Name | Level |
|------|-------|
| DEPLOY_SSH_PRIVATE_KEY | repository |
| DEPLOY_HOST_KEY | repository |
| DEPLOY_SSH_TARGET | repository (also present in the `production` environment) |
| PRODUCTION_HOST | repository |
| FW_SIGNING_KEY | environment `firmware-signing` only (not touched; retired later, only after the Mac signing proof and the owner's typed confirmation) |

Repository variables: none set.

### Dedicated deploy key

- A new key pair for CI was created on the owner's Mac and its public half appended to the deploy user's `authorized_keys` on the server (comment `skypane-deploy-ci`). The private half was stored with `gh secret set` as the repository secret `DEPLOY_SSH_PRIVATE_KEY`, replacing the previous value.
- Local private copy: deleted by the owner (option a). FileVault is on. Only the public file remains.
- Old CI key line (comment `ink-frame-ci-deploy`) removed from the server after the first successful proof; the owner's personal login key was not touched and still works. A copy of the previous `authorized_keys` was kept on the server as `authorized_keys.bak-ci` (public keys only); the owner may delete it.
- To revoke the CI key: delete its single `skypane-deploy-ci` line from `authorized_keys`, then repeat the key creation and `gh secret set`.

### Runs of `deploy.yml`

| Run | Input | Result | Where it stopped |
|-----|-------|--------|------------------|
| 45712777893 | main, wrong `confirm_sha` (0000000) | failure, as required | step "Require the tip of main, the confirmation and a green CI run"; key, firmware download and deploy steps not run |
| 45712969497 | throwaway branch `proof/deploy-guard` (deleted afterwards) | failure, as required | step "Refuse to run from any ref other than main"; nothing after it ran |
| 45713258859 | main, correct confirmation, tip `02eb098` | success (53 s) | deployed with the dedicated key |
| 45713738451 | main, correct confirmation, after the old key was removed | success (55 s) | deployed with only the dedicated key |

### Live frame after the first proof deploy

Same flight and picture, status "En ligne", same settings (screen on, night 23:30 to 06:00, ORY runway 3). The battery reading moved from 83 % to 92 % between the two captures; a deploy cannot raise a battery level, so it is recorded as a reading change or charging, not a regression. The owner watches it.

### Owner decision on a server-side restriction of the deploy key

chosen: dedicated-key-only (decided by the owner, 2026-11-25)

The standing limitation applies whatever is chosen: on the Free private plan anyone with write access to the repository can dispatch `deploy.yml`, and a workflow on any branch can read repository secrets. With this choice the barrier is that the repository has one owner and the sessions and Dependabot are the only other writers. The key gives administrator rights on the server (the deploy user has passwordless sudo).

Phase 66 hand-off: write access = ability to dispatch deploy.yml and read repository secrets from any branch; owner choice: dedicated-key-only
