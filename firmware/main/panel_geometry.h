/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Compile-time size of the selected panel: width and height in pixels and
 * the packed frame size in bytes (two pixels per byte).
 *
 * Pure C with no ESP-IDF dependency. Under ESP-IDF the panel choice comes
 * from sdkconfig.h; a host build without that header gets the default
 * 13.3" panel unless it defines the same CONFIG macros itself. */
#ifndef FP_PANEL_GEOMETRY_H
#define FP_PANEL_GEOMETRY_H

#if defined(__has_include)
#if __has_include("sdkconfig.h")
#include "sdkconfig.h"
#endif
#endif

#if defined(CONFIG_FP_PANEL_7IN3E) && CONFIG_FP_PANEL_7IN3E
#define FP_PANEL_WIDTH  800
#define FP_PANEL_HEIGHT 480
#else
#define FP_PANEL_WIDTH  1200
#define FP_PANEL_HEIGHT 1600
#endif

/* Two nibble-packed pixels per byte. */
#define FP_PANEL_BYTES ((FP_PANEL_WIDTH * FP_PANEL_HEIGHT) / 2)

_Static_assert(FP_PANEL_BYTES == (FP_PANEL_WIDTH * FP_PANEL_HEIGHT) / 2,
               "FP_PANEL_BYTES must be width * height / 2");
#ifdef CONFIG_FP_PANEL_BUFFER_BYTES
_Static_assert(FP_PANEL_BYTES == CONFIG_FP_PANEL_BUFFER_BYTES,
               "CONFIG_FP_PANEL_BUFFER_BYTES must equal the packed size of the selected panel");
#endif

#endif /* FP_PANEL_GEOMETRY_H */
