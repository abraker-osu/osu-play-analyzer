@echo off

if NOT EXIST "venv_win\\Scripts" (
    echo No venv found. Creating...
    python -m venv venv_win

    if %ERRORLEVEL% GEQ 1 (
        echo Failed to create virtual environment
        EXIT /B 1
    )
)

call venv_win\\Scripts\\activate.bat
if %ERRORLEVEL% GEQ 1 (
    echo Failed to activate virtual environment
    EXIT /B 1
)

if "%VIRTUAL_ENV%" == "" (
    echo Virtual environment not active
    EXIT /B 1
)

git config core.longpaths true
if %ERRORLEVEL% GEQ 1 (
    echo Failed to set git longpaths!
    EXIT /B 1
)

if "%1" == "install" (
    python -m pip install -r requirements.txt
    if %ERRORLEVEL% GEQ 1 (
        echo Failed to install editable libraries!
        EXIT /B 1
    )
)

:: Changes folders in venv_win/src from dashes to undescore
python "scripts\\helper\\src_fix.py"
if %ERRORLEVEL% GEQ 1 (
    echo Failed to fix src paths
    EXIT /B 1
)

echo [ DONE ]
