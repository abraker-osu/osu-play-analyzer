#!/bin/bash
# Description
#   Sets up the virtual environment and installs editable libraries
#   Also initializes/fixes submodules
#
# Usage
#   $ scripts\setup.sh install all
#
# Args
#   1: "install" (optional)
#       install: Installs python libraries if not already installed and initializes submodules
#
#   2: "all"     (optional)
#       all: Installs requirements for each submodule as well

if [ -f /etc/debian_version ]; then
    sudo apt update

    # Needed for pyqt6
    sudo apt install -y libxkbcommon-x11-0 libxcb-cursor-dev libxcb-icccm4 libxcb-keysyms1

    # Needed for pyinstaller and built binary metadata info setting
    sudo apt install -y binutils attr

    # Python prereqs
    sudo apt install -y python3 python3-venv
elif [ -f /etc/arch-release ]; then
    # Needed for PyQt6
    sudo pacman -Syy --noconfirm xorg-xkbcommon xcb-util-cursor xcb-util-keysyms

    # Needed for pyinstaller and built binary metadata info setting
    sudo pacman -Syy --noconfirm binutils attr

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

# Installs project libraries if not already installed
# NOTE: Editables will be re-installed
if [ "$1" == "install" ]; then
    python3 -m pip install --require-virtualenv -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install editable libraries!"
        exit 1
    fi

    python3 -m pip install --require-virtualenv -r requirements_editable.txt
    if [ $? -ne 0 ]; then
        echo "Failed to install editable libraries!"
        exit 1
    fi
fi

if [ -d "${VIRTUAL_ENV}/src}" ]; then
    dir "${VIRTUAL_ENV}/src"
    echo ""

    if [ "$2" == "all" ]; then
        # Installs requirements for each submodule
        for dir in "${VIRTUAL_ENV}/src"/*; do
            echo "processing \"${VIRTUAL_ENV}/src/$dir/requirements.txt\""
            if [ -f "${VIRTUAL_ENV}/src/$dir/requirements.txt" ]; then
                python3 -m pip install --require-virtualenv -r "${VIRTUAL_ENV}/src/$dir/requirements.txt"
                if [ $? -ne 0 ]; then
                    echo "Failed to install requirements for \"${VIRTUAL_ENV}/src/$dir\""
                    exit 1
                fi
            fi
            else
                echo "\"${VIRTUAL_ENV}/src/$dir/requirements.txt\" not found"
            fi
        done
        echo ""
    fi

    # Changes folders in venv/src from dashes to underscores
    python3 "scripts/helper/src_fix.py"
    if [ $? -ne 0 ]; then
        echo "Failed to fix src paths"
        exit 1
    fi

    python3 "scripts/helper/fix_submodules.py"
fi
else
    echo "\"${VIRTUAL_ENV}/src\" not found"
    exit 1
fi

python3 -m pip list
echo ""

echo "[ DONE ]"
exit 0
