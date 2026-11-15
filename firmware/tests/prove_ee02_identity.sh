#!/bin/sh
# SPDX-FileCopyrightText: 2026 Florian Lepont
# SPDX-License-Identifier: Apache-2.0
#
# Proves the live frame's (EE02) production firmware image is unchanged
# between a baseline commit and the current HEAD. Needs Docker and takes
# minutes (two full ESP-IDF builds), so it is NOT part of
# run_host_tests.sh: an owner runs it by hand before a release.
#
# Usage: ./prove_ee02_identity.sh [--keep] [BASELINE_REF]
#        ./prove_ee02_identity.sh --dry-run [BASELINE_REF]   (print the plan)
#        ./prove_ee02_identity.sh --help
#
# What it does:
#   1. creates two throwaway git worktrees (baseline, HEAD) under mktemp;
#   2. builds the EE02 production profile in each with firmware/build.sh
#      (SKYPANE_BOARD=ee02, SKYPANE_PROFILE=prod);
#   3. compares, in the espressif/idf:v5.3.1 container: the resolved
#      sdkconfig, `size -A`, `nm -n`, and the four sections .flash.text,
#      .iram0.text, .dram0.data, .flash.rodata dumped with objcopy byte for
#      byte; checks that the current image has no epd7in3e / 800x480 symbol;
#   4. runs check_production_config.sh built on the current build.
#
# Known, explicitly reported differences (never silently ignored):
#   VERSION  the embedded version string: build.sh passes
#            `git describe` as PROJECT_VER, which differs between the two
#            commits. Occurrences are masked and reported separately; the
#            verdict can still be IDENTICAL when this is the only difference.
#   LINE     digits after "<file>.c:" in assert/log text: ESP-IDF embeds
#            __LINE__, so an edit that moves a line above an assert changes
#            them. Reported separately but it makes the verdict DIFFERENT:
#            the code that takes the line as an immediate differs too, and
#            only a line-neutral rebuild can prove the image unchanged.
#   REAL     any other differing byte, with its symbol and offset.
#
# Output ends with one verdict line, IDENTICAL or DIFFERENT. Exit status:
# 0 identical, 1 different, 2 usage or environment error (no verdict).

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
DEFAULT_BASELINE=7137a0935
IMAGE="espressif/idf:v5.3.1"
BUILD_SUBDIR="build-ee02"

usage() {
    cat <<EOF
Usage: $0 [--keep] [BASELINE_REF]
       $0 --dry-run [BASELINE_REF]
       $0 --help

Proves the EE02 production image built from HEAD is unchanged against
BASELINE_REF (default ${DEFAULT_BASELINE}, the commit just before the first
Phase 64 firmware change). Needs Docker; takes minutes.

  --dry-run  print the plan and exit 0 without Docker, worktrees or builds
  --keep     keep the temporary worktrees and build output on exit
  --help     this text

Exit status: 0 IDENTICAL, 1 DIFFERENT, 2 usage or environment error.
Only commits are compared: uncommitted changes in the working tree are
not part of HEAD and are not built.
EOF
}

DRY_RUN=0
KEEP=0
BASELINE_REF=""
while [ $# -gt 0 ]; do
    case "$1" in
        --help|-h) usage; exit 0 ;;
        --dry-run) DRY_RUN=1 ;;
        --keep) KEEP=1 ;;
        -*) echo "ERROR: unknown option '$1'" >&2; usage >&2; exit 2 ;;
        *)
            if [ -n "${BASELINE_REF}" ]; then
                echo "ERROR: more than one baseline ref given" >&2
                exit 2
            fi
            BASELINE_REF="$1"
            ;;
    esac
    shift
done
[ -n "${BASELINE_REF}" ] || BASELINE_REF="${DEFAULT_BASELINE}"

REPO_ROOT=$(git -C "${SCRIPT_DIR}" rev-parse --show-toplevel 2>/dev/null) || {
    echo "ERROR: not inside a git checkout" >&2
    exit 2
}

BASE_SHA=$(git -C "${REPO_ROOT}" rev-parse --verify --quiet "${BASELINE_REF}^{commit}") || {
    echo "ERROR: baseline '${BASELINE_REF}' is not a commit in this repository" >&2
    exit 2
}
HEAD_SHA=$(git -C "${REPO_ROOT}" rev-parse --verify HEAD)

if [ "${BASE_SHA}" = "${HEAD_SHA}" ]; then
    echo "ERROR: baseline and HEAD are the same commit; nothing to compare" >&2
    exit 2
fi

if [ "${DRY_RUN}" -eq 1 ]; then
    cat <<EOF
Plan (dry run, nothing is executed):
  baseline : ${BASELINE_REF} -> ${BASE_SHA}
  current  : HEAD -> ${HEAD_SHA}
  1. mktemp directory outside the repository, two detached git worktrees
     (base, cur) removed again on exit
  2. SKYPANE_BOARD=ee02 SKYPANE_PROFILE=prod firmware/build.sh in each
     worktree (container ${IMAGE}), output firmware/${BUILD_SUBDIR}
  3. host: diff of the resolved sdkconfig (differing lines are listed)
  4. in ${IMAGE}: size -A, nm -n, and objcopy dumps of .flash.text,
     .iram0.text, .dram0.data, .flash.rodata compared byte for byte;
     version string occurrences masked and reported as VERSION, line
     numbers in assert text reported as LINE, anything else as REAL
  5. no epd7in3e / 800x480 symbol in the current image
  6. sh firmware/tests/check_production_config.sh built <cur build dir> ee02
  7. verdict line IDENTICAL or DIFFERENT; exit 0 only when IDENTICAL
Firmware files changed between the two commits:
EOF
    git -C "${REPO_ROOT}" diff --stat "${BASE_SHA}" "${HEAD_SHA}" -- firmware \
        | sed 's/^/  /'
    exit 0
fi

command -v docker >/dev/null 2>&1 || {
    echo "ERROR: docker is required (builds and comparison run in ${IMAGE})" >&2
    exit 2
}
docker info >/dev/null 2>&1 || {
    echo "ERROR: the Docker daemon is not reachable" >&2
    exit 2
}

WORK=$(mktemp -d "${TMPDIR:-/tmp}/skypane-ee02-identity.XXXXXX")
BASE_WT="${WORK}/base"
CUR_WT="${WORK}/cur"

cleanup() {
    status=$?
    if [ "${KEEP}" -eq 1 ]; then
        echo "kept: ${WORK} (remove worktrees with: git worktree remove --force)" >&2
    else
        for wt in "${BASE_WT}" "${CUR_WT}"; do
            [ -e "${wt}" ] && git -C "${REPO_ROOT}" worktree remove --force "${wt}" 2>/dev/null
        done
        git -C "${REPO_ROOT}" worktree prune 2>/dev/null
        rm -rf "${WORK}"
    fi
    exit "${status}"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

echo "== worktrees under ${WORK} =="
git -C "${REPO_ROOT}" worktree add --detach "${BASE_WT}" "${BASE_SHA}" >/dev/null
git -C "${REPO_ROOT}" worktree add --detach "${CUR_WT}" "${HEAD_SHA}" >/dev/null

build_one() {
    label="$1"
    wt="$2"
    log="${WORK}/build-${label}.log"
    echo "== building EE02 production image (${label}) ==" >&2
    if ! env -u SKYPANE_FAULT -u SKYPANE_BENCH_FLOOR -u SKYPANE_RELEASE_TAG \
        -u SKYPANE_VERSION_LABEL SKYPANE_PROFILE=prod SKYPANE_BOARD=ee02 \
        sh "${wt}/firmware/build.sh" >"${log}" 2>&1; then
        echo "ERROR: ${label} build failed; last lines of the log:" >&2
        tail -n 30 "${log}" >&2
        exit 2
    fi
    if [ ! -f "${wt}/firmware/${BUILD_SUBDIR}/skypane.elf" ]; then
        echo "ERROR: ${label} build produced no skypane.elf" >&2
        exit 2
    fi
    sed -n 's/^Firmware version: //p' "${log}" | head -n 1
}

VER_BASE=$(build_one baseline "${BASE_WT}")
VER_CUR=$(build_one current "${CUR_WT}")
# The two builds must have been the production EE02 profile; the log says so.
echo "baseline version string: ${VER_BASE}"
echo "current  version string: ${VER_CUR}"

FAILED_ITEMS="${WORK}/failed-items"
NOTES="${WORK}/notes"
: >"${FAILED_ITEMS}"
: >"${NOTES}"

item_failed() {
    printf '%s\n' "$1" >>"${FAILED_ITEMS}"
    echo "DIFF: $1"
}

echo "== resolved sdkconfig =="
if diff "${BASE_WT}/firmware/${BUILD_SUBDIR}/sdkconfig" \
    "${CUR_WT}/firmware/${BUILD_SUBDIR}/sdkconfig" >"${WORK}/sdkconfig.diff"; then
    echo "OK: sdkconfig identical"
else
    cat "${WORK}/sdkconfig.diff"
    item_failed "sdkconfig: $(grep -c '^[<>]' "${WORK}/sdkconfig.diff") differing line(s)"
fi

# Container-side comparison script: size, nm, four sections, symbols.
cat >"${WORK}/compare.py" <<'PYEOF'
import bisect
import difflib
import os
import re
import subprocess
import sys
import tempfile

P = "xtensa-esp32s3-elf-"
elf_a, elf_b, ver_a, ver_b = sys.argv[1:5]
SECTIONS = [".flash.text", ".iram0.text", ".dram0.data", ".flash.rodata"]
MAX_SHOWN = 15


def tool(name, *args):
    return subprocess.run([P + name, *args], check=True, capture_output=True).stdout


def emit(kind, msg):
    print(f"{kind}: {msg}")


def unified(a_lines, b_lines, limit=40):
    out = list(difflib.unified_diff(a_lines, b_lines, "baseline", "current", lineterm="", n=0))
    for line in out[:limit]:
        print("    " + line)
    if len(out) > limit:
        print(f"    ... {len(out) - limit} more diff line(s)")


# size -A: the first line carries the file name, which differs by design.
size_a = tool("size", "-A", elf_a).decode().splitlines()[1:]
size_b = tool("size", "-A", elf_b).decode().splitlines()[1:]
if size_a == size_b:
    emit("OK", "size -A identical")
else:
    emit("DIFF", "size -A differs")
    unified(size_a, size_b)

nm_a = tool("nm", "-n", elf_a).decode().splitlines()
nm_b = tool("nm", "-n", elf_b).decode().splitlines()
if nm_a == nm_b:
    emit("OK", f"nm -n identical ({len(nm_a)} symbols)")
else:
    emit("DIFF", "nm -n symbol lists differ")
    unified(nm_a, nm_b)

# Symbol table of the baseline, for attributing differing offsets.
syms = []
for line in nm_a:
    parts = line.split(None, 2)
    if len(parts) == 3 and re.fullmatch(r"[0-9a-fA-F]+", parts[0]):
        syms.append((int(parts[0], 16), parts[2]))
sym_addrs = [s[0] for s in syms]

vma = {}
for line in tool("objdump", "-h", elf_a).decode().splitlines():
    m = re.match(r"\s*\d+\s+(\S+)\s+([0-9a-f]+)\s+([0-9a-f]+)\s", line)
    if m:
        vma[m.group(1)] = int(m.group(3), 16)


def dump(elf, section):
    with tempfile.TemporaryDirectory() as d:
        out = os.path.join(d, "s.bin")
        tool("objcopy", "-O", "binary", "--only-section=" + section, elf, out)
        with open(out, "rb") as f:
            return f.read()


def mask_version(data, ver):
    if not ver:
        return data, []
    needle = ver.encode()
    offsets = []
    start = 0
    while True:
        i = data.find(needle, start)
        if i < 0:
            break
        offsets.append(i)
        start = i + len(needle)
    return data.replace(needle, b"\0" * len(needle)), offsets


def digit_run(buf, i):
    """Digit run containing index i, if it is the number in 'file.c:NNN'."""
    if not (0 <= i < len(buf)) or not (48 <= buf[i] <= 57):
        return None
    lo = i
    while lo > 0 and 48 <= buf[lo - 1] <= 57:
        lo -= 1
    if lo < 3 or buf[lo - 1:lo] != b":" or buf[lo - 3:lo - 1] not in (b".c", b".h"):
        return None
    hi = i
    while hi + 1 < len(buf) and 48 <= buf[hi + 1] <= 57:
        hi += 1
    return lo, hi


def context(buf, lo, hi):
    start = max(0, lo - 40)
    end = min(len(buf), hi + 12)
    return re.sub(rb"[^\x20-\x7e]", b".", buf[start:end]).decode()


def attribute(section, off):
    addr = vma.get(section, 0) + off
    i = bisect.bisect_right(sym_addrs, addr) - 1
    if i < 0:
        return f"0x{addr:08x}"
    return f"{syms[i][1]}+0x{addr - syms[i][0]:x} (0x{addr:08x})"


def compare_section(section):
    a = dump(elf_a, section)
    b = dump(elf_b, section)
    if not a and not b:
        emit("DIFF", f"{section}: empty or missing in both images, nothing proven")
        return
    if len(a) != len(b):
        emit("DIFF", f"{section}: size differs ({len(a)} vs {len(b)} bytes)")
        return
    if a == b:
        emit("OK", f"{section}: {len(a)} bytes identical")
        return
    ma, offs_a = mask_version(a, ver_a)
    mb, offs_b = mask_version(b, ver_b)
    if ma == mb:
        emit("VERSION", f"{section}: {len(a)} bytes, differs only in the version "
             f"string ('{ver_a}' vs '{ver_b}'; {len(offs_a)} and {len(offs_b)} "
             f"occurrence(s) at offsets {offs_a} / {offs_b})")
        return
    diff_offs = [i for i in range(len(ma)) if ma[i] != mb[i]]
    ranges = []
    for i in diff_offs:
        if ranges and i - ranges[-1][1] <= 8:
            ranges[-1][1] = i
        else:
            ranges.append([i, i])
    lines, reals = [], []
    for lo, hi in ranges:
        run_a = {digit_run(ma, i) for i in range(lo, hi + 1) if ma[i] != mb[i]}
        run_b = {digit_run(mb, i) for i in range(lo, hi + 1) if ma[i] != mb[i]}
        if None not in run_a and None not in run_b:
            lines.append((lo, hi))
        else:
            reals.append((lo, hi))
    if offs_a or offs_b:
        emit("VERSION", f"{section}: version string present ({len(offs_a)}/{len(offs_b)} "
             "occurrence(s)), masked before the comparison below")
    if lines:
        emit("LINE", f"{section}: {len(lines)} range(s) differ only in the line number of "
             "assert/log text (__LINE__)")
        for lo, hi in lines[:MAX_SHOWN]:
            print(f"    @0x{lo:x}  baseline: ...{context(ma, lo, hi)}")
            print(f"    @0x{lo:x}  current : ...{context(mb, lo, hi)}")
    if reals:
        emit("REAL", f"{section}: {len(reals)} range(s) differ, {len(diff_offs)} byte(s) in total "
             "(not version string, not assert line numbers)")
        for lo, hi in reals[:MAX_SHOWN]:
            print(f"    @0x{lo:x}..0x{hi:x} in {attribute(section, lo)}: "
                  f"baseline {a[lo:hi + 1][:16].hex()} vs current {b[lo:hi + 1][:16].hex()}")
        if len(reals) > MAX_SHOWN:
            print(f"    ... {len(reals) - MAX_SHOWN} more range(s)")


for section in SECTIONS:
    compare_section(section)

# The current image must carry no 7.3 inch driver or 800x480 mask symbol.
bad = [line for line in nm_b if re.search(r"epd7in3e|epd7|800x480|7in3", line, re.I)]
if bad:
    emit("DIFF", "current image has 7.3 inch / 800x480 symbol(s)")
    for line in bad[:MAX_SHOWN]:
        print("    " + line)
else:
    emit("OK", "no epd7in3e / 800x480 symbol in the current image")
PYEOF

echo "== size, nm, sections, symbols (in ${IMAGE}) =="
CMP_OUT="${WORK}/compare.out"
if ! docker run --rm \
    -v "${WORK}:/work" \
    -w /work \
    -u "$(id -u):$(id -g)" \
    -e HOME=/tmp \
    "${IMAGE}" \
    python3 -I /work/compare.py \
        "/work/base/firmware/${BUILD_SUBDIR}/skypane.elf" \
        "/work/cur/firmware/${BUILD_SUBDIR}/skypane.elf" \
        "${VER_BASE}" "${VER_CUR}" >"${CMP_OUT}" 2>"${WORK}/compare.err"; then
    cat "${WORK}/compare.err" >&2
    echo "ERROR: the container comparison failed to run" >&2
    exit 2
fi
cat "${CMP_OUT}"

echo "== check_production_config.sh built (current, ee02) =="
if sh "${CUR_WT}/firmware/tests/check_production_config.sh" built \
    "${CUR_WT}/firmware/${BUILD_SUBDIR}" ee02; then
    echo "OK: check_production_config.sh built passed"
else
    item_failed "check_production_config.sh built ee02 failed on the current build"
fi

# Items that make the verdict DIFFERENT: every DIFF, LINE and REAL line.
# VERSION lines are reported, never counted, and never hidden.
grep -E '^(DIFF|LINE|REAL):' "${CMP_OUT}" >>"${FAILED_ITEMS}" || true
grep -E '^VERSION:' "${CMP_OUT}" >"${NOTES}" || true

echo "== summary =="
if [ -s "${NOTES}" ]; then
    echo "Version-string-only differences (expected, reported):"
    sed 's/^/  /' "${NOTES}"
fi
if [ -s "${FAILED_ITEMS}" ]; then
    echo "Differing items:"
    sed 's/^/  /' "${FAILED_ITEMS}"
    echo "Source files changed between the commits (firmware/main):"
    git -C "${REPO_ROOT}" diff --stat "${BASE_SHA}" "${HEAD_SHA}" -- firmware/main \
        | sed 's/^/  /'
    echo "DIFFERENT: EE02 production image differs between ${BASE_SHA} and ${HEAD_SHA} ($(wc -l <"${FAILED_ITEMS}" | tr -d ' ') item(s))"
    exit 1
fi
echo "IDENTICAL: EE02 production image unchanged between ${BASE_SHA} and ${HEAD_SHA} (version string aside)"
exit 0
