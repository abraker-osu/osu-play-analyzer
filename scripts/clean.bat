:: Description
::   Cleans up the project
::
:: Usage
::   > scripts\clean.bat
::
:: Args
::   1: "all"  (optional)
::       all: Cleans logs and removes venv
@echo off

echo Removing ".eggs/..."
rd /s /q .eggs

echo Removing "build/..."
rd /s /q build

echo Removing "dist/..."
rd /s /q dist

echo Removing "pycache..."
python -Bc "import pathlib; import shutil; [ shutil.rmtree(path) for path in pathlib.Path('.').rglob('__pycache__') ]"

if "%1" == "all" (
    echo Removing "logs/..."
    rd /s /q logs

    echo Removing "venv_win/..."
    rd /s /q venv_win

    exit /B 0
)

if NOT EXIST "venv_win" (
    echo No venv found
    EXIT /B 1
)

call venv_win\\Scripts\\activate.bat
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment
    EXIT /B 1
)

if "%VIRTUAL_ENV%" == "" (
    echo Virtual environment not active
    EXIT /B 1
)

python -m pip cache purge

echo [ DONE ]
