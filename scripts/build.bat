:: Description
::   Builds the project
::
:: Usage
::   > scripts\build.bat
@echo off

if NOT EXIST "venv_win" (
    echo No venv found
    EXIT /B 1
)

call "venv_win\Scripts\activate.bat"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to activate virtual environment
    EXIT /B 1
)

if "%VIRTUAL_ENV%" == "" (
    echo Virtual environment not active
    EXIT /B 1
)

call "$~dp0\clean.bat"

:: Build exe
del /s "dist\osu-performance-analyzer.exe" >nul 2>&1
pyinstaller -y "build.spec"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to build exe
    EXIT /B 1
)

:: Generate version file to set exe version
del /s "data\version.txt" >nul 2>&1
python "scripts\helper\gen_ver.py"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to generate version file
    EXIT /B 1
)

:: Set exe version (shown in file properties metadata)
pyi-set_version "data\version.txt" "dist\osu-performance-analyzer.exe"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to set version to exe
    EXIT /B 1
)

:: Copy res to dist
rd /s /q "dist\res"
mkdir "dist\res"
robocopy "res" "dist\res" /MIR /NJH /NJS
if %ERRORLEVEL% GEQ 8 (
    echo Failed to copy res to dist
    EXIT /B 1
)

:: Copy map_generator library to dist (used by map architect)
mkdir "dist\res\map_generator"
robocopy "venv_win\src\map_generator\src" "dist\res\map_generator" "*.py" /MIR /NJH /NJS
if %ERRORLEVEL% GEQ 8 (
    echo Failed to copy res to dist
    EXIT /B 1
)

:: zip relevant files
:: apprently tar can create zip files
:: https://superuser.com/questions/201371/create-zip-folder-from-the-command-line-windows#comment2831491_898508
del /s "dist\osu-performance-analyzer_win.zip" >nul 2>&1
tar -a -c -C "dist" -f "dist/osu-performance-analyzer_win.zip" "osu-performance-analyzer.exe" "res"
if %ERRORLEVEL% NEQ 0 (
    echo Failed to zip files
    EXIT /B 1whr
)

echo [ DONE ]
EXIT /B 0
