#!/bin/bash

if [ -f /etc/debian_version ]; then
    # Needed for pyqt6
    sudo apt install -y libxkbcommon-x11-0 libxcb-cursor-dev libxcb-icccm4 libxcb-keysyms1

    # Python prereqs
    sudo apt install -y python3
    sudo apt install -y python3-venv
elif [ -f /etc/arch-release ]; then
    # Needed for PyQt6
    sudo pacman -Syy --noconfirm xorg-xkbcommon xcb-util-cursor xcb-util-keysyms

    # Python prerequisites
    sudo pacman -Syy --noconfirm python python-virtualenv
else
    echo "Unsupported distribution."
    exit 1
fi

# Create venv
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

echo "[ DONE ]"
