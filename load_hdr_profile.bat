@echo off
REM Navigate to the directory where ArgyllCMS tools and your profiles are located
cd /d "c:\calibrations"

set CALFILE=pq_bt2390_400nits.cal

REM Check HDR status and store result
set HDRMODE=UNKNOWN
for /f "tokens=*" %%i in ('HdrSwitcher.exe status --index 0') do (
    echo %%i | findstr /i "SDR" >nul
    if not errorlevel 1 (
        set HDRMODE=SDR
    )
)

REM Use delayed expansion to access updated variables
setlocal enabledelayedexpansion

if "!HDRMODE!"=="SDR" (
    echo Display is in SDR mode.

    REM Check if calibration is loaded
    dispwin -V -d1 "%CALFILE%" | findstr /C:"IS loaded" >nul
    if !ERRORLEVEL! EQU 0 (
        echo HDR calibration is active. Clearing calibration...
        dispwin -c -d1
    ) else (
        echo No action needed.
    )
) else (
    echo Display is in HDR mode.

    REM Check if calibration is loaded
    dispwin -V -d1 "%CALFILE%" | findstr /C:"IS loaded" >nul
    if !ERRORLEVEL! EQU 0 (
        echo HDR profile already active. 
    ) else (
        dispwin -d1 "%CALFILE%"
        echo HDR profile loaded.
    )
)

endlocal