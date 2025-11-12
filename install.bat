@echo off
REM Faderfox MX12 Control Surface - Installation Script (Windows)

echo.
echo ============================================
echo   Faderfox MX12 Control Surface - Installer
echo ============================================
echo.

REM Set installation path
set INSTALL_PATH=%USERPROFILE%\Documents\Ableton\User Library\Remote Scripts\FaderfoxMX12byYVMA

echo Installing to: %INSTALL_PATH%
echo.

REM Create directory
echo Creating directory...
if not exist "%INSTALL_PATH%" mkdir "%INSTALL_PATH%"

REM Copy files
echo Copying files...
xcopy /E /I /Y RemoteScript\src\* "%INSTALL_PATH%\"

REM Verify installation
if exist "%INSTALL_PATH%\FaderfoxMX12byYVMA.py" (
    echo.
    echo ========================================
    echo   Installation complete!
    echo ========================================
    echo.
    echo Next steps:
    echo   1. Restart Ableton Live
    echo   2. Go to Preferences - Link, Tempo ^& MIDI
    echo   3. Set Control Surface to 'FaderfoxMX12byYVMA'
    echo   4. Set Input/Output to 'Faderfox MX12'
    echo.
    echo For detailed setup, see README.md
    echo.
) else (
    echo.
    echo ========================================
    echo   Installation failed
    echo ========================================
    echo.
    echo Please install manually ^(see README.md^)
    echo.
)

pause
