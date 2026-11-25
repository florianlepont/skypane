# Quick 261125-fam: Summary

Type rows of /airlines/manage are labelled with the aircraft family name. Codes: tooltip (hover and
keyboard focus, table layout) or two-line secondary line with tap-to-expand (card layout). The
default type is a text-free star with an accessible name and its own tooltip. "(famille)" and
"family" suffixes are gone from every family label; the add dialog chip of a type row names the
family too.

Deviations from the mockup: see the final report of the run (phone card shows no "N vues" in the
state line, as before; a slot with no family name keeps its designator label and has no tooltip).

Verification: the airline editor test files, `companion -m "not browser"`, the structure, i18n and
render baseline guards pass; ruff, mypy, function-size and comment-history gates pass.
