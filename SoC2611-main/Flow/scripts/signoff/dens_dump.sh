#!/bin/bash
# Dump placement geometry (dump_density.tcl) of an odb to a txt, unless it exists.  usage: dens_dump.sh <odb> <out.txt>
set -u
HERE=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
OR=/nix/store/2y36a4sr078y15ick388dncqjdzmlxga-openroad-2026-02-17/bin/openroad
[ -s "$2" ] && { echo "DENS: $2 exists"; exit 0; }
IN_ODB=$1 OUT_TXT=$2 "$OR" -exit "$HERE/dump_density.tcl" > "$2.log" 2>&1
grep -a "DUMP_DENSITY" "$2.log" || { echo "DENS: dump failed"; tail -3 "$2.log"; exit 1; }
