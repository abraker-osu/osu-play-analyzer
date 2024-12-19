#!/bin/bash

# Check if python3 is installed
if ! command -v python3 &> /dev/null; then
    echo "python3 is not installed. Installing..."
    sudo apt-get install python3

    if [ $? -ne 0 ]; then
        echo "Failed to install python3"
        exit 1
    fi
fi

# Check if python3-venv is installed
if ! python3 -c "import ensurepip" &> /dev/null; then
    echo "python3-venv is not installed. Installing..."
    sudo apt-get install python3-venv

    if [ $? -ne 0 ]; then
        echo "Failed to install python3-venv"
        exit 1
    fi
fi

if [ ! -d "venv_nix/bin" ]; then
    echo "No venv found. Creating..."
    python3 -m venv venv_nix

    if [ $? -ne 0 ]; then
        echo "Failed to create virtual environment"
        exit 1
    fi
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

git config core.longpaths true
if [ $? -ne 0 ]; then
    echo "Failed to set git longpaths!"
    exit 1
fi

if [ "$1" == "install" ]; then
    python3 -m pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install editable libraries!"
        exit 1
    fi
fi

# Changes folders in venv/src from dashes to underscores
python3 "scripts/helper/src_fix.py"
if [ $? -ne 0 ]; then
    echo "Failed to fix src paths"
    exit 1
fi

# # Get the Python version (e.g., 3.8 or 3.9)
# PY_VER=$(python3 --version | awk '{print $2}' | cut -d '.' -f 1-2)

# # Set the hook file path
# hook_file="$VIRTUAL_ENV/lib/python$PY_VER/site-packages/sitecustomize.py"
# rm -f "$hook_file"

# # Create a 'sitecustomize.py' file
# # Python automatically runs this before importing any modules
# # This edits paths to allow module import from workspace root
# echo "import sys" > "$hook_file"
# echo "sys.path.insert(0, f'{sys.prefix}/src')" >> "$hook_file"

# if [ ! -f "$hook_file" ]; then
#     echo "Failed to create sitecustomize.py"
#     exit 1
# fi

echo "[ DONE ]"
