# Ledger: companion/test_contrast_check.py

Baseline: `companion__test_contrast_check.txt`, 49 checks

| # | Old check label | Disposition | New node id / reason |
| --- | --- | --- | --- |
| 1 | contrast_ratio('#E8622C', '#FBF9F6') reproduces the audit's published 3.22 | pending | |
| 2 | contrast_ratio('#E8622C', '#F3EEE7') reproduces the audit's published 2.93 | pending | |
| 3 | contrast_ratio('#D2521F', '#FBF9F6') reproduces the audit's published 4.02 | pending | |
| 4 | contrast_ratio('#FF8A5C', '#0D0F14') reproduces the audit's published 8.25 | pending | |
| 5 | contrast_ratio('B13F16', 'FFFFFF') reproduces the audit's published 5.85 | pending | |
| 6 | contrast_ratio('#B13F16', '#F7F4EF') reproduces the audit's published 5.33 | pending | |
| 7 | contrast_ratio('#B13F16', '#EEE8DE') reproduces the audit's published 4.80 | pending | |
| 8 | contrast_ratio('#FF9B73', '#0C0F14') reproduces the audit's published 9.31 | pending | |
| 9 | light: accent text/link on canvas meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 10 | light: accent on primary surface / active nav meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 11 | light: accent on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 12 | light: primary-button label on accent fill meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 13 | light: body text on canvas meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 14 | light: body text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 15 | dark: accent text/link on canvas meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 16 | dark: accent on primary surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 17 | dark: accent on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 18 | dark: primary-button label on accent fill meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 19 | dark: body text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 20 | light: muted detail text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 21 | dark: muted detail text on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 22 | light: body text on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 23 | dark: body text on secondary/sidebar surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 24 | light: --color-accent is perceptually separated from --color-status-ok (dE76 >= 28) | pending | |
| 25 | light: --color-accent is perceptually separated from --color-status-warn (dE76 >= 28) | pending | |
| 26 | light: --color-accent is perceptually separated from --color-status-error (dE76 >= 28) | pending | |
| 27 | dark: --color-accent is perceptually separated from --color-status-ok (dE76 >= 28) | pending | |
| 28 | dark: --color-accent is perceptually separated from --color-status-warn (dE76 >= 28) | pending | |
| 29 | dark: --color-accent is perceptually separated from --color-status-error (dE76 >= 28) | pending | |
| 30 | light: --color-status-ok and --color-status-warn are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | pending | |
| 31 | light: --color-status-ok and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | pending | |
| 32 | light: --color-status-warn and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | pending | |
| 33 | dark: --color-status-ok and --color-status-warn are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | pending | |
| 34 | dark: --color-status-ok and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | pending | |
| 35 | dark: --color-status-warn and --color-status-error are perceptually separated (dE76 >= 28) — the regularity grid paints them as adjacent cells with nothing but colour between them | pending | |
| 36 | light: --color-accent and --color-status-error are hue-separated (>= 24 deg) | pending | |
| 37 | dark: --color-accent and --color-status-error are hue-separated (>= 24 deg) | pending | |
| 38 | light: the dE76 floor rejects the superseded error colour #DC2626 (guard against a decorative threshold) | pending | |
| 39 | light: the hue floor rejects the superseded error colour #DC2626 (guard against a decorative threshold) | pending | |
| 40 | dark: the dE76 floor rejects the superseded error colour #F87171 (guard against a decorative threshold) | pending | |
| 41 | dark: the hue floor rejects the superseded error colour #F87171 (guard against a decorative threshold) | pending | |
| 42 | light: --color-status-error meets WCAG AA UI-component contrast (>= 3:1) on every light surface | pending | |
| 43 | dark: --color-status-error meets WCAG AA UI-component contrast (>= 3:1) on every dark surface | pending | |
| 44 | hue_separation() takes the shorter arc, including across the 0/360 wrap point | pending | |
| 45 | dark: warn-coloured headline on card surface meets WCAG AA normal-text contrast (>= 4.5:1) | pending | |
| 46 | light: warn-coloured headline on card surface correctly falls below WCAG AA normal-text contrast, confirming style.css's non-colour status-warn fallback is required | pending | |
| 47 | the status-warn-on-card pair is present in contrast_check.STATUS_WARN_ON_CARD_PAIRS for both themes | pending | |
| 48 | light: the login field's error border (--color-status-error) meets WCAG AA UI-component contrast (>= 3:1) against BOTH colours adjacent to it — the field's own fill and the login card's surface | pending | |
| 49 | dark: the login field's error border (--color-status-error) meets WCAG AA UI-component contrast (>= 3:1) against BOTH colours adjacent to it — the field's own fill and the login card's surface | pending | |

