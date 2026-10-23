# Sleep-current measurement (Phase 47)

Purpose: read the current the frame draws while it sleeps between two wakes, with a multimeter. This is the number that decides whether a six-month autonomy is realistic (`hardware/BATTERY-MODEL.md`, "Six-month target").

Status: procedure only. No reading has been taken. Nothing in this file is a measurement.

## What the reading will tell you

The model estimates a standing draw of about 7.3 mA (central fit, derived from two discharge runs, not a measured hardware current). For about 180 days between charges the average current must be at most the capacity divided by 4320 hours (arithmetic):

| Pack (rated) | Average current allowed for 180 days |
|---|---|
| 3000 mAh | 0.69 mA |
| 5000 mAh | 1.16 mA |
| 6000 mAh | 1.39 mA |
| 10000 mAh | 2.31 mA |

Reading the sleep current:

| Sleep reading | Meaning |
|---|---|
| about 5 mA or more | consistent with the model; something on the board or in the firmware keeps drawing between wakes; six months is out of reach until it is found |
| between 1 and 5 mA | partly explained; six months needs a long interval and a large pack |
| about 1 mA or less | six months becomes plausible with a large pack and a long interval |

The reading is the sleep draw only. Each wake adds to the average on top of it.

## What you need

- A multimeter with a DC milliamp range and a fuse (a range up to about 200 to 400 mA).
- A JST-PH 2 mm pigtail or breakout (a spare cable with the matching connector) so that no wire of the battery is cut. Do not cut or strip the pack's own wires.
- The battery already checked for polarity with the meter in voltage mode. Per `hardware/BOM.md`, on the board the negative pin is nearest the USB-C port and the positive pin the farthest from it.
- The frame displaying an image (an e-ink panel holds its image without power).

## Procedure

1. With the meter in voltage mode, read the battery voltage and write it down.
2. Unplug the USB cable. A frame on USB is not on battery and would invalidate the reading.
3. On the companion Device page, set the wake interval to 3600 s for the test, so that the frame is asleep almost all the time. Note the value that was in force (300 s in production) to put back at the end.
4. Unplug the battery from the board.
5. Put the meter in series on the positive (red) wire only: battery positive, then the meter, then the board's positive pin. Start on the highest milliamp range. Never use the current range across the battery or across the board's pins.
6. Plug the battery back in through the meter and watch. When the frame wakes you will see the reading jump to tens of milliamps for about ten to twenty seconds (the model puts a wake at roughly 87 mA, derived, not measured); between wakes it falls to a steady value. That steady value is the sleep current.
7. Write down at least five steady readings, taken during at least two separate sleep periods, with the range used.
8. If the frame resets, shows an error, or never starts while the meter is in the circuit, stop: the meter's own voltage drop is too high for the wake peaks. Remove the meter and report what happened. Do not force it.
9. Remove the meter, restore the original wiring, put the interval back to its production value, and put the meter back in voltage mode.

## What to record

| Item | Value |
|---|---|
| Date | |
| Meter model and range | |
| Battery voltage before | |
| Wake interval during the test | |
| Steady sleep readings (mA) | |
| Largest reading seen at a wake (mA) | |
| Anything unexpected | |
| Interval restored to | |

Send the table back; the project records it as the result of VAL-03 and compares it with the table above.

## Not covered

- It does not say which part of the board or firmware draws the current. If the reading is high, finding the source is a separate piece of work.
- It does not measure the energy of an image download or a panel refresh.
