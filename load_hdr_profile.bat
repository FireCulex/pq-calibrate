@echo off
REM Navigate to the directory where ArgyllCMS tools and your profiles are located
cd /d "c:\calibrations"

REM Check if calibration is already loaded
dispwin -V -d1 "My_HDR_Display.icc" | findstr /C:"IS loaded" >nul
IF %ERRORLEVEL% EQU 0 (
    echo HDR profile is already active. Skipping reload.
) ELSE (
    echo Reloading HDR profile...
    dispwin -I -d1 "My_HDR_Display.icc"
    echo HDR profile loaded.
)

