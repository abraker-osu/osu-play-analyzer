:: Description
::   Sets up the virtual environment and installs editable libraries
::   Also initializes/fixes submodules
::
:: Usage
::   > scripts\setup.bat install all
::
:: Args
::   1: "install"\"upgrade" (optional)
::       install: Installs python libraries if not already installed and initializes submodules
::       upgrade: Upgrades python libraries
::
::   2: "all"               (optional)
::       all: Installs requirements for each submodule as well
::
:: ENVIRONMENT VARIABLES
::   PYTHON: Python path
::   GIT:    Git path

@echo off
setlocal ENABLEDELAYEDEXPANSION

if not defined PYTHON set "PYTHON=python"
if not defined GIT    set "GIT=git"

echo Python path: %PYTHON%
echo Git path:    %GIT%

%PYTHON% --version
if !ERRORLEVEL! NEQ 0 (
    echo python not found
    EXIT /B 1
)

%GIT% --version
if !ERRORLEVEL! NEQ 0 (
    echo git not found
    EXIT /B 1
)

if NOT EXIST "venv_win\\Scripts" (
    echo No venv found. Creating...
    %PYTHON% -m venv venv_win

    if %ERRORLEVEL% NEQ 0 (
        echo Failed to create virtual environment
        EXIT /B 1
    )
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

%GIT% config core.longpaths true
if %ERRORLEVEL% NEQ 0 (
    echo Failed to set git longpaths!
    EXIT /B 1
)

if "%1" == "install" (
    python -m pip install -r requirements.txt
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to install editable libraries
        EXIT /B 1
    )
)

:: Upgrades project libraries
if "%1" == "upgrade" (
    python -m pip install --require-virtualenv --upgrade pip
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to upgrade pip!
        EXIT /B 1
    )

    python -m pip install --require-virtualenv --upgrade -r requirements.txt
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to upgrade editable libraries
        EXIT /B 1
    )

    echo.
)

:: Installs project libraries if not already installed
if "%1" == "install" (
    python -m pip install --require-virtualenv -r requirements.txt
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to install libraries
        EXIT /B 1
    )
)

if EXIST "%VIRTUAL_ENV%\src" (

    echo.
    dir /AD "%VIRTUAL_ENV%\src"
    echo.

    if "%2" == "all" (
        @REM Installs requirements for each submodule
        for /f "tokens=*" %%f in ('dir /b "%VIRTUAL_ENV%\src"') do (
            echo Processing "%VIRTUAL_ENV%\src\%%f\requirements.txt"
            if EXIST "%VIRTUAL_ENV%\src\%%f\requirements.txt" (
                python -m pip install --require-virtualenv -r "%VIRTUAL_ENV%\src\%%f\requirements.txt"
                if !ERRORLEVEL! NEQ 0 (
                    echo Failed to install requirements for "%VIRTUAL_ENV%\src\%%f"
                    EXIT /B 1
                )
            ) else (
                echo "%VIRTUAL_ENV%\src\%%f\requirements.txt" not found
            )
            echo.
        )
    )

    @REM Changes folders in "venv_win\src" from dashes to undescore
    python "scripts\helper\fix_submodule_path.py"
    if %ERRORLEVEL% NEQ 0 (
        echo Failed to fix src paths
        EXIT /B 1
    )

    @REM Initializes python editable libraries as submodules and adds them to git index
    python "scripts\helper\fix_submodule_git.py"

) else (
    echo "%VIRTUAL_ENV%\src" does not exist
)
echo.

python -m pip list
echo.

echo [ DONE ]
EXIT /B 0
