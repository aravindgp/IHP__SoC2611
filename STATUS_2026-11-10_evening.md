# SoC2611 - status 10 November 2026, 19:30 CET (timing finding on rc2, fix in routing)

Follows `STATUS_2026-11-10.md` (08:30 CET). Since the morning the checks on the filled file progressed, and the first
full timing report of the routed chip found a clock alignment problem that has to be fixed before submission.

**`release/v.2.0.0-rc2` is a candidate for the layout checks only (DRC, density, fill, seal ring). It is not the file
we will submit.** The file with the timing fix follows as `v.2.0.0`.

## Layout checks on rc2 (filled GDS, fill at the die corners cleaned)
| check | result |
|---|---|
| density (Activ, GatPoly, Metal1-4, TopMetal1; global and window rules) | 0 violations |
| IHP minimum DRC, deep mode | 27 of 28 rule tables completed with 0 violations, each verified by its own completion line; the Nwell table is running since 11:30 CET |
| LVS, deep mode | devices extracted; the netlist comparison is running since 06:07 CET and has not finished |

## The timing finding
The single-port SRAM wrapper does two accesses per system clock cycle on the double-rate clock. For that, the clock
edge at the SRAM clock pins must not arrive later than at the flip-flops that drive the SRAM pins. On rc2 it does
(typical corner; wire parasitics estimated from placement with the Metal3 layer RC):

| clock arrival on rc2 | ns |
|---|---|
| core flip-flops | about 4.6 |
| phase flip-flops of the wrapper | about 7.8 |
| single-port SRAM clock pins | up to about 12 |

| hold on rc2, typical corner | value |
|---|---|
| worst hold slack | -7.73 ns |
| flip-flop to SRAM pin endpoints that fail | 10,324 |
| phase flip-flop to SRAM pin endpoints that fail | 2,136 |
| flip-flop to flip-flop endpoints that fail | 246 |

A hold failure does not depend on the clock frequency, so rc2 would not work at any speed. Two causes: hold repair
had not been run in the flow that produced this placement, and the clock root net is about 10 mm long without a
repeater.

## The fix (ECO on the clean routed database)
- the SRAM clock tree is taken from the clock root directly, so the SRAM clock arrives first
- six repeaters on the clock root
- 16 and 17 delay cells put the phase flip-flop clock and the core flip-flop clock after the SRAM clock, aligned
  with each other
- hold repair at the fast corner and then at the slow corner: 7,615 + 315 buffers
- legalisation: 7,969 new cells, 2,218 existing cells moved (23 um at most); 20,475 nets are re-routed

Timing of the fixed database before the re-route (same parasitic estimate; the constraints carry 0.15 ns clock
uncertainty):

| corner | hold, internal paths | hold at the SRAM pins | setup at 100 MHz double-rate clock | system clock that meets setup |
|---|---|---|---|---|
| fast | -0.03 ns worst on 168 endpoints (inside the uncertainty) | +0.27 ns | met, +0.56 ns | 50 MHz |
| typical | met | +0.57 ns | -4.47 ns | 34.6 MHz |
| slow | met | +1.05 ns | -13.04 ns | 21.7 MHz |

The fix costs speed: 50 MHz was the target, and the paths into the SRAM pins on the double-rate clock now set the
limit. Six paths from input pads to flip-flops are not part of the hold repair; their hold depends on the board
timing (the constraints hold one placeholder input delay).

## Running at 19:30 CET
| run | state |
|---|---|
| re-route of the timing fix, 24 repair passes | pass 9; violations 2,056, 1,141, 1,034, 855, 764, 685 in passes 3 to 8 |
| antenna repair on the clean database (11,513 diodes, 325 jumpers on 6,105 nets) | pass 18 of 24; 3,608 violations before the rip-up pass, 8,191 after it |
| Nwell rule table on rc2 | running |
| LVS on the clean database | netlist comparison running |

## Plan
1. Close the routing of the fixed database (further repair passes if the first 24 do not reach 0).
2. Antenna: if the repair on the clean database closes, the timing fix is applied on top of it. If not, antennas are
   repaired on the fixed database, highest ratios first.
3. GDS, seal ring, fill, corner clean-up, density, all DRC tables and LVS on that database.
4. Release `v.2.0.0` with hashes and the DRC result files, and a note on Open-Silicon-MPW issue #79.

Deadline given by IHP on 10 November: 15 November 2026, 23:59 CET, one attempt. Our target for the checked file is
13 November.
