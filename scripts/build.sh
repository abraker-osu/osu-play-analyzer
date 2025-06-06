#!/bin/bash
# Description
#   Builds the project
#
# Usage
#   $ scripts\build.bat

if [ ! -d "venv_nix" ]; then
    echo "No venv found"
    exit 1
fi

source "venv_nix/bin/activate"
if [ $? -ne 0 ]; then
    echo "Failed to activate virtual environment"
    exit 1
fi

if [ -z "$VIRTUAL_ENV" ]; then
    echo "Virtual environment not active"
    exit 1
fi

bash scripts/clean.sh
if [ $? -ne 0 ]; then
    echo "Failed to clean project"
    exit 1
fi

# Build exe
rm -f "dist/osu-performance-analyzer" 2>/dev/null
pyinstaller -y "build.spec"
if [ $? -ne 0 ]; then
    echo "Failed to build exe"
    exit 1
fi

# Copy res to dist
rm -rf "dist/res"
cp -r "res" "dist/res"
if [ $? -ne 0 ]; then
    echo "Failed to copy res to dist"
    exit 1
fi

# Set binary metadata
ver_date=$(date +'%Y.%m.%d')
ver_time=$(printf "%05d" $((10000*$(date +'%H') + 100*$(date +'%M') + $(date +'%S'))))

setfattr -n user.version -v "${ver_date}.${ver_time}" dist/osu-performance-analyzer
setfattr -n user.description -v "An analysis tool for osu! beatmaps, replays, scores, and more!" dist/osu-performance-analyzer

# Copy map_generator library to dist (used by map architect)
mkdir -p "dist/res/map_generator"
cp "venv_nix/src/map_generator/src/"*.py "dist/res/map_generator/"
if [ $? -ne 0 ]; then
    echo "Failed to copy map_generator to dist"
    exit 1
fi

# Zip relevant files
rm -f "dist/osu-performance-analyzer_linux.tar.gz" 2>/dev/null

tar -czf "dist/osu-performance-analyzer_linux.tar.gz" -C "dist" "osu-performance-analyzer" "res"
if [ $? -ne 0 ]; then
    echo "Failed to tar files"
    exit 1
fi

echo "[ DONE ]"
exit 0
