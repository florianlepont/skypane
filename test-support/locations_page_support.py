"""Opens the Locations page in a browser. The page has no address of its own
any more (GET /locations redirects to Fleet); it is only produced as the
answer to a refused add submission, so the helper submits a blank name from a
console page the way a form would and waits for that answer."""

_SUBMIT_BLANK_ADD = """() => {
  const token = document.querySelector('input[name="csrf_token"]').value;
  const form = document.createElement('form');
  form.method = 'post';
  form.action = '/locations/add';
  for (const [name, value] of [['csrf_token', token], ['name', ' ']]) {
    const input = document.createElement('input');
    input.type = 'hidden';
    input.name = name;
    input.value = value;
    form.appendChild(input);
  }
  document.body.appendChild(form);
  form.submit();
}"""


def open_locations_page(page, base_url):
    """Leave `page` on the Locations page as an administrator sees it after a
    refused submission (status 400)."""
    page.goto(base_url + "/fleet")
    page.locator("main").wait_for(state="visible")
    with page.expect_navigation():
        page.evaluate(_SUBMIT_BLANK_ADD)
    page.locator("#new-name").wait_for(state="visible")
    # The page change runs a cross-document view transition; until it ends,
    # hit-testing lands on the root element instead of the page controls.
    page.wait_for_function(
        "() => { const e = document.querySelector('#new-name');"
        " const r = e.getBoundingClientRect();"
        " return document.elementFromPoint(r.left + r.width / 2,"
        " r.top + r.height / 2) === e; }",
        timeout=10000)
