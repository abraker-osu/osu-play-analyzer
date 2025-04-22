:: Description:
::   Runs a python file with the virtual environment activated
::
:: Usage:
::   > scripts/run.bat <python file>
::
:: Args
::   1: python file to run
@echo off

if NOT EXIST "venv_win" (
    echo No venv found
    EXIT /B 1
)

call "venv_win\Scripts\activate.bat"
if %ERRORLEVEL% GEQ 1 (
    echo Failed to activate virtual environment
    EXIT /B 1
)

if "%VIRTUAL_ENV%" == "" (
    echo Virtual environment not active
    EXIT /B 1
)

python %1

echo [ DONE ]
EXIT /B 0
