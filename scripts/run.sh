#!/bin/bash
# Description:
#   Runs a python file with the virtual environment activated
#
# Usage:
#   $ scripts/run.sh <python file>
#
# Args
#   1: python file to run
if [ ! -d "venv_nix" ]; then
    echo "No venv found"
    exit 1
fi

source venv_nix/bin/activate
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment"
    exit 1
fi

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment not active"
    exit 1
fi

python3 $1

echo "[ DONE ]"
