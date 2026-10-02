@echo off
chcp 65001 >nul
title Olcum Karti - otomatik baslatmayi kapat

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0otomatik-baslat.ps1" -Kaldir
echo.
pause
