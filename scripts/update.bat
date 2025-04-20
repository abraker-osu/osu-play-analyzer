:: Description
::   Updates the submodules to latest main/master
::
:: Usage
::   > scripts\update.bat all
::
:: Args
::   1: "all" (optional)
::       all: Update python libraries as well

@echo off
SETLOCAL ENABLEDELAYEDEXPANSION

if not defined PYTHON set "PYTHON=python"
if not defined GIT    set "GIT=git"

echo Python path: %PYTHON%
echo Git path:    %GIT%

%PYTHON% --version
if !ERRORLEVEL! NEQ 0 (
    echo python not found
    exit /B 1
)

%GIT% --version
if !ERRORLEVEL! NEQ 0 (
    echo git not found
    exit /B 1
)
echo.

for /d %%f in ("venv_win\src\*") do (
    echo Updating %%f...
    pushd %%f

    %GIT% fetch origin
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to fetch
        EXIT /B 1
    )

    @REM Check if 'main' branch exists
    %GIT% show-ref --verify --quiet refs/heads/main
    if !ERRORLEVEL! EQU 0 (
        %GIT% checkout main
        if !ERRORLEVEL! NEQ 0 (
            echo Failed to checkout main
            EXIT /B 1
        )

        %GIT% pull origin main
    ) else (
        @REM Check if 'master' branch exists
        %GIT% show-ref --verify --quiet refs/heads/master
        if !ERRORLEVEL! EQU 0 (
            %GIT% checkout master
            if !ERRORLEVEL! NEQ 0 (
                echo Failed to checkout master
                EXIT /B 1
            )

            %GIT% pull origin master
        )
    )

    popd
    echo.
)

if "%1" == "all" (
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

    echo Updating pip...
    python -m pip install --upgrade pip
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to upgrade pip
        EXIT /B 1
    )

    echo Updating python libraries...
    python -m pip install --upgrade -r requirements.txt
    if !ERRORLEVEL! NEQ 0 (
        echo Failed to install python libraries
        EXIT /B 1
    )

    echo.
)

echo [ DONE ]
EXIT /B 0
