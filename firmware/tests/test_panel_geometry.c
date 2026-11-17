/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Host test of the compile-time panel geometry: the width, height and packed
 * byte count of the selected panel. The header has no matching .c file, and
 * the suite runs twice: once with the default profile and once with the
 * second-profile macros an ESP-IDF build would take from sdkconfig.h.
 * Run by tests/run_host_tests.sh. */
/* HOST_TEST_HEADER_ONLY */
/* HOST_TEST_PROFILES: second */
#include <assert.h>
#include <stdio.h>

#include "../main/panel_geometry.h"

#if defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
#include "../main/epd7in3e.h"
#endif

static void test_selected_profile_values(void)
{
#if defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
    assert(FP_PANEL_WIDTH == 800);
    assert(FP_PANEL_HEIGHT == 480);
    assert(FP_PANEL_BYTES == 192000);
    assert(FP_PANEL_BYTES == EPD7_PACKED_BYTES);
    printf("panel_geometry: second profile 800x480 = 192000 bytes\n");
#else
    assert(FP_PANEL_WIDTH == 1200);
    assert(FP_PANEL_HEIGHT == 1600);
    assert(FP_PANEL_BYTES == 960000);
    printf("panel_geometry: default profile 1200x1600 = 960000 bytes\n");
#endif
}

static void test_bytes_follow_dimensions_and_kconfig(void)
{
    assert(FP_PANEL_BYTES == (FP_PANEL_WIDTH * FP_PANEL_HEIGHT) / 2);
#ifdef CONFIG_FP_PANEL_BUFFER_BYTES
    assert(FP_PANEL_BYTES == CONFIG_FP_PANEL_BUFFER_BYTES);
#endif
}

int main(void)
{
    test_selected_profile_values();
    test_bytes_follow_dimensions_and_kconfig();
    printf("panel_geometry: all cases pass\n");
    return 0;
}
