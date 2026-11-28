# SPDX-License-Identifier: AGPL-3.0-only
"""Real-browser check that a phone bottom sheet lifted over the on-screen keyboard keeps its own
surface below its bottom edge: the zone between the sheet and the keyboard (iOS leaves its
autofill bar transparent) shows the sheet, not the page behind, and adds no page size."""
import io

import pytest
from PIL import Image

from co_manager_browser_support import Rig, _open
from companion.test_browser_ux_helpers import UI_THEMES_EXPLICIT

pytestmark = pytest.mark.browser

PHONE = {"width": 390, "height": 844}
KEYBOARD_PX = 336

# The page's own dialogs: the frame sheets (rename, access, leave), the airline editor's sheets
# (compact and collection).
PAGES = (("owner", "/account"), ("admin", "/airlines/manage"), ("admin", "/fleet?frame={frame}"))

_OPEN_EACH = """(i) => {
  const dialogs = [...document.querySelectorAll('dialog.modal')];
  document.querySelectorAll('dialog.modal[open]').forEach((d) => d.close());
  if (i >= dialogs.length) { return null; }
  window.SkyPaneModal.open(dialogs[i], null);
  return {id: dialogs[i].id, classes: dialogs[i].className, count: dialogs.length};
}"""
# The same path modal.js listens to: the visual viewport shrinks and reports a resize.
_RAISE_KEYBOARD = """(px) => {
  const real = window.visualViewport;
  Object.defineProperty(real, 'height', {get: () => innerHeight - px, configurable: true});
  real.dispatchEvent(new Event('resize'));
}"""
_SIZE = "() => [document.documentElement.scrollWidth, document.documentElement.scrollHeight]"


def _rgb(page, x, y):
    png = page.screenshot(clip={"x": x, "y": y, "width": 1, "height": 1})
    return Image.open(io.BytesIO(png)).convert("RGB").getpixel((0, 0))


@pytest.fixture
def rig(app_server_in_process):
    return Rig(app_server_in_process)


@pytest.mark.parametrize("theme", UI_THEMES_EXPLICIT)
@pytest.mark.parametrize("who,path", PAGES)
def test_every_sheet_continues_its_surface_down_to_the_keyboard(
        new_context, rig, who, path, theme):
    context, page = _open(new_context, rig, who, path=path.format(frame=rig.seed.owned_id), lang="fr", theme=theme, viewport=PHONE)
    try:
        page.wait_for_function("document.readyState === 'complete'")
        total = page.evaluate(_OPEN_EACH, 0)["count"]
        assert total >= 1
        checked = 0
        for index in range(total):
            info = page.evaluate(_OPEN_EACH, index)
            page.wait_for_timeout(450)
            before = page.evaluate(_SIZE)
            page.evaluate(_RAISE_KEYBOARD, KEYBOARD_PX)
            page.wait_for_timeout(150)
            box = page.evaluate(
                """(id) => { const d = document.getElementById(id); const r = d.getBoundingClientRect();
                             return {open: d.open, bottom: r.bottom, vh: innerHeight,
                                     inset: d.style.getPropertyValue('--keyboard-inset')}; }""", info["id"])
            if not box["open"]:
                continue
            checked += 1
            assert box["inset"] == "%dpx" % KEYBOARD_PX and abs(box["bottom"] - (box["vh"] - KEYBOARD_PX)) <= 1, box
            ys = [int(box["bottom"]) + 4, int((box["bottom"] + box["vh"]) / 2), box["vh"] - 2]
            for y in ys:
                for x in (3, PHONE["width"] // 2, PHONE["width"] - 3):
                    hit = page.evaluate(
                        "([x, y, id]) => document.elementFromPoint(x, y) === document.getElementById(id)",
                        [x, y, info["id"]])
                    assert hit, (info, x, y, box)
            inside = _rgb(page, 3, int(box["bottom"]) - 8)
            below = _rgb(page, 3, int(box["vh"]) - 20)
            assert all(abs(a - b) <= 2 for a, b in zip(inside, below)), (info, inside, below)
            assert page.evaluate(_SIZE) == before, (info, before)
            page.evaluate(_RAISE_KEYBOARD, 0)
        assert checked >= 1
    finally:
        context.close()
