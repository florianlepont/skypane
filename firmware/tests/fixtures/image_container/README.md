# Image container golden fixtures

Small binary bodies, one per decoder outcome (valid, legacy and every
rejection class), plus `manifest.txt` listing the expected result of each.

Regenerate with:

    python3 firmware/tests/fixtures/image_container/generate_fixtures.py

The generator is deterministic and the bytes are committed, so the Python
decoder tests and the C reader tests read identical files. Each case line in
`manifest.txt` is `<file> <expected> <palette_id> <payload_len>`, optionally
followed by `panel_override <w> <h>`; without an override the panel is the
size on the `panel` line. The full-size 1200x1600 image is not committed:
the manifest carries its payload CRC-32 and the SHA-256 of the whole
container so both sides can regenerate and compare it.
