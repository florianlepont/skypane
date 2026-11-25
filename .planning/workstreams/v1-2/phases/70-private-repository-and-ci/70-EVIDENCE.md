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

## Signed test release

Date: 2026-11-25. Done by the owner on his Mac and in GitHub; sessions never read, used or deleted a key or secret.

tag: fw-v1.2.2 (the next free number after fw-v1.2.1; the release occupies it permanently and is never scheduled for the frame)

prerequisites ok (Docker running, `gh` logged in with repository and workflow scopes, a full clone with tags, Mac on Apple Silicon so signing runs under emulation)

| Step | Result |
|------|--------|
| Build by CI (no key, no environment) | run 45715502682, success, unsigned artifact `fw-unsigned-fw-v1.2.2` |
| Dry run on the Mac | provenance and checksums verified, signatures verified against the committed public key, scratch import succeeded |
| dry-run published nothing: yes | `gh release view fw-v1.2.2` answered "release not found" after the dry run |
| Real publication on the Mac | release `fw-v1.2.2` with 7 assets (checked through the API) |
| release assets: 7 | main board image, `release.json`, second-board image and its json, bootloader, partition table, OTA data |
| Deploy answer at the publish prompt | `n` (deploy started by hand afterwards) |
| First deploy attempt | run 45720954578 refused as designed: the tip of main was a docs-only commit with no CI run (guard step), nothing deployed |
| Deploy by hand | run 45721077282, success, the server imported the release |
| listed in firmware_cli: not run | checked on the companion Update page instead: `fw-v1.2.2` shown as "available" and "newest", `fw-v1.2.1` still "running" |
| offered to frame: no | no installation scheduled; the owner did not press Install |
| frame poll unchanged: yes | the frame stayed online with the same flight, picture and settings (owner's check) |

## Signing key recovery (incident during this step)

The owner's attempts to take the signing key from his password manager failed: the first copy was a short unrelated field (20 bytes), and Apple Passwords cannot hold attachments. The only remaining copy was the environment secret `FW_SIGNING_KEY`, which cannot be read back. Recovery done once, by the owner:

- The owner created a recovery key pair on his Mac. Only the public certificate was given to a session and committed (on a branch that was never merged).
- A one-time workflow, started by the owner pushing a tag, encrypted the secret for that certificate and uploaded only the encrypted file (kept one day). The first attempt (run 45719131128) was refused by the environment's tag rule, so no secret was read; the owner added a temporary tag rule, and the second attempt (run 45719795193) succeeded.
- The owner decrypted it on his Mac, checked it is a valid RSA key, and the dry run then verified its signatures against the committed public key.
- The signing key and the recovery key now live in an encrypted disk image (vault) whose password is in the owner's password manager, with a second copy of the image elsewhere.
- Cleanup: the recovery branch and its two tags were deleted; the temporary tag rule was removed again; the temporary plaintext key file and the encrypted download were deleted by the owner (artifact deletion and file removal confirmed by the owner).
- Exposure to record: the key was read by a GitHub workflow in a repository that is still public, and left no plaintext in logs or artifacts. Whether to keep it or rotate it is the owner's decision below.

## Signing secret retired

Not done yet. It needs the owner's own typed confirmation and must happen before the visibility changes.

key decision: pending (owner chooses to keep the key, or to rotate it with a transition release; rotation is a separate act and is not done here)
