# Signoff environment: DGSE toolchain (KLayout 0.30.5, Magic, Netgen, OpenROAD) + IHP PDK.
# Source it:  . HW/asic/signoff/env.sh      (override DGSE_ENV / PDK_ROOT before sourcing)
: "${DGSE_ENV:=/root/.claude/jobs/658ac326/tmp/dgse_env.sh}"
[ -f "$DGSE_ENV" ] && . "$DGSE_ENV"
: "${PDK_ROOT:=/root/.claude/jobs/658ac326/tmp/pdk_root}"
export PDK_ROOT
export PDK=ihp-sg13cmos5l
export KLAYOUT_TECH=$PDK_ROOT/$PDK/libs.tech/klayout/tech
SIGNOFF_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)
export SIGNOFF_DIR
export QT_QPA_PLATFORM=offscreen
