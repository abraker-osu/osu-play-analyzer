#!/bin/bash

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

echo "Removing 'build/...'..."
rm -rf "build"

# Uncomment the following lines if you want to remove 'dist/' as well
# echo "Removing 'dist/...'..."
# rm -rf "dist"

# Build exe
rm -f "dist/osu-performance-analyzer.exe" 2>/dev/null
pyinstaller -y "build.spec"
if [ $? -ne 0 ]; then
    echo "Failed to build exe"
    exit 1
fi

# Generate version file to set exe version
rm -f "data/version.txt" 2>/dev/null
python "scripts/helper/gen_ver.py"
if [ $? -ne 0 ]; then
    echo "Failed to generate version file"
    exit 1
fi

# Set exe version (shown in file properties metadata)
pyi-set_version "data/version.txt" "dist/osu-performance-analyzer.exe"
if [ $? -ne 0 ]; then
    echo "Failed to set version to exe"
    exit 1
fi

# Copy res to dist
rm -rf "dist/res"
mkdir -p "dist/res"
rsync -a --delete "res/" "dist/res/"
if [ $? -ne 0 ]; then
    echo "Failed to copy res to dist"
    exit 1
fi

# Copy map_generator library to dist (used by map architect)
mkdir -p "dist/res/map_generator"
rsync -a --include='*.py' --exclude='*' "venv_nix/src/map_generator/src/" "dist/res/map_generator/"
if [ $? -ne 0 ]; then
    echo "Failed to copy map_generator to dist"
    exit 1
fi

# Zip relevant files
rm -f "dist/osu-performance-analyzer.zip" 2>/dev/null
tar -a -c -C "dist" -f "dist/osu-performance-analyzer.zip" "osu-performance-analyzer.exe" "res"
if [ $? -ne 0 ]; then
    echo "Failed to zip files"
    exit 1
fi

echo "[ DONE ]"
