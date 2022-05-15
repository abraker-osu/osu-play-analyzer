python -O -m PyInstaller -n osu-performance-analyzer ^
    --add-data venv\Lib\site-packages\tables.libs;tables.libs ^
    --onefile ^
    run.py
