/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Bench-only verification hooks for the reset/backoff path (FW-01) and
 * the wake-budget path (FW-02): a real crash, hang or brownout is hard
 * to reproduce on demand, so the hardware session needs a way to
 * trigger each one deliberately. Selected by the
 * CONFIG_SKYPANE_FAULT_INJECT_* choice (main/Kconfig.projbuild),
 * default NONE.
 *
 * When NONE is selected this header's own inline stub is the entire
 * cost: fault_inject.c's whole body is excluded from the translation
 * unit, so no fault code and no "SKYPANE-FAULT-INJECT" string reach a
 * production image — proven by
 * firmware/tests/check_production_config.sh's built-mode check. */
#pragma once

#include "sdkconfig.h"

#if CONFIG_SKYPANE_FAULT_INJECT_NONE

static inline void fp_fault_inject_point(void)
{
}

#else

/* Called once, right after Wi-Fi connects (state_machine.c) — the
 * earliest point downstream code already treats as a safe checkpoint.
 * Logs which fault is armed, then triggers it: PANIC aborts outright;
 * TASK_WDT blocks without feeding the task watchdog; INT_WDT spins with
 * interrupts disabled; SLOW_WAKE keeps making progress (feeding the
 * watchdog, checkpointing) so only the wake budget — not the watchdog —
 * ends it. Never returns for PANIC/TASK_WDT/INT_WDT; SLOW_WAKE's loop
 * ends by calling fp_wake_checkpoint()'s own noreturn expiry callback. */
void fp_fault_inject_point(void);

#endif
