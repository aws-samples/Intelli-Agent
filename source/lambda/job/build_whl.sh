#!/bin/bash

# Change to the directory where this script is located
SCRIPT_PATH="$0"
echo "SCRIPT_PATH: $SCRIPT_PATH"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$SCRIPT_DIR"

# Define paths using relative path for SHARED_DIR
SHARED_DIR="$(cd "$SCRIPT_DIR/../shared" && pwd)"
TARGET_DIR="$SCRIPT_DIR/dep/llm_bot_dep/shared"

# Create target directory if it doesn't exist
mkdir -p "$TARGET_DIR"

# Copy files from shared directory to target directory
echo "Copying shared files from $SHARED_DIR to $TARGET_DIR"
cp -r "$SHARED_DIR"/ "$TARGET_DIR"/

# Now proceed with the original commands
cd ./dep
pip install setuptools wheel

python3 setup.py bdist_wheel

# Clean up: Remove the copied files after building the wheel
echo "Cleaning up: Removing copied files from $TARGET_DIR"
rm -rf "$TARGET_DIR"