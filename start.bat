@echo off
title YouTube Downloader Web
color 07
cls

echo ========================================
echo   YouTube Downloader - Web App
echo ========================================
echo.

echo Starting server...
echo Open: http://localhost:8000
echo Close this window to stop the server.
echo.

venv\Scripts\python main.py

echo.
echo Server has stopped.
pause