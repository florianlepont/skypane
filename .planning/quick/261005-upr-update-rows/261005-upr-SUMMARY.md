---
quick_id: 261005-upr
status: complete
---

# 261005-upr summary

- The Update page is now one call-to-action card plus one "Versions" card. The card says "Le cadre
  est à jour" (running version + relative install time), "Mise à jour disponible" (the newest
  installable newer release, its first note, the one accent Install button, and an "On the frame"
  footer), or the schedule in flight (planifiée with a quiet Cancel, installation en cours, échec
  with a retry). The list shows every release as a native `<details>` row: version, running badge,
  first note on one ellipsised line, one relative date (`<time data-relative title=absolute>`),
  trailing chevron. Opening a row lists every note, the absolute "Sortie le / Installée le /
  Dernière installation" dates (plain `<time>`, never ticking) and the action. Works with scripts
  blocked.
- Wording and colour: a newer release is "Installer" on the accent primary button; an older one is
  "Revenir à fw-vX.Y.Z" on the quiet secondary button (`calendar-disconnect-btn`). The direction
  comes from `update_view()` (`direction` per release). The confirmation flow, `data-confirm`, the
  hidden `version` field and the server confirmation page are unchanged. No "last contact" line.
- Release notes cleaned at the source: `scripts/fw_release_manifest.py` `clean_note()` /
  `clean_notes()` (pure, deterministic, unit-tested). The notes are not part of the signed payload
  (the signature covers the `.bin`; the registry checks the image's sha256 and size), so signing,
  the manifest identity fields, version numbers and OTA verification are untouched. Releases already
  published keep their old notes (nothing is rewritten or re-published); the page shows them as
  stored. Cleaning is applied from the next tagged release.
- CSS: `.update-cta*`, `.update-row*`, `.update-actions` added; the old firmware table, cards and
  notes rules removed. No new custom property, colour literal, size or accent consumer.
- Tests rewritten to the served HTML and a browser (360/390/700/1024/1280, EN/FR, 12 releases, unbroken
  tokens, 44 px targets, scripts blocked, accent exclusivity).
- Render baseline regenerated; a page-level diff against `origin/main` shows only the four Update
  entries (EN/FR x light/dark) changed.
