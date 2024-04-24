#!/bin/bash

set -e

if [ -d "venv" ]; then
    echo "You've set up a test environment. "
    echo "To prevent mis-operation, you can only rebuild by running the 'make rebuild'"
    exit 1
fi

python3 -m venv venv

source venv/bin/activate

pip install --upgrade pip

pip --default-timeout=6000 install -r requirements.txt

echo "Done"