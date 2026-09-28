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
