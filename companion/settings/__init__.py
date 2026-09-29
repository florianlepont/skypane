"""The Settings page's rendering, split one module per settings group
(theme/aspect, runway/LED, quiet hours, wake interval, calendar,
colour rules) plus a shared `form` module of field-error and
repopulation helpers every group uses.

The Settings page module (companion/pages/) imports and re-exports these
modules' names; render() and handle_post() stay there, since assembling
the groups into a page and validating a posted form are page-level
concerns, not any one group's own.

A group module never imports a page module. Group modules may import
each other (e.g. `calendar`/`rules` import `theme`'s chip/row builders)
as long as no cycle results — `theme` itself never imports
`calendar`/`rules`, so those two take theme-built row HTML as plain
parameters instead of building it themselves.
"""
