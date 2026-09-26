/* SPDX-FileCopyrightText: 2026 Florian Lepont
 * SPDX-License-Identifier: Apache-2.0 */
/* Fault triggers for the five CONFIG_SKYPANE_FAULT_INJECT_* choices
 * other than NONE — see fault_inject.h for why this file compiles to
 * nothing when NONE is selected. Bench-only: never reachable from a
 * production build. */
#include "fault_inject.h"

#if !CONFIG_SKYPANE_FAULT_INJECT_NONE

#include "esp_log.h"

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "wake_guard.h"

static const char *TAG = "fp_fault";

#if CONFIG_SKYPANE_FAULT_INJECT_PANIC
#define FP_FAULT_NAME "panic"
#elif CONFIG_SKYPANE_FAULT_INJECT_TASK_WDT
#define FP_FAULT_NAME "task_wdt"
#elif CONFIG_SKYPANE_FAULT_INJECT_INT_WDT
#define FP_FAULT_NAME "int_wdt"
#elif CONFIG_SKYPANE_FAULT_INJECT_SLOW_WAKE
#define FP_FAULT_NAME "slow_wake"
#elif CONFIG_SKYPANE_FAULT_INJECT_NVS
#define FP_FAULT_NAME "nvs"
#endif

bool fp_fault_inject_nvs(void)
{
#if CONFIG_SKYPANE_FAULT_INJECT_NVS
    ESP_LOGE(TAG, "SKYPANE-FAULT-INJECT %s", FP_FAULT_NAME);
    return true;
#else
    return false;
#endif
}

void fp_fault_inject_point(void)
{
#if CONFIG_SKYPANE_FAULT_INJECT_NVS
    /* The NVS fault fires at boot (fp_fault_inject_nvs()); a wake that
     * reaches Wi-Fi has nothing left to inject. */
    return;
#endif
    ESP_LOGE(TAG, "SKYPANE-FAULT-INJECT %s", FP_FAULT_NAME);

#if CONFIG_SKYPANE_FAULT_INJECT_PANIC
    /* Verifies the reset classification: the next boot's
     * esp_reset_reason() must read ESP_RST_PANIC and back off instead
     * of polling. */
    abort();
#elif CONFIG_SKYPANE_FAULT_INJECT_TASK_WDT
    /* Never feeds the task watchdog (CONFIG_ESP_TASK_WDT_TIMEOUT_S=60,
     * CONFIG_ESP_TASK_WDT_PANIC=y) — panics within 60 s, verifying the
     * same reset->backoff path via ESP_RST_TASK_WDT. */
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000));
    }
#elif CONFIG_SKYPANE_FAULT_INJECT_INT_WDT
    /* Disabling interrupts starves the interrupt watchdog's own timer
     * tick, which resets the chip with ESP_RST_INT_WDT. */
    portDISABLE_INTERRUPTS();
    for (;;) {
    }
#elif CONFIG_SKYPANE_FAULT_INJECT_SLOW_WAKE
    /* Keeps making progress (feeding the watchdog, checkpointing) past
     * every legitimate wake's duration, so only CONFIG_SKYPANE_WAKE_
     * BUDGET_S's deadline — not the 60 s task watchdog — ends this wake,
     * verifying the `step=deadline` path. fp_wake_checkpoint()'s
     * on_expired callback is noreturn, so this loop never falls through. */
    for (;;) {
        vTaskDelay(pdMS_TO_TICKS(1000));
        fp_wake_checkpoint();
    }
#endif
}

#endif /* !CONFIG_SKYPANE_FAULT_INJECT_NONE */
