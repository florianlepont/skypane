# Runway images — drop-in asset contract

The Config page's runway picker shows each runway's number/heading in
large type unconditionally. Alongside it, it will also show a real
airport diagram or satellite excerpt for a given runway — but only once
you drop the matching image file into this directory. No code change and
no service restart are needed once you do.

## Exact filenames

Put exactly these three files in this directory (`companion/static/`):

- `companion/static/runway-3.png`
- `companion/static/runway-06-24.png`
- `companion/static/runway-02-20.png`

The filename is derived mechanically from `server/device_config.py`'s
`RUNWAYS` registry key, as `runway-{id}.png`. If a fourth runway is ever
added to that registry, its image filename is defined by this same rule
with no code change required.

## Format

PNG only. No other extension is looked for — if your source image is a
JPEG or anything else, convert it to PNG first.

## Content requirements

The image must be a real airport diagram or satellite excerpt, with
**that specific runway already highlighted in the image file itself**
(outline, color overlay, arrow/label — your choice). Nothing in the
application code draws a highlight; the highlighted image is the
deliverable.

## Absent files are fine

Any one of the three files may be absent. That runway's option then
renders its number/heading text only, with no image and no error.
Supplying one file affects only that runway — partial sets are fully
supported and are the phase's default shipped state.

## Sizing guidance (not a hard limit)

At desktop widths (≥960px) the Runway fieldset occupies one half of a
two-column layout alongside the Theme fieldset. Suggested width is
roughly 600-900px; the page's CSS scales anything down to fit
(`max-width: 100%`), so this is guidance, not a requirement.

## When it takes effect

The file is picked up on the very next `/config` page load. There is no
caching that would delay this, no service restart, and no code change —
availability is recomputed once per request.

## Deploying it

Committing the file(s) to this directory is what ships them to the VPS:
`deploy/deploy.sh` rsyncs `companion/` wholesale, with no PNG exclusion,
and there is no `*.png` rule in `.gitignore`.

## Access control

These images are served only to an already-logged-in companion session,
over `/runway-image/{id}.png` — not from the unauthenticated `/static/`
namespace the stylesheet uses. An unauthenticated request is redirected
to `/login`, exactly like every other data-bearing route on this site.
