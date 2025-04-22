#!/bin/bash
# Description
#   Updates the submodules to latest main/master
#
# Usage
#  $ scripts\update.sh all
#
# Args
#  1: "all" (optional)
#      all: Update python libraries as well

for dir in "venv_nix/src"/*; do
    echo "Updating \"$dir\"..."
    pushd "venv_nix/src/$dir"

    git fetch origin
    if [ $? -ne 0 ]; then
        echo "Failed to fetch"
        exit 1
    fi

    # Check if 'main' branch exists
    git show-ref --verify --quiet refs/heads/main
    if [ $? -eq 0 ]; then
        git checkout main
        if [ $? -ne 0 ]; then
            echo "Failed to checkout main"
            exit 1
        fi

        git pull origin main
    else
        # Check if 'master' branch exists
        git show-ref --verify --quiet refs/heads/master
        if [ $? -eq 0 ]; then
            git checkout master
            if [ $? -ne 0 ]; then
                echo "Failed to checkout master"
                exit 1
            fi

            git pull origin master
        else
            echo "Failed to find main or master branch"
            exit 1
        fi
    fi

    popd
    echo ""
done

if [ "$1" == "all" ]; then
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

    echo "Updating pip..."
    python3 -m pip install --require-virtualenv --upgrade pip
    if [ $? -ne 0 ]; then
        echo "Failed to upgrade pip"
        exit 1
    fi

    echo "Updating python libraries..."
    python3 -m pip install --require-virtualenv --upgrade -r requirements.txt
    if [ $? -ne 0 ]; then
        echo "Failed to upgrade libraries"
        exit 1
    fi
fi

echo "[ DONE ]"
exit 0
