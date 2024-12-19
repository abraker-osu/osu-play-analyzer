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

@REM :: When pip installs editable modules via setuptools, it applies PEP 503
@REM :: (https://peps.python.org/pep-0503/#normalized-names). This requires modules'
@REM :: names to be "normalized" form for web/system compatibility. Unfortunately,
@REM :: setuptools applies this to the module directory as well, causing python
@REM :: imports to break. Setuptools fixes this via the __editable__.* python hooks
@REM :: in venv, which depends on specific directories contiaining dashes. As such,
@REM :: the renaming above breaks python imports. This is solved by creating another
@REM :: python hook below to fix the search paths.
@REM ::
@REM :: NOTE: Assumes nothing else generates sitecustomize.py
@REM set hook_file=%VIRTUAL_ENV%\Lib\site-packages\sitecustomize.py
@REM del /s /Q "%hook_file%" >nul 2>&1

@REM :: Create a 'sitecustomize.py' file
@REM :: Python automatically runs this before importing any modules
@REM :: This edits paths to allow module import from workspace root
@REM ::
@REM :: NOTE: '^' is used to escape the parenthesis
@REM echo import sys > "%hook_file%"
@REM echo sys.path.insert^(0, f'{sys.prefix}\\src'^) >> "%hook_file%"

@REM if NOT EXIST "%hook_file%" (
@REM     echo Failed to create sitecustomize.py
@REM     EXIT /B 1
@REM )

echo [ DONE ]
