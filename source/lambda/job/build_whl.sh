#!/bin/bash

cd ./dep
pip install setuptools wheel

python setup.py bdist_wheel