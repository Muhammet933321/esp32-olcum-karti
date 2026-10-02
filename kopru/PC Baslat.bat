@echo off
chcp 65001 >nul
title Olcum Karti - PC uygulamasi
cd /d "%~dp0.."

echo Olcum Karti PC uygulamasi baslatiliyor...
echo   Panel: http://olcum.localhost:8770  (yalniz bu bilgisayar)
echo   Kart USB'nin "COM" soketinde olmali; takili degilse kopru bekler.
echo   Arka planda zaten calisiyorsa yalniz tarayici acilir.
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py kopru\pc.py %*
) else (
    python kopru\pc.py %*
)

if %errorlevel% neq 0 (
    echo.
    echo Kopru kapandi ya da acilamadi - yukaridaki mesaja bakin.
    pause
)
