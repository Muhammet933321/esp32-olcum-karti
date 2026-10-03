@echo off
chcp 65001 >nul
title Olcum Karti - kopruyu durdur
cd /d "%~dp0.."

rem Calisan PC koprusunu (arka plandaki de) KENDI ucundan durdurur: POST /kapat,
rem yalniz bu bilgisayardan. "pythonw.exe oldur" DEGIL - stok-takip de pythonw.
where py >nul 2>&1
if %errorlevel%==0 (
    py kopru\pc.py --durdur %*
) else (
    python kopru\pc.py --durdur %*
)
echo.
pause
