@echo off

python -O -m PyInstaller -n osu-performance-analyzer ^
    --collect-binaries=tables ^
    --onefile ^
    run.py

echo [DONE]
