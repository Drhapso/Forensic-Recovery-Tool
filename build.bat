@echo off
chcp 65001 >nul
title Compilador Autónomo - Suite Forense y Edición Demo

echo ======================================================================
echo    COMPILADOR DE EJECUTABLES PORTABLES (SUITE FORENSE & DEMO 24H)
echo ======================================================================
echo.

python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [ERROR] No se detectó Python en el sistema. Asegúrese de tener Python instalado.
    pause
    exit /b 1
)

echo Verificando PyInstaller...
python -c "import PyInstaller" >nul 2>&1
if %errorlevel% neq 0 (
    echo Instalando PyInstaller...
    pip install pyinstaller
)

if "%1"=="--demo" goto compile_demo
if "%1"=="--commercial-only" goto compile_commercial_only
if "%1"=="--all" goto compile_all
if "%1"=="--full" goto compile_all

:menu
echo.
echo Seleccione la opción de compilación:
echo   [1] Compilar Comercial y Demo para Testers (Recomendado - Sincronizado)
echo   [2] Compilar Únicamente Versión Comercial (RecuperadorDeDatos.exe)
echo   [3] Compilar Únicamente Versión DEMO 24 Horas (Forensic_Recovery_DEMO.exe)
echo   [4] Salir
echo.
set /p opt="Ingrese una opción (1-4): "

if "%opt%"=="1" goto compile_all
if "%opt%"=="2" goto compile_commercial_only
if "%opt%"=="3" goto compile_demo
if "%opt%"=="4" exit /b 0
echo Opción inválida. Intente de nuevo.
goto menu

:compile_all
echo.
echo ======================================================================
echo  Compilando Aplicativo Comercial y Demo para Testers en Sincronía...
echo ======================================================================
python build_exe.py
goto end

:compile_commercial_only
echo.
echo ======================================================================
echo  Compilando Únicamente Versión Comercial (RecuperadorDeDatos.exe)...
echo ======================================================================
python build_exe.py --no-demo
goto end

:compile_demo
echo.
echo ======================================================================
echo  Compilando Únicamente Versión DEMO 24 Horas (Forensic_Recovery_DEMO.exe)...
echo ======================================================================
python build_demo.py
goto end

:end
echo.
echo Proceso finalizado. Revise la carpeta 'dist\'.
pause
