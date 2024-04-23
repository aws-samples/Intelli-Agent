#!/bin/bash

set -e

if [ -d "venv" ]; then
    source venv/bin/activate
fi

if [ -n "$1" ]; then
    pytest ./$1 --exitfirst -rA --log-cli-level=INFO --json-report --json-report-summary --json-report-file=detailed_report.json --html=report.html --self-contained-html --continue-on-collection-errors
    exit 0
fi

pytest ./ --exitfirst -rA --log-cli-level=INFO --json-report --json-report-summary --json-report-file=detailed_report.json --html=report.html --self-contained-html --continue-on-collection-errors