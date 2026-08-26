#!/usr/bin/env bash
# Ink Frame — machine-checked vendored-asset attribution completeness (D-14).
#
# Every non-markdown file under server/assets/ must be named, by filename,
# in at least one VENDOR.md under server/assets/ — and every font family
# present in server/assets/fonts/ must have its own vendored OFL licence
# text sitting alongside it. This is the check that would have caught the
# Inter-OFL.txt gap (04-03, L2) on the day it happened, rather than at the
# next manual audit.
#
# Usage:
#   scripts/check-attribution.sh
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${HERE}/.." && pwd)"
cd "${REPO_ROOT}"

ASSETS_DIR="server/assets"
FAILED=0

if [ ! -d "${ASSETS_DIR}" ]; then
    echo "ERROR: ${ASSETS_DIR} not found — run from the repository root or check the path." >&2
    exit 1
fi

echo "==> Enumerating VENDOR.md files under ${ASSETS_DIR}/"
VENDOR_FILES=()
while IFS= read -r -d '' f; do
    VENDOR_FILES+=("${f}")
done < <(find "${ASSETS_DIR}" -type f -iname 'VENDOR.md' -print0 | sort -z)

if [ "${#VENDOR_FILES[@]}" -eq 0 ]; then
    echo "FAIL: no VENDOR.md files found under ${ASSETS_DIR}/ — nothing to check attribution against."
    exit 1
fi

for f in "${VENDOR_FILES[@]}"; do
    echo "    - ${f}"
done

echo "==> Enumerating non-markdown asset files under ${ASSETS_DIR}/ (ignoring OS cruft)"
ASSET_FILES=()
while IFS= read -r -d '' f; do
    base="$(basename "${f}")"
    # Skip OS cruft and other non-asset noise that should never require
    # attribution (.DS_Store, hidden dotfiles).
    case "${base}" in
        .DS_Store|.*) continue ;;
    esac
    ASSET_FILES+=("${f}")
done < <(find "${ASSETS_DIR}" -type f ! -iname '*.md' -print0 | sort -z)

echo "    found ${#ASSET_FILES[@]} asset file(s)"

echo "==> Checking every asset file is named in some VENDOR.md"
UNATTRIBUTED=()
for f in "${ASSET_FILES[@]}"; do
    base="$(basename "${f}")"
    found=0
    for vendor in "${VENDOR_FILES[@]}"; do
        if grep -qF -- "${base}" "${vendor}"; then
            found=1
            break
        fi
    done
    if [ "${found}" -eq 0 ]; then
        UNATTRIBUTED+=("${f}")
    fi
done

if [ "${#UNATTRIBUTED[@]}" -gt 0 ]; then
    echo "FAIL: the following asset file(s) are not named in any VENDOR.md:"
    for f in "${UNATTRIBUTED[@]}"; do
        echo "    - ${f}"
    done
    FAILED=1
else
    echo "    OK: all ${#ASSET_FILES[@]} asset file(s) are named in a VENDOR.md"
fi

echo "==> Checking every font family in server/assets/fonts/ has a vendored OFL licence text"
# Bash 3.2 (macOS's shipped /bin/bash) has no associative arrays, so
# families are de-duplicated via a plain array + grep -qx rather than
# `declare -A`.
FONTS_DIR="${ASSETS_DIR}/fonts"
FAMILIES_SEEN=()
if [ -d "${FONTS_DIR}" ]; then
    while IFS= read -r -d '' f; do
        base="$(basename "${f}")"
        family="${base%%-*}"
        if [ -n "${family}" ]; then
            already=0
            for seen in "${FAMILIES_SEEN[@]:-}"; do
                [ "${seen}" = "${family}" ] && already=1 && break
            done
            [ "${already}" -eq 0 ] && FAMILIES_SEEN+=("${family}")
        fi
    done < <(find "${FONTS_DIR}" -maxdepth 1 -type f -iname '*.ttf' -print0)
fi

MISSING_LICENCE_FAMILIES=()
for family in "${FAMILIES_SEEN[@]:-}"; do
    [ -z "${family}" ] && continue
    licence_file="${FONTS_DIR}/${family}-OFL.txt"
    if [ ! -f "${licence_file}" ]; then
        MISSING_LICENCE_FAMILIES+=("${family}")
    fi
done

if [ "${#MISSING_LICENCE_FAMILIES[@]}" -gt 0 ]; then
    echo "FAIL: the following font family(ies) have no vendored *-OFL.txt licence text:"
    for family in "${MISSING_LICENCE_FAMILIES[@]}"; do
        echo "    - ${family} (expected ${FONTS_DIR}/${family}-OFL.txt)"
    done
    FAILED=1
else
    echo "    OK: all ${#FAMILIES_SEEN[@]} font family(ies) have a vendored *-OFL.txt licence text"
fi

echo "==> Summary"
if [ "${FAILED}" -ne 0 ]; then
    echo "FAIL: attribution check found gap(s) above."
    exit 1
fi

echo "PASS: ${#ASSET_FILES[@]} asset file(s) all attributed in ${#VENDOR_FILES[@]} VENDOR.md file(s); ${#FAMILIES_SEEN[@]} font family(ies) all have licence text."
exit 0
