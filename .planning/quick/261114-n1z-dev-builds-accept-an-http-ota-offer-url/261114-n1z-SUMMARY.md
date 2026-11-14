---
quick_id: 261114-n1z
status: complete
---
# Summary

Found on the bench unit: the server offered `fw-v1.0.5-bench1` four times (`device_report.json`) and the unit never downloaded it, because `parse_fw_offer` required https for the offer URL while the bench server answers over http.

- `api_client.c`: one argument changed from `false` to `s_allow_http`. In a production image `s_allow_http` is the constant `false`, so behaviour there is unchanged.
- `esp_https_ota` needs no change: it performs no scheme check of its own, and the signature, descriptor, floor and read-back checks that matter run after the download.
- Legacy (EE02) production image, before and after: identical sdkconfig, identical `nm -n`, identical `size -A`, identical `.flash.text`, `.iram0.text`, `.flash.rodata`, `.dram0.data` and `.rtc.data` bytes. Only the app descriptor (version string, build time) differs.
- 20 hardware-free firmware suites, the production static check and the comment-history guard pass; a second-profile dev image builds.

The TLS path of an OTA download is not exercised on the bench; it is exercised when the unit joins the fleet over https. The unit needs one more cable flash of a build containing this change.
