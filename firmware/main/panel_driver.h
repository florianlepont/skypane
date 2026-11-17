/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Compile-time panel driver selection for panel.c.
 *
 * With the default configuration (CONFIG_FP_PANEL_13IN3E) this header
 * defines nothing, so panel.c calls the 13.3" driver exactly as before.
 * When the 7.3" panel is configured it re-points the three driver calls
 * panel.c makes at the single-controller driver in epd7in3e.c. */
#pragma once

#include "sdkconfig.h"

#if defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
#include "epd7in3e.h"

_Static_assert(CONFIG_FP_PANEL_BUFFER_BYTES == EPD7_PACKED_BYTES,
               "CONFIG_FP_PANEL_BUFFER_BYTES must be the 800x480 frame size");

#define epd_init  epd7in3e_init
#define epd_blit  epd7in3e_blit
#define epd_sleep epd7in3e_sleep
#else
_Static_assert(CONFIG_FP_PANEL_BUFFER_BYTES == 960000,
               "CONFIG_FP_PANEL_BUFFER_BYTES must be the 1200x1600 frame size");
#endif
