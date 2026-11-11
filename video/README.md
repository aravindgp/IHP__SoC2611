# SoC2611 - explainer videos

Short narrated videos (British male voice-over, edge-tts en-GB-RyanNeural, captions follow the spoken word).
File names give the viewing order, the topic and the date the video was made; each one describes the state of that day.

| file | content | length |
|---|---|---|
| `SoC2611_01_chip_explained_2026-11-10.mp4` | the whole chip: blocks, data flow, memory, pins, numbers, boot, current status | 3 min 42 s |
| `SoC2611_02_pinout_2026-11-09.mp4` | the pads, their sides and functions | |
| `SoC2611_03_routing_shorts_explained_2026-11-09.mp4` | what the routing shorts inside and around the SRAM macros were and where they came from | |
| `SoC2611_04_repair_rounds_and_ask_2026-11-09.mp4` | the repair rounds of 8-9 November and the question about the delivery date as it stood that day | |
| `SoC2611_05_status_2026-11-10.mp4` | latest status: how the routing closed (641 to 0), DRC and density results, the clock timing finding and its fix, the 15 November deadline | 2 min 35 s |
| `SoC2611_06_wires_clock_and_hold_explained_2026-11-11.mp4` | what the pF and ns of a wire mean (plain words, then engineering), the detours found on the real routed wires, why a late clock breaks hold, the violation counts of 11 November and the repair plan | 3 min 33 s |

Videos 03 and 04 are a record of 9 November; the dates in 04 are superseded by video 05.
Video 05 says the timing fix brings hold to zero; that was on estimated wires. Video 06 gives the result on the real routed wires.
The scripts that render them are in `SoC2611-main/Flow/scripts/signoff/video/`.
