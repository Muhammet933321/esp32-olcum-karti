@echo off
chcp 65001 >nul
title Olcum Karti — PC Koprusu
cd /d "%~dp0"

echo Olcum Karti PC koprusu baslatiliyor...
echo   Kart USB ile bagli olmali. Arduino seri monitoru ACIKSA kapatin —
echo   portu tek bir program tutabilir.
echo.

where py >nul 2>&1
if %errorlevel%==0 (
    py kopru\kopru.py %*
) else (
    python kopru\kopru.py %*
)

if %errorlevel% neq 0 (
    echo.
    echo Kopru kapandi. Kart takili mi, port mesgul mu?
    echo Donanimsiz denemek icin:  Kopru Baslat.bat --kayit kopru\arsiv\GUN.satir
    pause
)
