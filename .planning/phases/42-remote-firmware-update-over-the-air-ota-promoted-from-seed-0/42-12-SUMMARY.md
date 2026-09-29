---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 12
subsystem: firmware-signing
tags: [ota, signing, key-ceremony, human-checkpoint]
requires:
  - phase: 42-03
    provides: firmware/SIGNING.md procedure and RSA-3072 signed-app Kconfig chain
  - phase: 42-11
    provides: firmware-release.yml, which expects FW_SIGNING_KEY in the firmware-signing environment and the public key at firmware/signing/skypane-signing-pubkey.pem
provides:
  - firmware/signing/skypane-signing-pubkey.pem (RSA-3072 public key, committed)
  - GitHub environment firmware-signing (required reviewer florianlepont, deployment rule tag fw-v*) holding FW_SIGNING_KEY
  - Encrypted offline backup of the private key
key-files:
  created:
    - firmware/signing/skypane-signing-pubkey.pem
requirements-completed: []
duration: ~40 min (human procedure, guided)
completed: 2026-09-28
---

# Phase 42 Plan 12: Signing key ceremony Summary

**The developer generated the RSA-3072 firmware signing key offline and stored it in a reviewer-gated GitHub environment secret plus an encrypted backup. The public half is committed.**

## Task 1: key generation, done by the developer (checkpoint:human-action)

The orchestrator guided each step, ran no key command itself, and never read the private key. The developer:

1. Generated `skypane-signing-key.pem` in `~/skypane-signing` (outside the repository) with
   `espsecure.py generate_signing_key --version 2 --scheme rsa3072`. It ran inside `espressif/idf:v5.3.1` with `--network none`.
2. Extracted `skypane-signing-pubkey.pem` with `espsecure.py extract_public_key --version 2`, in the same container.
3. Created the `firmware-signing` GitHub environment. The orchestrator verified it read-only through the GitHub API: required reviewer is `florianlepont`, custom deployment policy is on, and the only rule is `fw-v*` of type `tag`.
4. Ran `gh secret set FW_SIGNING_KEY --env firmware-signing`. The orchestrator verified that `gh secret list --env firmware-signing` lists `FW_SIGNING_KEY`.
5. Made the encrypted backup with `gpg --symmetric --cipher-algo AES256`, which produced `skypane-signing-key.pem.gpg`.
   - Decryption checked once: `gpg --decrypt … | cmp - skypane-signing-key.pem` printed `OK`.
   - The developer copied the file to iCloud Drive (byte-identical, checked with `cmp`) and keeps the passphrase in Apple Passwords.
   - Apple Passwords was not used for the key itself because it takes no file attachments.
6. Deleted the plaintext private key with `rm -P`. It is confirmed absent from `~/skypane-signing`.
7. `PRODUCTION_HOST` already existed as a repository secret (`cortege.algernon.ovh`), set earlier in the session.
8. Pasted the public key block into the chat. It is byte-identical to the file, has no `PRIVATE` marker, and reads as `-----BEGIN PUBLIC KEY-----`.

## Task 2: commit the public key and check it

- `firmware/signing/skypane-signing-pubkey.pem` was written from the file the developer produced. It matches the pasted block.
- `openssl pkey -pubin … -noout -text` reports `Public-Key: (3072 bit)`.
- `grep -rlE 'BEGIN [A-Z ]*PRIVATE KEY' firmware/` prints nothing.
- The SHA-256 of the DER public key starts with `38d198008d695554`.

## Deviations

- The pinentry curses dialog did not render usably in the app's terminal pane. Its `<OK>` button was not obvious, so the passphrase prompt looked stuck. The dialog did complete, and the backup was verified afterwards. In future, use `--pinentry-mode loopback` in the app terminal.
- No sign-and-verify round trip was run here, because the private key had already been deleted. The first real check is the release workflow's own `espsecure.py verify_signature` step, and after that the hardware session (signed install accepted, wrong key refused).

## Self-Check: PASSED

- The public key file exists, is 3072-bit RSA, and there is no private key material under `firmware/`.
- The environment, reviewer, tag rule and secret were all confirmed through the GitHub API.
