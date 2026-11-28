# SPDX-License-Identifier: AGPL-3.0-only
"""The short build id the Account page shows for a support request.

The release is staged under `<root>/releases/<40-hex git sha>/` and the service runs
from `<root>/current`, a symlink to that directory, so the path of this module is
resolved with `os.path.realpath` before the release directory name is read. Without
the resolution the name would be `current` and every release would read `dev`.

Only a validated run of hex digits ever leaves this module, so the value is safe to
render in markup and in an attribute.
"""
import os
import re

ENV_NAME = "SKYPANE_BUILD"
DEV_ID = "dev"
SHORT_LENGTH = 7

_RELEASE_NAME = re.compile(r"[0-9a-fA-F]{40}")
_ENV_VALUE = re.compile(r"[0-9a-fA-F]{7,40}")


def _release_dir_name(code_path):
    """The name of the directory holding the `companion` package, after symlinks are
    resolved: the release directory when the code runs from a release."""
    real = os.path.realpath(code_path)
    return os.path.basename(os.path.dirname(os.path.dirname(real)))


def build_id(code_path=__file__, environ=None):
    """The first 7 hex characters of the release's git sha, else of `SKYPANE_BUILD`
    (7 to 40 hex characters), else `dev`. Never raises and reads nothing but a path
    name and one environment value."""
    environ = os.environ if environ is None else environ
    name = _release_dir_name(code_path)
    if _RELEASE_NAME.fullmatch(name):
        return name[:SHORT_LENGTH].lower()
    value = environ.get(ENV_NAME, "")
    if _ENV_VALUE.fullmatch(value):
        return value[:SHORT_LENGTH].lower()
    return DEV_ID
