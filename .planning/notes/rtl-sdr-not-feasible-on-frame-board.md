---
title: RTL-SDR ADS-B decoding is not feasible directly on the Frame's own board
date: 2026-08-27
context: Explore session on local RTL-SDR as a backup ADS-B source (see the sibling seed local-rtl-sdr-adsb-backup.md)
---

## Decision

Running an RTL-SDR dongle and ADS-B decoder directly on the Frame's XIAO
ESP32-S3 board was considered and ruled out. Any future local-reception
work needs a separate always-on host near Orly (Raspberry Pi, Freebox, or
similar) — not the device itself.

## Why

Two independent, non-negotiable blockers, either one of which alone would
be disqualifying:

1. **Battery/power architecture.** The Frame's entire hardware and firmware
   design is a wake → poll → display → deep-sleep cycle specifically so it
   can run on battery for weeks/months (a core project constraint - see
   PROJECT.md's Power constraint and DEVICE-05). Real-time ADS-B decoding
   requires the receiver and decoder to run continuously, which is the
   direct opposite of that model. Attempting it on-device would keep the
   ESP32-S3 awake permanently and exhaust the battery in hours, not weeks.

2. **Compute/DSP workload.** Decoding ADS-B from raw RTL-SDR IQ samples
   (~2.4 Msps: preamble correlation, PPM demodulation, CRC checking, done
   continuously) is a sustained signal-processing job that even a
   Raspberry Pi Zero runs at or near its capacity. The ESP32-S3 is a
   battery-oriented microcontroller (no MMU, limited RAM, no OS-level
   scheduling/buffering) built for brief wake cycles, not sustained DSP
   throughput. This is a fundamentally different hardware class from what
   ADS-B decoding software (dump1090/readsb) targets.

Not fully verified: whether anyone has published a working ESP32-based
ADS-B decoder as a research curiosity. Even if one exists, blocker #1
(battery) would still rule it out for this project's use case regardless
of blocker #2's outcome, since the power model conflict is independent of
whatever compute optimization might be possible.

## Implication

If local reception is ever pursued (see the RTL-SDR seed), the receiver
and decoder must run on a separate, dedicated, always-on host at the
install address - not integrated into the Frame's own firmware/hardware.
