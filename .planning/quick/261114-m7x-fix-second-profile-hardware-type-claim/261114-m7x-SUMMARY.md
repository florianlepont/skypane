---
quick_id: 261114-m7x
status: complete
---
# Summary

Found on the bench unit: the unit polled and was enrolled, but a scheduled OTA offer was never served. The server withholds the offer when the announced `X-Hw-Type` differs from the type it assigned. The firmware default for `CONFIG_SKYPANE_HW_TYPE` is the legacy key and the second profile never overrode it.

- `firmware/sdkconfig.second.defaults`: `CONFIG_SKYPANE_HW_TYPE="seeed-ee04-7in3-spectra6"`.
- `firmware/tests/check_hw_type_key.sh`: the second profile's key must equal the server's evaluation key. Verified failing without the fix (`key '' != ...`) and passing with it.
- A built second-profile dev image's generated sdkconfig shows the new key; 20 hardware-free firmware suites, the production static check and the comment-history guard pass.

The unit currently flashed announces the old key. It must be cable-flashed once with a build of this change before the OTA bench run continues. The legacy build does not read this defaults file.
