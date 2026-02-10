@echo off
chcp 65001 >nul
echo ==========================================
echo  COMPILANDO GESTOR DE NOTAS PARA WINDOWS
echo ==========================================
echo.

:: Verificar entorno virtual
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: No se encontró el entorno virtual
    echo Crea uno con: python -m venv venv
    pause
    exit /b 1
)

:: Activar entorno virtual
echo [1/4] Activando entorno virtual...
call venv\Scripts\activate.bat

:: Limpiar compilaciones anteriores
echo [2/4] Limpiando compilaciones anteriores...
rmdir /s /q build 2>nul
rmdir /s /q dist 2>nul
rmdir /s /q installer 2>nul

:: Instalar/actualizar pyinstaller
echo [3/4] Verificando PyInstaller...
pip show pyinstaller >nul 2>&1
if errorlevel 1 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

:: Compilar ejecutable
echo [4/4] Compilando ejecutable...
pyinstaller --clean --onefile --windowed ^
    --name "GestorNotas" ^
    --add-data "data;data" ^
    --hidden-import customtkinter ^
    --hidden-import pandas ^
    --hidden-import openpyxl ^
    --hidden-import googleapiclient ^
    --hidden-import google_auth_httplib2 ^
    --hidden-import google_auth_oauthlib ^
    --hidden-import pydrive2 ^
    --hidden-import PIL ^
    --hidden-import sqlite3 ^
    --icon=NONE ^
    run.py

:: Verificar resultado
if not exist "dist\GestorNotas.exe" (
    echo.
    echo ==========================================
    echo  ERROR: No se pudo compilar
    echo ==========================================
    pause
    exit /b 1
)

echo.
echo ==========================================
echo  ¡EXE CREADO EXITOSAMENTE!
echo  Ubicación: dist\GestorNotas.exe
echo ==========================================
echo.
pause