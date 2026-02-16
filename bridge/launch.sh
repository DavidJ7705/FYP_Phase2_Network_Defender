#!/bin/bash
# Launch script that uses a native Linux venv for speed.
# Downloads packages from pip instead of reading over the OrbStack mount.

set -e

BRIDGE_DIR="$(cd "$(dirname "$0")" && pwd)"
LOCAL_VENV="/tmp/fyp-venv-linux"

if [ ! -f "$LOCAL_VENV/.ready" ]; then
    echo "=== First run: creating native Linux venv ==="
    echo "This downloads packages from pip (much faster than reading over mount)."
    echo ""
    rm -rf "$LOCAL_VENV"
    python3 -m venv "$LOCAL_VENV"
    "$LOCAL_VENV/bin/pip" install --upgrade pip -q
    echo "Installing PyTorch (CPU)..."
    "$LOCAL_VENV/bin/pip" install torch==2.6.0+cpu --index-url https://download.pytorch.org/whl/cpu -q
    echo "Installing torch_geometric..."
    "$LOCAL_VENV/bin/pip" install torch_geometric -q
    echo "Installing other dependencies..."
    "$LOCAL_VENV/bin/pip" install docker numpy -q
    touch "$LOCAL_VENV/.ready"
    echo ""
    echo "=== Venv ready at $LOCAL_VENV ==="
    echo "Future runs will skip this step."
    echo ""
else
    echo "Using cached native venv at $LOCAL_VENV"
fi

cd "$BRIDGE_DIR"
exec sudo "$LOCAL_VENV/bin/python" run_agent.py "$@"