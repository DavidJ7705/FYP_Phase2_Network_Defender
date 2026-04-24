#!/bin/bash
# Setup script for trained-agent evaluation

# Activate the venv
source venv/bin/activate

# Upgrade pip
pip install --upgrade pip

# Install requirements
pip install -r requirements.txt

# Install CybORG in editable mode from the parent directory
pip install -e ../CAGE_CHALLENGE_4
