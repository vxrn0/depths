#!/bin/sh
# Balance run: ./scripts/sim.sh [games]
exec python3 -m depths --sim "${1:-200}"
