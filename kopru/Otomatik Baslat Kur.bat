@echo off
chcp 65001 >nul
title Olcum Karti - otomatik baslatmayi kur

echo Windows acilisinda olcum karti PC koprusu arka planda baslasin mi?
echo   Baslangic klasorune bir kisayol konur (pythonw, konsolsuz).
echo   DIKKAT: arka plandaki kopru kartin COM portunu tutar; tezgah araclari
echo   ve yukle.py calisirken kopruyu kapatin.
echo.
pause

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0otomatik-baslat.ps1" -Kur
echo.
pause
