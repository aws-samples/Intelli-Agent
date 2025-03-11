#!/bin/bash

# Change to the directory where this script is located
# Works with both sh and bash
SCRIPT_PATH="$0"
echo "SCRIPT_PATH: $SCRIPT_PATH"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$SCRIPT_DIR"

# Now proceed with the original commands
cd ./dep
pip install setuptools wheel

python3 setup.py bdist_wheel
