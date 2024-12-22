#!/bin/bash

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

python3 src/run.py

echo "[ DONE ]"
