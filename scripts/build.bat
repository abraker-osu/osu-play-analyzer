@echo off

echo Removing "build/..."
rd /s /q build

echo Removing "dist/..."
rd /s /q dist

python -O -m PyInstaller -n osu-performance-analyzer ^
    --collect-binaries=tables ^
    --onefile ^
    run.py

echo [DONE]
