# SoC2611 - status 11 November 2026, 14:30 CET (hold repaired on the extracted wires, antenna repair in routing)

Follows `STATUS_2026-11-10_evening.md`. The candidate `v.2.0.0-rc3` of this morning is **not** the file we will submit:
its hold timing was met on wire parasitics estimated from placement, and failed once the routed wires were extracted.
This note gives what was found, what is repaired, what is still running, and the checks that run on a second machine.

## What the extracted wires showed (rc3)
The routed wires of rc3 were extracted (own RC extraction of the routed database) and the timing repeated on them.

| item on rc3, extracted wires | value |
|---|---|
| hold, failing endpoints (fast / typical / slow corner) | 3,029 / 1,503 / 586 |
| nets with more than 1 ns of wire delay | 434 |
| clock nets with more than 0.5 ns of wire delay | 16 |
| longest net | 23 mm for pins 150 um apart |

Cause: to remove the last routing violations the router had pushed nets onto long detours around the SRAM macros
(Metal1 to Metal4 cannot cross a macro). Sixteen of them were clock nets, so about 3,300 flip-flops saw the clock
0.5 to 2.8 ns late. A hold failure does not depend on the clock frequency.

## Repaired since then
1. **Clock nets.** 42 clock nets were routed again along explicit short guides, with the long runs on TopMetal1.
   Routing re-closed to 0 violations. Clock nets above 0.5 ns of wire delay: 16 before, 2 after (both are the
   wires from clock input pads: camera pixel clock and JTAG clock).
2. **Hold, on the extracted timing.** Hold repair was run on the extracted parasitics at the fast, slow and typical
   corner, with every existing cell locked: 7,205 delay cells, 13,892 nets routed again.

| hold, failing endpoints on extracted wires | fast | typical | slow |
|---|---|---|---|
| before the repair | 1,771 | 616 | 511 |
| after the repair (first route of it) | 15 | 14 | 14 |
| of those, paths from input pads | 14 | 14 | 14 |
| inside the chip | 1 at -0.03 ns | 0 | 0 |

The 14 pad paths are 6 plain inputs (GPIO, UART receive and similar; their timing is set by the board) and the 8
HyperBus data inputs (covered by the delayed read strobe, see the rc3 note). The one internal endpoint is taken by
the last, small hold round after the antenna route.

3. **Antenna repair, placed.** On the hold-repaired route the OpenROAD check lists 6,131 nets and 7,227 gate pins
   above the ratio limit (worst 59 times the limit, most below 2 times).

| antenna repair | value |
|---|---|
| diodes, one at each violating gate pin (two where the ratio is 20 times the limit or more) | 7,213 |
| buffers at SRAM and pad pins (the long wire then ends on the buffer, which has its own diode) | 1,315 |
| SRAM clock pins left without a cell, on purpose (a buffer there would delay that clock), on 16 clock nets, at most 2.75 times the limit | 26 |
| existing cells moved | 0 |

   The 7,429 touched nets are **not** sent through a new global route. Each keeps the guides its present wire was
   routed in and only gains the short link to its new pin, so the paths, and with them the timing, stay where they
   were. Violations of that route per pass: 203,334, 21,429, 16,292, 3,469, 2,416, 2,023, 1,858, 1,642, 1,575, 1,521,
   1,073, 942, 862 (pass 12 of 16).

4. **Row filler cells.** The rows had no filler cells so far. A trial on the clean database placed 1,080,061 filler
   cells (placement legal).

| check with row fillers | result |
|---|---|
| IHP minimum rule set, layout without fill, 11 front-end tables | 0 violations |
| density of the filled file, before and after the corner clean-up | 0 violations |
| minimum rule set on the filled file: Activ, Activ filler, GatPoly, TopMetal1 filler | 0 violations |
| minimum rule set on the filled file: Metal filler, Metal1, pSD | running |

   The final file will carry the row fillers.

## Speed, on the extracted wires
The rc3 note gave 34.6 MHz (typical) and 21.7 MHz (slow) for the system clock; that was on estimated wires. On the
extracted wires the limit is lower:

| corner | system clock that meets setup today |
|---|---|
| fast | 15.0 MHz |
| typical | 12.7 MHz |
| slow | 10.0 MHz |

The limiting paths go from system-clock flip-flops into SRAM pins on the double-rate clock (half a cycle) and carry
a few nets on long detours. Ranked by the paths they sit on, 50 nets explain it:

| nets put on a direct path, most useful first | system clock at the slow corner (what-if, 0.3 ns per fixed net) |
|---|---|
| 0 | 10.0 MHz |
| 1 | 15.0 MHz |
| 10 | 18.9 MHz |
| 30 | 25.1 MHz |
| 50 | 26.9 MHz; after that cell delay limits, not wires |

Direct guides for these 50 nets are prepared (1,566 guide boxes, 37 mm of tree length) and are routed on a separate
line on top of the antenna-routed database. They go into the final file only if that line closes as cleanly as the
plain one. Speed does not decide whether the chip works; hold does.

## Checks on a second machine (the two packages)
LVS has not completed on the build machine (more than 15 hours without finishing), and there it would compete with
the routing runs for memory. Two packages were therefore made from rc3 and moved to a second machine as a
rehearsal: they show how long the runs take and whether the setup itself reports anything, before the final file.

| package | content | size | sha256 |
|---|---|---|---|
| `lvs_pkg_rc3.tar` | LVS view of rc3 (seal ring, via cells dissolved), its CDL, the KLayout LVS deck of the PDK, run script (deep mode) | 269,803,520 bytes | `3176e2df733fc88aec1472332956ce8e960e202911e170ae56a994b7aac4c699` |
| `drc_pkg_rc3.tar` | full-fill GDS of rc3 (die corners cleaned), the KLayout DRC deck of the PDK, run script (minimum rule set with density, deep mode) | 191,580,160 bytes | `f79d4df54f13c842d7f18585e86610a15da5e3f603acf90600932e3ef765d11c` |

The packages are not in git (a file in them is over GitHub's 100 MB limit); they are moved machine to machine and
checked against the hashes above. On the build machine the minimum rule set on the filled rc3 file was stopped after
18 of 26 tables, all clean, when rc3 was withdrawn; the second machine takes it to the end. The same two packages
will be made for the final file.

| run on the second machine | state at 14:30 CET |
|---|---|
| LVS on rc3 | package delivered; no result yet |
| minimum rule set with density on the filled rc3 file | first transfer arrived damaged, package sent again; no result yet |

## Running on the build machine at 14:30 CET
| run | state |
|---|---|
| antenna route along the existing guides | pass 13 of 16, 862 violations |
| closure of the hold-repaired route without antenna cells (fallback) | 288, then 149, then 30 after two rounds; round 3 running |
| minimum rule set on the filled file with row fillers | 4 of 7 tables done, 0 violations |

## Still open
- routing of the antenna repair to 0 violations (16 passes, then the closure rounds: only the nets named in the
  markers are routed again, 16 passes each)
- the last, small hold round on the extracted wires of that result
- on the final database: GDS, seal ring, row fillers, fill, corner clean-up, density, the minimum rule set with all
  26 tables and the GatPoly filler table, the trace of every net in the GDS against the netlist, the antenna check
- LVS: on the second machine; it has never completed on this chip

## Dates
| step | target |
|---|---|
| antenna route closed, first full DRC run on it | night of 11 to 12 November |
| final hold round, final checks, release `v.2.0.0` on a branch | 12 November |
| our own limit for the checked file | 13 November |
| deadline given by IHP | 15 November 2026, 23:59 CET, one attempt |

## Explainer videos (branch `videos`, folder `video/`)
| file | content |
|---|---|
| `SoC2611_07_antenna_violations_explained_2026-11-11.mp4` | what an antenna violation is, why 6,111 nets, the diode repair, the risk of handing in unrepaired |
| `SoC2611_08_status_hold_and_antenna_repair_2026-11-11.mp4` | the three kinds of violation and their repairs, hold before and after |
| `SoC2611_09_solved_and_waiting_before_submission_2026-11-11.mp4` | what is solved and what the submission still waits for |
| `SoC2611_10_how_why_where_solved_2026-11-11.mp4` | how, why and where each problem was solved, on maps of the chip |
