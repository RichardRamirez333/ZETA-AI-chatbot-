@echo off
title Building VERTEX Windows App...
cd /d "%~dp0"

echo =====================================
echo  Building VERTEX - Windows Executable
echo =====================================
echo.

:: Clean previous build
if exist "dist\VERTEX" rmdir /s /q "dist\VERTEX"
if exist "build\vertex" rmdir /s /q "build\vertex"

echo [1/4] Installing requirements...
pip install -r requirements.txt >nul 2>&1

echo [2/4] Building executable (this may take a minute)...
pyinstaller --onefile --windowed --name "VERTEX" --add-data "templates;templates" --add-data "statics;statics" --add-data "config.json;." --add-data "api_keys.json;." --add-data "database;database" --add-data "uploads;uploads" --hidden-import flask --hidden-import werkzeug --hidden-import cryptography --hidden-import requests --hidden-import webview --hidden-import bottle --hidden-import proxy_tools vertex_desktop.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [3/3] Build complete!
copy /y "%~dp0dist\VERTEX.exe" "%~dp0VERTEX.exe" >nul

echo.
echo =====================================
echo  SUCCESS!
echo =====================================
echo.
echo  Your desktop app is ready: VERTEX.exe
echo.
echo  Double-click VERTEX.exe to launch VERTEX in its own window
echo.
pause