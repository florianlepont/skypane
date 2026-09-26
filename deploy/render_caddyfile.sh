#!/usr/bin/env bash
# SkyPane — render deploy/Caddyfile's two placeholder site blocks with
# the operator's actual hostnames.
#
# Output is not a whole Caddyfile: it is the snippet installed as
# /etc/caddy/sites/skypane.caddy, imported by the host's shared
# /etc/caddy/Caddyfile (`import sites/*.caddy`) — site blocks only, no
# global options block (legal only at the top of the host file).

# Usage: deploy/render_caddyfile.sh <template> <public-host> <companion-host> > out
#   <public-host>    hostname the device reaches (e.g. 203-0-113-10.nip.io)
#   <companion-host> hostname of the companion web interface
set -euo pipefail

TEMPLATE="${1:-}"
PUBLIC_HOST="${2:-}"
COMPANION_HOST="${3:-}"

if [ -z "${TEMPLATE}" ] || [ -z "${PUBLIC_HOST}" ] || [ -z "${COMPANION_HOST}" ]; then
    echo "render_caddyfile.sh: usage: render_caddyfile.sh <template> <public-host> <companion-host>" >&2
    exit 1
fi

if ! [[ "${PUBLIC_HOST}" =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "render_caddyfile.sh: invalid public host '${PUBLIC_HOST}' (letters, digits, dots and dashes only)" >&2
    exit 1
fi

if ! [[ "${COMPANION_HOST}" =~ ^[A-Za-z0-9.-]+$ ]]; then
    echo "render_caddyfile.sh: invalid companion host '${COMPANION_HOST}' (letters, digits, dots and dashes only)" >&2
    exit 1
fi

if [ ! -f "${TEMPLATE}" ]; then
    echo "render_caddyfile.sh: template not found: ${TEMPLATE}" >&2
    exit 1
fi

# Companion substitution runs first: its anchor line contains the device
# anchor as a substring, so substituting the device first would also
# match inside the still-unrendered companion line. Anchoring both to
# column 0 and the literal " {" keeps each substitution scoped to its own line.
sed -e "s/^config-203-0-113-10\.nip\.io {/${COMPANION_HOST} {/" \
    -e "s/^203-0-113-10\.nip\.io {/${PUBLIC_HOST} {/" \
    "${TEMPLATE}"
