#!/bin/bash

cd ./dep
pip install setuptools wheel

python3 setup.py bdist_wheel
