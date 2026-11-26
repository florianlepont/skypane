"""The wait that makes the admin Components page ready to measure, shared by its browser tests."""
import animation_settle

__test__ = False

# The loading-spinner specimen runs a finite 8 s animation. It only turns the specimen, so it is
# finished by script instead of waited out; a finished animation leaves the element in the same
# state as one that ran to its end.
_FINISH_SPINNERS = """() => {
  for (const a of document.getAnimations()) {
    const t = a.effect && a.effect.target;
    if (t && t.closest && t.closest('.place-loading__spinner')
        && Number.isFinite(a.effect.getComputedTiming().endTime)) a.finish();
  }
}"""

# The save-bar specimens only get a box once the toast specimen's own 6 s timer has hidden it, so
# measuring them needs this explicit wait, not the length of the spinner.
_SAVE_BARS_SHOWN = """() => {
  const bars = [...document.querySelectorAll('.components-save-bar .dirty-bar')];
  return bars.length > 0 && bars.every((bar) => {
    const r = bar.getBoundingClientRect(); return r.width > 0 && r.height > 0; });
}"""


def wait_until_measurable(page):
    """Wait for the page to finish loading, its entrance animations to end and the save-bar
    specimens to be on screen, without waiting for the spinner specimen to finish by itself."""
    page.wait_for_function("() => document.readyState === 'complete'", timeout=10000)
    page.evaluate(_FINISH_SPINNERS)
    page.wait_for_function(animation_settle.SETTLED, timeout=10000)
    page.wait_for_function(_SAVE_BARS_SHOWN, timeout=15000)
    page.wait_for_function(animation_settle.SETTLED, timeout=10000)
