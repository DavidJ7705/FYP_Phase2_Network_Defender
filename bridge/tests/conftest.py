# pytest configuration — adds bridge/ to sys.path so all test files can import bridge modules.
#
# Run the full test suite (Terminal 2, topology must be deployed in Terminal 1):
#   cd ~/Desktop/Network_Defender_FYP/bridge
#   sudo ~/fyp-venv-linux/bin/python -m pytest tests/ -v
#
# Run with coverage:
#   sudo ~/fyp-venv-linux/bin/python -m pytest tests/ -v --cov=. --cov-report=term-missing

import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

collect_ignore = ["test_docker_action.py"]