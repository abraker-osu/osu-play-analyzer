@echo off

if NOT EXIST "venv" (
    echo No venv found
    EXIT /B 1
)

call venv\\Scripts\\activate.bat
if %ERRORLEVEL% GEQ 1 (
    echo Failed to activate virtual environment
    EXIT /B 1
)

if "%VIRTUAL_ENV%" == "" (
    echo Virtual environment not active
    EXIT /B 1
)

python src/run.py

echo [ DONE ]
