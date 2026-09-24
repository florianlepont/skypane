#!/usr/bin/env bash
# SkyPane — render deploy/Caddyfile's two placeholder site blocks into a
# real Caddyfile using the operator's actual hostnames.
#
# Runs on the VPS as root, from deploy/activate.sh (Plan 37-06), which
# writes the result to /etc/caddy/Caddyfile.new before validating and
# swapping it in. deploy/provision.sh's first-run installer uses the same
# anchored substitution inline; this script is the one shared
# implementation both call, so the render logic exists in exactly one
# place (SEC-05, D-11).
#
# Usage:
#   deploy/render_caddyfile.sh <template> <public-host> <companion-host> > out
#
# <template>       path to deploy/Caddyfile (or a release copy of it)
# <public-host>    hostname the device reaches (e.g. 203-0-113-10.nip.io)
# <companion-host> hostname of the companion web interface
#
# Both hostnames must match ^[A-Za-z0-9.-]+$ — the same rule
# deploy/provision.sh already applies (T-37-11) — checked before anything
# is printed, so a bad argument produces empty stdout and a non-zero exit
# rather than a half-rendered file. This script never reads the
# operator's environment file directly: the caller is responsible for
# extracting and validating the two hostname values from it first
# (deploy/provision.sh:41-48 shows the pattern) and passing them here as
# plain arguments.
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

# Companion substitution runs first: its anchor line
# (^config-203-0-113-10\.nip\.io {) contains the device anchor
# (^203-0-113-10\.nip\.io {) as a substring, so applying the device
# substitution first would also match inside the still-unrendered
# companion line. Anchoring both patterns to column 0 (^) and to the
# literal " {" that opens a site block keeps each substitution scoped to
# its own line only.
sed -e "s/^config-203-0-113-10\.nip\.io {/${COMPANION_HOST} {/" \
    -e "s/^203-0-113-10\.nip\.io {/${PUBLIC_HOST} {/" \
    "${TEMPLATE}"
