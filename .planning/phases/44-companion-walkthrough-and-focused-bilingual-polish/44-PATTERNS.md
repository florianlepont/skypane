# Phase 44: Companion Walkthrough and Focused Bilingual Polish - Pattern Map

**Mapped:** 2026-09-30  
**Files classified:** 12 (2 evidence-first files; 10 conditional finding-owned files)  
**Analogs found:** 11 / 12

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|---|---|---|---|---|
| `.planning/phases/44-companion-walkthrough-and-focused-bilingual-polish/44-WALKTHROUGH.md` | evidence record | batch / review | `43-VERIFICATION.md`-style phase evidence; no page-specific equivalent | partial |
| `companion/test_browser_walkthrough.py` (new) | browser test | request-response / event-driven | `companion/test_browser_ux_01.py` | exact |
| `companion/test_browser_walkthrough.py` update fixture section | browser test | request-response / event-driven | `companion/test_browser_update.py` | exact |
| `companion/pages/<owning_page>.py` | page renderer | request-response / transform | `companion/pages/health_page.py` and `companion/pages/update_page.py` | role-match |
| `companion/pages/config_page.py` | page renderer + POST boundary | request-response / CRUD | `companion/test_browser_ux_01.py` settings flows | exact for a confirmed settings finding |
| `companion/ui_nav.py` | shared navigation component | request-response / transform | `companion/ui_nav.py::_nav_links()` | exact |
| `companion/ui_shell.py` | shared shell component | request-response / transform | `companion/ui_shell.py::page_shell()` | exact |
| `companion/static/style.css` | stylesheet | client-side responsive / event-driven | existing focus and narrow-width rules | exact |
| `companion/static/<page_feature>.js` | page-local client behaviour | event-driven | `companion/static/flight-rows.js` registration pattern through `ui_shell.py` | role-match |
| `companion/ui_base.py` + `companion/static_files.py` | static-script registry | request-response | existing `*_SCRIPT_SRC` / `*_SCRIPT_ROUTE` entries | exact |
| `companion/i18n_fr/<area>.py` | translation catalogue | transform | `companion/i18n.py::msg()` plus an existing area catalogue | exact |
| `companion/test_i18n.py` and owning served/browser test | test | request-response / event-driven | `test_i18n.py`, `test_browser_ux_01.py` | exact |

The product-fix files are deliberately conditional. The phase boundary requires a recorded walkthrough before selecting a defect; each `fix now` row must name exactly one owning seam. Do not pre-allocate speculative page, CSS, JavaScript, or translation changes.

## Pattern Assignments

### `44-WALKTHROUGH.md` (evidence record, batch/review)

**Analog:** Phase verification artifacts, with Phase 44's research-defined matrix as the required schema.

Create this before changing companion behaviour. Give every observation a reproducible record:

```markdown
| Fixture / revision | Journey | Route | Language | Viewport | Trigger | Observed result | Impact | Disposition | Owning seam | Regression |
|---|---|---|---:|---:|---|---|---|---|---|---|
```

Use the exact route set from the route table: `/`, `/display`, `/flights`, `/airlines`, `/health`, `/device`, and `/update`; record both `en` and `fr`, plus 1280, 390, and 360 px. Rows are evidence, not source-test assertions: the browser test proves the deterministic matrix can be exercised, while the document records the human product judgement and `keep` / `fix now` / `defer` disposition.

### `companion/test_browser_walkthrough.py` (browser test, request-response/event-driven)

**Analog:** `companion/test_browser_ux_01.py` (lines 1-30, 115-152, 549-627).

**Imports and module discipline:**

```python
import pytest

from companion.test_browser_ux_helpers import (
    VIEWPORT_DESKTOP, VIEWPORT_MIN_SUPPORTED, VIEWPORT_PHONE,
    _assert_hit_target, _assert_no_page_overflow, _login, seed_state_dir,
)

pytestmark = pytest.mark.browser

@pytest.fixture(scope="module")
def server(module_app_server_factory):
    return module_app_server_factory(seed=seed_state_dir, fake_providers=True)
```

Use a module-scoped fixture only for read-only matrix coverage. `test_browser_ux_01.py` documents this at lines 7-9 and implements it at lines 25-30. Any test that changes a setting must instead create a function-scoped `make_app_server(...)`, as lines 549-627 do, so persisted state cannot leak across tests or xdist workers.

**Real authentication and each route:**

```python
_login(page, server.base_url())
page.goto(server.base_url() + route)
page.wait_for_load_state("networkidle")
```

`_login()` drives the actual password form (helper lines 147-153); it is the only route into authenticated coverage. The dedicated test must use the guarded `new_context` fixture, never `browser.new_context()` directly, because the helper module's contract installs the loopback-only guard (lines 1-8).

**Responsive and interaction assertions:**

```python
context = new_context(viewport=VIEWPORT_MIN_SUPPORTED)
try:
    page = context.new_page()
    _login(page, base_url)
    page.goto(base_url + route)
    assert not _assert_no_page_overflow(
        page, route, expected_width=VIEWPORT_MIN_SUPPORTED["width"])
finally:
    context.close()
```

Use the named 1280/390/360 viewport constants from helper lines 45-63. `_assert_no_page_overflow()` measures resolved `documentElement.scrollWidth` versus `clientWidth` (lines 466-491); it does not inspect stylesheet text. For a confirmed changed control, use `_assert_hit_target()` (lines 1104-1119) and `_operate_with_keyboard()` (lines 821-875) rather than a source-level focus or size assertion.

### `companion/test_browser_walkthrough.py` Update route section (browser test, request-response/event-driven)

**Analog:** `companion/test_browser_update.py` (lines 1-12, 156-165, 325-390).

Keep Update's state fixture separate from the normal read-only fixture. `test_browser_update.py` uses a module-scoped, read-only update server for geometry and navigation and function-scoped servers for action flows. Its language/phone matrix parametrizes the viewport and language, logs in, visits each route, then measures rendered link widths and real hit targets. Copy that shape if the walkthrough needs an Update-specific smoke case; do not force update state into `seed_state_dir()`.

### `companion/pages/<owning_page>.py` (page renderer, request-response/transform)

**Analogs:** `companion/pages/health_page.py::render()` (line 1017) and `companion/pages/update_page.py::render()` (line 636).

**Page ownership rule:** a confirmed status-clarity defect belongs to the renderer that consumes its `PageContext`. Page modules declare English copy as stable messages at module scope, build escaped markup from context, and pass the completed page body to the shared shell. Do not reread storage from the renderer and do not reimplement a status indicator in navigation.

```python
TITLE = i18n.msg("health.<stable_slug>", "English source text")

def render(ctx):
    ctx = page_context.coerce(ctx)
    # build escaped page markup from ctx
    return ui_shell.page_shell(
        i18n.t(TITLE), active="health", body=body, ...)
```

The exact `active` key, script list, and context fields must match the chosen page's existing `render()` implementation. Treat the renderer's current method as the authoritative local pattern; this map does not authorize an across-page abstraction.

### `companion/pages/config_page.py` (settings page and POST boundary, request-response/CRUD)

**Analog:** `companion/test_browser_ux_01.py` lines 549-627.

When a confirmed Display or Device finding concerns saving, retain the physical form and dirty-bar flow:

```python
page.fill(field_selector, target)
_commit_field(page, field_selector)
_wait_for_bar(page)
_save_via_bar(page)
assert device_config.load_device_config(server.tmpdir)[key] == expected
```

The test analog proves the important contract: an edit reveals feedback, the existing save affordance produces a real navigation, and the new value reaches persisted configuration. Preserve rejected-save inline errors and the no-JS POST path; do not replace it with client-only feedback.

### `companion/ui_nav.py` (shared navigation component, request-response/transform)

**Analog:** `companion/ui_nav.py::_nav_links()` (lines 57-77) and `_nav_groups()` (lines 80-104).

For a confirmed cross-route orientation defect, change the shared navigation once. The renderer derives active state from the existing `NAV_TABS` table, translates labels at render time, and escapes both route and label:

```python
for route, label in NAV_TABS:
    slug = nav_slug(route)
    is_active = slug == active
    links.append((is_active, escape_html(route),
                  escape_html(i18n.t(label)), slug))
```

Do not copy navigation markup into seven pages or create a second route list in the walkthrough test.

### `companion/ui_shell.py` (shared shell component, request-response/transform)

**Analog:** `companion/ui_shell.py::page_shell()` (lines 280-300) and `_script_tags_html()` (lines 150-165).

Use the shell only for a genuinely cross-route concern such as document-level focus, flash placement, or a shared script registration. The shell preserves a first-focusable skip link, language on `<html>`, the common sidebar/mobile navigation, the flash slot, and the alert region (template lines 228-277).

```python
return page_shell(
    title, active, body, ui_theme="auto", flash=None, banner=None,
    health_alert=None, lang=None, device_config=None, scripts=(),
    refresh_token=None)
```

`scripts` must be a known source constant. `_script_tags_html()` rejects unknown entries and emits every script at most once in the established order; never inject a raw `<script>` tag from a page.

### `companion/static/style.css` (stylesheet, client-side responsive/event-driven)

**Analog:** rendered-style validation in `companion/test_browser_ux_helpers.py` lines 466-491, 946-999, and 1104-1119; structural checks in `companion/test_stylesheet_structure.py` lines 1-48 and 105-124.

Add only a localized rule for a confirmed layout, focus, or touch-target finding. Reuse existing custom properties and responsive breakpoints. Validate the browser's resolved overflow, hit testing, and focus behaviour in English and French at 360/390, rather than testing declarations or selectors directly. Keep the served stylesheet's two structural invariants:

```python
# test_stylesheet_structure.py
# one selector declaration per at-rule context
# no colour literal outside custom-property definitions
```

### `companion/static/<page_feature>.js`, `companion/ui_base.py`, and `companion/static_files.py` (page-local client behaviour and asset registry, event-driven/request-response)

**Analog:** existing static allowlist in `companion/static_files.py` lines 25-46 and 90-112; source constants in `companion/ui_base.py` lines 126-186; shell script validation at `ui_shell.py` lines 150-165.

Only add a script if the walkthrough proves a local interaction needs it and the no-JS server flow already remains functional. Register it through all three existing seams:

```python
# ui_base.py
FEATURE_SCRIPT_SRC = "/static/feature.js"

# static_files.py
FEATURE_SCRIPT_ROUTE = "/static/feature.js"
STATIC_ROUTES[FEATURE_SCRIPT_ROUTE] = StaticAsset(
    _FEATURE_JS_PATH, "text/javascript", _PUBLIC_NO_CACHE)

# ui_shell.py call site in the owning page
scripts=(FEATURE_SCRIPT_SRC,)
```

Also add the source constant to `SHELL_SCRIPT_ORDER`; otherwise `page_shell()` raises. Keep the asset public and exact-path allowlisted; no request-derived path joins are permitted (`static_files.py` lines 1-14).

### `companion/i18n.py`, `companion/i18n_fr/<area>.py`, and `companion/test_i18n.py` (translation catalogue, transform)

**Analog:** `companion/i18n.py` lines 46-65 and 83-102; `companion/test_i18n.py` lines 162-173 and 222-253.

Define English source copy with a stable area-qualified message ID at module scope and add its French value to the matching area catalogue:

```python
STATUS_COPY = i18n.msg("health.status_copy", "English source text")
# rendering code: escape_html(i18n.t(STATUS_COPY))

# companion/i18n_fr/health.py
BY_ID = {
    # ...
    "health.status_copy": "Texte source français",
}
```

Never use a user-facing plain string at render time or use English text as the translation key. The registry rejects malformed/duplicated IDs, and `test_i18n.py` checks French completeness, non-empty translations, and placeholder parity.

## Shared Patterns

### Authentication and browser isolation

**Sources:** `companion/test_browser_ux_helpers.py` lines 1-8 and 147-180; `companion/test_route_table.py` lines 72-125.

All seven walkthrough routes stay authenticated. Browser checks must drive the real login form and build contexts through the guarded fixture. A companion polish must not add an unauthenticated route or circumvent session handling.

### Bilingual delivery

**Sources:** `companion/i18n.py` lines 46-65 and 83-102; `companion/ui_nav.py` lines 57-77.

English is declared once through `i18n.msg()`, French resolves by stable ID, and dynamic output is escaped after translation. Test both languages at the rendered document level for every modified flow; catalogue tests alone cannot reveal French mobile wrapping or an inaccessible label.

### Responsive, keyboard, and touch proof

**Sources:** `companion/test_browser_ux_helpers.py` lines 45-63, 466-491, 821-875, and 1104-1119.

Use 1280, 390, and 360 px. Preserve existing 320 px assertions that already pass. Check a changed interactive surface through keyboard focus/action and resolved hit testing, not CSS source text or fixed screenshots.

### Settings feedback and no-JS floor

**Sources:** `companion/test_browser_ux_01.py` lines 549-627; `companion/test_browser_ux_helpers.py` lines 155-180 and 242-265.

Settings retain native forms, server validation, redirect/re-render feedback, and persisted read-back. A script may enhance a local interaction, but it cannot become the sole save path.

## No Analog Found

| File | Role | Data Flow | Reason |
|---|---|---|---|
| `44-WALKTHROUGH.md` | evidence record | batch / review | The repository has phase evidence, but no previous artifact with this exact seven-route bilingual usability matrix. Use the schema required by `44-RESEARCH.md`. |

## Metadata

**Analog search scope:** `companion/pages/`, `companion/ui_*.py`, `companion/static/`, `companion/i18n*`, and companion browser/served test modules.  
**Files scanned:** 18 primary implementation and test files.  
**Pattern extraction date:** 2026-09-30
