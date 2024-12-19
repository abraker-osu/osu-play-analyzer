#!/bin/bash

echo "Removing '.eggs/...'..."
rm -rf .eggs

echo "Removing 'build/...'..."
rm -rf build

echo "Removing 'dist/...'..."
rm -rf dist

echo "Removing 'pycache'..."
python3 -Bc "import pathlib; import shutil; [shutil.rmtree(path) for path in pathlib.Path('.').rglob('__pycache__')]"
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

python3 -m pip cache purge

echo "[ DONE ]"
