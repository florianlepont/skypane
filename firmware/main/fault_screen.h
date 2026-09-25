/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Quick task 260924-u7n (DEVICE-06,
 * .planning/seeds/on-device-fault-icon.md): the firmware-local NO
 * CONNECTION hold screen - drawn entirely on-device, with zero server
 * round-trip, on the 2nd consecutive failed wake for a comm/data step.
 *
 * Why a mask + on-device dither, not a full pre-rendered image: a full
 * 960,000-byte NO CONNECTION frame baked into flash would cost 960 KB of
 * the 2.4 MB (0x250000) app partition (firmware/partitions.csv) for what
 * is mostly a blank dithered field - rejected by the seed's own
 * feasibility check. Pillow's Floyd-Steinberg output is aperiodic (each
 * pixel's error depends on every pixel before it), so the dithered field
 * cannot be tiled from a small repeating pattern either - the field must
 * be computed, not stored. fault_screen.c reproduces the exact same
 * integer Floyd-Steinberg recipe firmware/tools/gen_fault_screen.py's
 * Python port implements (one shared spec, see that module's docstring),
 * and stamps the ~32 KB committed ink mask (fault_screen_mask.h,
 * generated from server/plane/render.py's own composition) on top.
 *
 * Counter semantics: `next_backoff_n` is the value AFTER
 * fp_sleep_decide()'s own increment (app_main.c's fail_and_sleep()), so
 * 2 means "this is the 2nd consecutive failure" - the seed's own
 * `backoff_n >= 2` rule, counted post-increment. A healthy wake resets
 * the counter to 0, so an outage always needs two consecutive failures
 * before this screen appears, every time.
 *
 * Excluded step tokens - fp_fault_screen_should_draw() returns false for
 * these regardless of next_backoff_n, by design:
 *   - "blit"     - the panel itself just failed; drawing through the same
 *                  path that failed is unlikely to succeed and risks
 *                  wasting the wake budget on a doomed second blit.
 *   - "reset"    - the previous wake never reached deep sleep on its own,
 *                  which can be a brownout mid-blit; attempting another
 *                  blit immediately after an abnormal reset risks
 *                  looping the exact fault that caused the reset.
 *   - "deadline" - the whole-wake budget is already spent; a blit costs
 *                  roughly another 30 s this wake does not have.
 *   - "nvs"      - NVS is unusable, so the "already shown" sentinel can be
 *                  neither read nor written and the screen would redraw
 *                  on every 5-minute wake of the outage.
 */
#pragma once

#include <stdbool.h>
#include <stdint.h>

#define FP_FAULT_SCREEN_WIDTH 1200
#define FP_FAULT_SCREEN_HEIGHT 1600
#define FP_FAULT_SCREEN_BYTES (FP_FAULT_SCREEN_WIDTH * FP_FAULT_SCREEN_HEIGHT / 2) /* 960,000 */

/* Sentinel written to FP_NVS_IMAGE_HASH once this screen has been drawn -
 * deliberately never of the "sha256:<64 hex>" shape a real server hash
 * takes (validate.c), so it can never collide with one (T-u7n-04) and so
 * the first healthy poll's hash-skip never mistakes this sentinel for a
 * server picture already on the panel. */
#define FP_FAULT_SCREEN_HASH "fault:no-connection"

/* The seed's `backoff_n >= 2` rule, counted post-increment - see this
 * header's own doc comment above. */
#define FP_FAULT_SCREEN_MIN_BACKOFF_N 2

/* Called every FP_FAULT_SCREEN_TICK_ROWS rows during fp_fault_screen_render()
 * so the caller can feed the task watchdog (fp_wake_feed()) - the render
 * itself has no ESP-IDF dependency and cannot call it directly. May be
 * NULL. */
typedef void (*fp_fault_screen_tick_fn)(void);

/* Renders the NO CONNECTION hold screen into `buf`
 * (FP_FAULT_SCREEN_BYTES, PROTOCOL.md §1 packed format: 1600 rows x 600
 * bytes, left pixel of each byte in the high nibble, Black = 0x0,
 * White = 0x1). Fully overwrites every byte - deterministic, so two
 * renders into two differently-pre-filled buffers are byte-identical.
 * `tick` is called (if non-NULL) roughly every 64 rows. */
void fp_fault_screen_render(uint8_t *buf, fp_fault_screen_tick_fn tick);

/* True only when this wake's failed step is one of the allow-listed
 * comm/data tokens (wifi, http, status, json, auth, enrol, secret,
 * config, download, verify - an allow-list, so a future new token
 * defaults to NOT drawing rather than silently starting to), the failure
 * counter has reached FP_FAULT_SCREEN_MIN_BACKOFF_N, and the screen has
 * not already been drawn for this same outage (`already_shown`, driven
 * by the caller comparing FP_NVS_IMAGE_HASH against
 * FP_FAULT_SCREEN_HASH). `step` may be NULL, which always returns
 * false. */
bool fp_fault_screen_should_draw(const char *step, uint8_t next_backoff_n, bool already_shown);
