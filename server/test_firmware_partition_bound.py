# SPDX-License-Identifier: AGPL-3.0-only
"""Each real hardware profile's OTA image bound equals the ota_0 slot size."""
import re
from pathlib import Path

from skypane_test_support import REPO_ROOT

import server.hardware as hardware


def _ota0_size() -> int:
    # partitions.csv columns: name, type, subtype, offset, size.
    for line in (Path(REPO_ROOT) / "firmware" / "partitions.csv").read_text().splitlines():
        cols = [c.strip() for c in line.split(",")]
        if cols[0] == "ota_0":
            return int(cols[4], 16)
    raise AssertionError("ota_0 is missing from partitions.csv")


def test_real_profiles_bound_matches_ota_slot():
    slot = _ota0_size()
    real = [p for p in hardware.REGISTRY.values() if not p.simulated]
    assert real
    for profile in real:
        assert profile.firmware.max_app_bytes == slot, profile.key


def test_ci_size_gate_literal_matches_ota_slot():
    # The workflow gates on 90 percent of this literal; it must be the slot size.
    text = (Path(REPO_ROOT) / ".github" / "workflows" / "firmware.yml").read_text()
    literals = {int(m, 16) for m in re.findall(r"0x[0-9a-fA-F]+(?= \* 90 / 100)", text)}
    assert literals == {_ota0_size()}
