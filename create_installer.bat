@echo off
chcp 65001 >nul
echo ==========================================
echo  CREANDO INSTALADOR PARA WINDOWS
echo ==========================================
echo.

:: Verificar que existe el EXE
if not exist "dist\GestorNotas.exe" (
    echo ERROR: No se encontró dist\GestorNotas.exe
    echo Ejecuta primero: build_windows.bat
    pause
    exit /b 1
)

:: Verificar Inno Setup
set INNO_PATH="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if not exist %INNO_PATH% (
    set INNO_PATH="C:\Program Files\Inno Setup 6\ISCC.exe"
)
if not exist %INNO_PATH% (
    echo ERROR: Inno Setup no encontrado
    echo Descarga e instala desde: https://jrsoftware.org/isinfo.php
    pause
    exit /b 1
)

:: Crear instalador
echo Compilando instalador con Inno Setup...
%INNO_PATH% "setup.iss"

:: Verificar resultado
if exist "installer\GestorNotas_Setup_v1.0.exe" (
    echo.
    echo ==========================================
    echo  ¡INSTALADOR CREADO EXITOSAMENTE!
    echo ==========================================
    echo Ubicación: installer\GestorNotas_Setup_v1.0.exe
    echo.
    echo Para instalar en otra PC, solo ejecuta este archivo.
    echo.
    start installer
) else (
    echo.
    echo ERROR: No se pudo crear el instalador
)

pause