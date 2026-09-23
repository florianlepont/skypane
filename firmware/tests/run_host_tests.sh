#!/bin/sh
# Compiles and runs every hardware-free firmware test with the system `cc`,
# discovered by naming convention (test_<name>.c -> main/<name>.c) so a new
# suite needs no edit here - just drop the file in.
#
# A test source that needs more than its one matching main/<name>.c file may
# declare `/* HOST_TEST_DEPS: other.c another.c */` on one line; those extra
# files (resolved against main/) are compiled in alongside it.
#
# No ESP-IDF, no Docker, no hardware required - that property is the whole
# point: it is the only automated feedback signal available in this phase
# before the EE02 kit arrives (01-RESEARCH.md, D-08).
#
# Usage: ./run_host_tests.sh   (from any working directory)

set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
MAIN_DIR="${SCRIPT_DIR}/../main"
TMP_DIR=$(mktemp -d)
trap 'rm -rf "${TMP_DIR}"' EXIT

CC="${CC:-cc}"
FAIL=0
COUNT=0

run_suite() {
    name="$1"
    test_src="$2"
    shift 2
    bin="${TMP_DIR}/${name}"

    echo "== ${name} =="
    if ! "${CC}" -Wall -Wextra -std=c11 "$@" "${test_src}" -o "${bin}"; then
        echo "${name}: COMPILE FAILED"
        FAIL=1
        return
    fi
    if ! "${bin}"; then
        echo "${name}: FAILED"
        FAIL=1
    fi
}

for test_src in "${SCRIPT_DIR}"/test_*.c; do
    [ -e "${test_src}" ] || continue
    COUNT=$((COUNT + 1))
    name=$(basename "${test_src}" .c)
    module=${name#test_}
    impl_src="${MAIN_DIR}/${module}.c"

    if [ ! -f "${impl_src}" ]; then
        echo "${name}: MISSING main/${module}.c"
        FAIL=1
        continue
    fi

    extra=""
    deps_line=$(grep -m1 'HOST_TEST_DEPS:' "${test_src}" 2>/dev/null || true)
    if [ -n "${deps_line}" ]; then
        deps=$(printf '%s\n' "${deps_line}" \
            | sed -n 's/.*HOST_TEST_DEPS:\([^*]*\)\*.*/\1/p')
        for dep in ${deps}; do
            extra="${extra} ${MAIN_DIR}/${dep}"
        done
    fi

    # shellcheck disable=SC2086  # $extra is a deliberately word-split list
    run_suite "${name}" "${test_src}" "${impl_src}" ${extra}
done

if [ "${COUNT}" -eq 0 ]; then
    echo "== summary: no test_*.c suites found =="
    FAIL=1
elif [ "${FAIL}" -eq 0 ]; then
    echo "== summary: ${COUNT} suites, all hardware-free firmware suites passed =="
else
    echo "== summary: one or more suites FAILED =="
fi

exit "${FAIL}"
