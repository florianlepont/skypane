"""Shared selectors and waits for tests of the frame button and its popover."""

MENU = "details.frame-menu"
BUTTON = MENU + " > summary.frame-menu__button"
PANEL = MENU + " .frame-menu__panel"
LIST = MENU + " ul.frame-menu__list"
ROW = LIST + " a.frame-row"
FRAMES = ROW + ":not(.frame-row--add):not(.frame-row--system)"
ADD = LIST + " a.frame-row--add"
SYSTEM = LIST + " a.frame-row--system"

# Finished loading, every finite animation over and the button owns its own
# centre (a cross-document view transition leaves the root answering hit tests).
BUTTON_READY = """(sel) => {
  if (document.readyState !== 'complete') return false;
  if (!document.getAnimations().every((a) => a.playState !== 'running'
      || a.effect.getComputedTiming().iterations === Infinity)) return false;
  const el = document.querySelector(sel);
  if (!el) return true;
  const box = el.getBoundingClientRect();
  const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
  return !!hit && el.contains(hit);
}"""

MENU_IS_OPEN = "() => document.querySelector('details.frame-menu').open"
MENU_IS_CLOSED = "() => !document.querySelector('details.frame-menu').open"
# The popover's first row owns its centre and no entrance animation is running.
ROWS_SETTLED = """() => {
  const menu = document.querySelector('details.frame-menu');
  if (!menu || !menu.open) return false;
  if (!document.getAnimations().every((a) => a.playState !== 'running'
      || a.effect.getComputedTiming().iterations === Infinity)) return false;
  const row = menu.querySelector('a.frame-row');
  const box = row.getBoundingClientRect();
  const hit = document.elementFromPoint(box.x + box.width / 2, box.y + box.height / 2);
  return !!hit && row.contains(hit);
}"""


def wait_for_button(page):
    page.locator(BUTTON).wait_for(state="visible")
    page.wait_for_function(BUTTON_READY, arg=BUTTON)


def open_menu(page):
    """Click the frame button and wait until the popover is open and settled."""
    wait_for_button(page)
    page.locator(BUTTON).click()
    page.wait_for_function(ROWS_SETTLED)


def close_menu_with_escape(page):
    page.keyboard.press("Escape")
    page.wait_for_function(MENU_IS_CLOSED)


def click_add(page):
    """Open the popover and choose its Add a frame row."""
    open_menu(page)
    page.locator(ADD).click()


def click_add_without_script(page):
    """Open the native disclosure and follow the Add a frame row (no waits that
    need page script)."""
    page.locator(BUTTON).click()
    page.locator(ADD).click()
