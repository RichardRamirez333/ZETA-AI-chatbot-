@echo off
title Building ZETA Windows App...
cd /d "%~dp0"

echo =====================================
echo  Building ZETA - Windows Executable
echo =====================================
echo.

:: Clean previous build
if exist "dist\ZETA" rmdir /s /q "dist\ZETA"
if exist "build\zeta" rmdir /s /q "build\zeta"

echo [1/4] Installing requirements...
pip install -r requirements.txt >nul 2>&1

echo [2/4] Building executable (this may take a minute)...
pyinstaller --onefile --windowed --name "ZETA" --add-data "templates;templates" --add-data "statics;statics" --add-data "config.json;." --add-data "api_keys.json;." --add-data "database;database" --add-data "uploads;uploads" --hidden-import flask --hidden-import werkzeug --hidden-import cryptography --hidden-import requests --hidden-import webview --hidden-import bottle --hidden-import proxy_tools zeta_desktop.py

if %errorlevel% neq 0 (
    echo [ERROR] Build failed!
    pause
    exit /b 1
)

echo [3/3] Build complete!
copy /y "%~dp0dist\ZETA.exe" "%~dp0ZETA.exe" >nul

echo.
echo =====================================
echo  SUCCESS!
echo =====================================
echo.
echo  Your desktop app is ready: ZETA.exe
echo.
echo  Double-click ZETA.exe to launch ZETA in its own window
echo.
pause