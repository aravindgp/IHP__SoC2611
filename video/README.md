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
| `SoC2611_07_antenna_violations_explained_2026-11-11.mp4` | what an antenna violation is (plain words, then engineering), why 6,111 wires are above the limit, the repair with a diode at the gate pin, what happens if the chip is handed in unrepaired, and the plan | 3 min 56 s |
| `SoC2611_08_status_hold_and_antenna_repair_2026-11-11.mp4` | status of the afternoon of 11 November: the three kinds of violation (routing, hold, antenna) and their repairs, hold on the real wires before and after the repair (1,771 to 15 at the fast corner) and what the last 15 are, the antenna repair as placed (7,213 diodes, 1,315 buffers), how the routing conflicts close, the two parallel lines, the timeline | 4 min 23 s |
| `SoC2611_09_solved_and_waiting_before_submission_2026-11-11.mp4` | evening of 11 November: what is solved (clock wires and hold on the real wires, antenna repair placed, row fillers and density, the wires that limit the speed) and what the final submission still waits for (the routes, the checks on the final file, LVS on a second machine), with the path to submission | 4 min 4 s |
| `SoC2611_10_how_why_where_solved_2026-11-11.mp4` | how each problem was solved, why it existed and where on the chip the fix sits: maps of the real chip with the 42 re-laid clock wires, the 7,205 delay cells of the hold repair, the 7,213 antenna diodes and 1,315 buffers, the row fillers and the 50 wires that limit the speed, each with a short why and how animation | 3 min 58 s |
| `SoC2611_11_three_runs_problem_solution_hours_2026-11-11.mp4` | the three runs of the evening of 11 November, each with a problem and solution animation: the local antenna route (charge on a long wire, a diode drains it), the fallback closure (wires that touch are laid again) and the data wire experiment (detours, direct paths), with their counts and how many more hours each needs | 3 min 0 s |
| `SoC2611_12_clocks_and_speed_explained_2026-11-13.mp4` | the clocks and the speed of the chip in plain words: what a clock is and why the slowest path sets the fastest beat, why three speeds are quoted (fast, typical and slow corner), the input clock at the pad and the system clock at half its rate, how a path into a memory limits the speed (one input tick, half a system step), and why a system clock of 100 MHz is out of reach on this chip; numbers of candidate v.2.4.0: 54.7 / 45.5 / 29.4 MHz | 5 min 33 s |
| `SoC2611_13_slowest_wire_on_the_chip_2026-11-13.mp4` | the slowest logic step shown on the real layout: seven cells, two small gates that take 23 of the 29 ns, and the wire between them drawn on the chip map (pins 142 um apart, route 8.7 mm); why it runs that way (one of the 202 wires taken out of crowded places on 11 November), what a repair would give, and why the rating of the chip stays at 29.4 MHz (the path into the memories sets it) | 3 min 11 s |
| `SoC2611_16_every_check_2026-11-14.mp4` | every check of release v.3.0.0, each in plain words, then technically, with a small animation of the check at work, the result on this chip and the errors met on the way: open inputs, wiring against synthesis, detours, DRC, antenna, LVS with its negative control, net trace, timing and hold (64.4 / 45.5 / 29.4 MHz), simulation without and with delays, supply voltage drop, and the checklist page | 12 min 7 s |

Videos 03 and 04 are a record of 9 November; the dates in 04 are superseded by video 05.
Video 05 says the timing fix brings hold to zero; that was on estimated wires. Video 06 gives the result on the real routed wires.
The scripts that render videos 01 to 13 are in `SoC2611-main/Flow/scripts/signoff/video/`.
