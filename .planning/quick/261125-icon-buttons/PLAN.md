# Quick 261125-ico: Icon-only add and change picture buttons

The airline editor's "Ajouter une illustration" / "Changer l'illustration" text buttons and the
"+ Illustration" button of the missing illustrations rows become 44px icon buttons. Follows the
approved mockup (variant A, tooltip only).

Owner decisions (2026-11-25):
1. Add = a picture with a plus badge, change = a picture with a pencil badge, same outlined 44px
   rounded square as one family; the "..." menu is unchanged.
2. Name: `aria-label` "Add an illustration for <airline>, <family>" / "Change the artwork of
   <airline>, <family>" (a visually hidden label for the file-input control). Tooltip (the action
   name) on hover and keyboard focus. No first-use label.
3. A card puts the button to the right of the thumbnail block (menu under it), so a card without
   a picture is shorter. The missing illustrations rows use the add button.

## Tasks
1. Two sprite glyphs (`icon-picture-add`, `icon-picture-edit`), markup in `airline_table` and
   `airline_missing`, CSS in `style-airlines.css`, French catalogue.
2. Served-HTML tests, a Playwright test (44px, tooltip on hover and focus, aria-label, shorter card).
3. Design-system skill page patterns; regenerate `companion/testdata/render_baseline.json`.
