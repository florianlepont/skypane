# SkyPane firmware signing and OTA authenticity

This document records the resolved Kconfig chain OTA relies on, and the
human-run procedure for generating, storing and rotating the private
signing key. No command in this document burns an eFuse; `espefuse.py
burn_*` is named only as forbidden.

## Resolved configuration (ESP-IDF v5.3.1)

Confirmed by running `idf.py reconfigure` against a scratch copy of
`firmware/` (never the committed sdkconfig) inside the pinned
`espressif/idf:v5.3.1` container, with
`CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y`,
`CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT=y` and
`CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y` layered onto
`sdkconfig.defaults;sdkconfig.ee02.defaults`, then reading the generated
`build-kconfig/sdkconfig` and the bootloader's own Kconfig help text
(`/opt/esp/idf/components/bootloader/Kconfig.projbuild` inside the
container).

Exact resolved lines (a full clean reconfigure, not an incremental one --
an incremental reconfigure can carry over a stale resolved value from a
previous run and misreport what a fresh build actually produces):

```
CONFIG_BOOTLOADER_APP_ROLLBACK_ENABLE=y
# CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK is not set
CONFIG_SECURE_SIGNED_ON_UPDATE=y
CONFIG_SECURE_SIGNED_APPS=y
CONFIG_SECURE_BOOT_V2_RSA_SUPPORTED=y
CONFIG_SECURE_BOOT_V2_PREFERRED=y
CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT=y
CONFIG_SECURE_SIGNED_APPS_RSA_SCHEME=y
CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT=y
# CONFIG_SECURE_BOOT is not set
# CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES is not set
# CONFIG_SECURE_FLASH_ENC_ENABLED is not set
# CONFIG_SECURE_BOOT_ALLOW_SHORT_APP_PARTITION is not set
CONFIG_SECURE_ROM_DL_MODE_ENABLED=y
# CONFIG_EFUSE_VIRTUAL is not set
# CONFIG_NVS_ENCRYPTION is not set
# CONFIG_FLASH_ENCRYPTION_ENABLED is not set
```

Re-run against the actual committed `firmware/sdkconfig.defaults` +
`firmware/sdkconfig.ee02.defaults` (no scratch edits) and confirmed
byte-identical for every line above.

**Signature scheme:** `CONFIG_SECURE_SIGNED_APPS_RSA_SCHEME=y` is
selected -- the bootloader's own Kconfig help for this option reads
"Appends the RSA-3072 based Signature block to the application." This is
the same RSA-3072 scheme Secure Boot V2 uses; `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`'s
own help text confirms it "uses the same app signature scheme as
hardware secure boot, but unlike hardware secure boot it does not
prevent the bootloader from being physically updated" -- i.e. the
security boundary is software (the running app's embedded public key),
not a hardware-locked eFuse key.

**`CONFIG_SECURE_SIGNED_ON_BOOT_NO_SECURE_BOOT` does not exist for this
scheme.** Its Kconfig entry reads
`depends on SECURE_SIGNED_APPS_NO_SECURE_BOOT && SECURE_SIGNED_APPS_ECDSA_SCHEME`
-- SkyPane resolves the RSA scheme, not ECDSA, so this symbol's
dependency is never satisfied and it is entirely absent from the
resolved sdkconfig (not even present as a commented-out
`# ... is not set` line; grepping the resolved file for
`SECURE_SIGNED_ON_BOOT` returns nothing). Practically: the bootloader
does not re-verify the app's signature on every boot, only
`esp_ota_ops`/`esp_https_ota` verify it on the way in during an OTA
update (`CONFIG_SECURE_SIGNED_ON_UPDATE_NO_SECURE_BOOT`). A USB-flashed
unsigned dev image still boots normally (nothing checks it), but that
same unsigned image, if it were ever the *running* app, could never
verify a subsequent OTA update, since there would be no public key
embedded in its signature block to check the next image against -- every
device must run a signed image before its first OTA.

**No eFuse-burning option is on.** `CONFIG_SECURE_BOOT`,
`CONFIG_SECURE_FLASH_ENC_ENABLED`, `CONFIG_NVS_ENCRYPTION`,
`CONFIG_BOOTLOADER_APP_ANTI_ROLLBACK` and `CONFIG_EFUSE_VIRTUAL` all
resolved as not set, confirmed both in the scratch-copy run above and
against the real committed defaults. `CONFIG_SECURE_SIGNED_APPS_NO_SECURE_BOOT`'s
own help text is explicit that this mode "does not prevent the
bootloader from being physically updated" -- the opposite of what a
hardware-locked eFuse key would guarantee, which is exactly the
trade-off this project chose: network-origin authenticity without an
irreversible hardware commitment.

## What is signed and why

Every OTA-eligible release image carries an RSA-3072 Secure Boot V2
signature block appended after the app image. On an update, the device
checks that signature against the public key embedded in the currently
running app's own signature block -- not against a hardware-locked key,
since no eFuse is used at all. A compromised server can serve any bytes
it likes, but the device will still refuse to boot an image signed with
the wrong key, or an image with no signature block at all.

The SHA-256 hash and byte size the server advertises alongside an offer
stay as an earlier, cheaper gate: they catch a truncated or corrupted
download before the device spends time on signature verification, but
they are not the security boundary -- the signature is. A hash and size
alone can be recomputed by anyone; a signature cannot be forged without
the private key.

## Release tags

A release is named `fw-vMAJOR.MINOR.PATCH`, created as a git tag on a
commit already on `main`. The first OTA-capable release is `fw-v1.0.0`,
which is also the compiled-in version floor: no device ever accepts, and
the server never offers, anything older.

## One-time key generation (human only)

Run this once, by hand, inside the pinned `espressif/idf:v5.3.1`
container on the developer's own Mac -- offline if possible, since the
key never needs to touch a network until it is uploaded as a secret.

1. Generate the signing key:
   ```
   espsecure.py generate_signing_key --version 2 --scheme rsa3072 \
       skypane-signing-key.pem
   ```
2. Extract the public half:
   ```
   espsecure.py extract_public_key --version 2 \
       --keyfile skypane-signing-key.pem skypane-signing-pubkey.pem
   ```
3. Store the private key as a GitHub Actions environment secret, in an
   environment named `firmware-signing` with the developer set as a
   required reviewer, so every signing run needs an explicit approval:
   ```
   gh secret set FW_SIGNING_KEY --env firmware-signing \
       < skypane-signing-key.pem
   ```
4. Make an encrypted offline backup -- a password manager attachment, or
   an `age -p` / `gpg --symmetric` encrypted file kept on the developer's
   Mac. Without this backup, losing the GitHub secret means losing the
   key permanently (see Rotation below).
5. Delete the plaintext private key from disk:
   ```
   rm -P skypane-signing-key.pem
   ```
6. Commit only the public key, at `firmware/signing/skypane-signing-pubkey.pem`.

The private key must never be copied to the VPS, committed to the
repository, or pasted into a chat or a log. It exists in exactly two
places: the `firmware-signing` GitHub environment secret, and the
developer's own encrypted offline backup.

## Rotation

A new signing key only ever reaches the device inside an image signed by
the *current* key -- there is no remote channel for changing the trusted
key directly, since the trust anchor is the running app's own embedded
public key. To rotate: sign a transition release with the old key that
changes nothing else, install it normally, then start signing subsequent
releases with the new key.

If the old key is lost or compromised before a rotation release ships,
the only recovery path is a USB flash carrying a factory image signed
with a new key.

## Forbidden

- Any `espefuse.py burn_*` command.
- Enabling hardware secure boot (`CONFIG_SECURE_BOOT`) or flash
  encryption (`CONFIG_SECURE_FLASH_ENC_ENABLED`).
- `CONFIG_SECURE_BOOT_BUILD_SIGNED_BINARIES=y` -- that would require the
  private key to be present on the build machine itself, which is
  exactly what CI-side out-of-band signing avoids.

## Local signing for bench images

For a bench image built from a release tag but not going through CI (for
example during the hardware session), the developer signs it locally
using the offline key inside the pinned container:

```
espsecure.py sign_data --version 2 --keyfile <path-to-decrypted-key> \
    --output <signed-output.bin> <unsigned-input.bin>
```

Delete the decrypted key file immediately afterward. `SKYPANE_VERSION_LABEL`
(for example `unsigned`) marks a bench image that has not gone through
this step, so it is never mistaken for a real release artifact.
