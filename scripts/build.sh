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
rm -f "dist/osu-performance-analyzer" 2>/dev/null
pyinstaller -y "build.spec"
if [ $? -ne 0 ]; then
    echo "Failed to build exe"
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
rm -f "dist/osu-performance-analyzer.zip" 2>/dev/null

pushd "dist"
zip "osu-performance-analyzer.zip" "osu-performance-analyzer" "res"
if [ $? -ne 0 ]; then
    echo "Failed to zip files"
    popd
    exit 1
fi
popd

echo "[ DONE ]"
