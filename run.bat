@echo off
title Recuperador de Datos - Iniciando...
cd /d "%~dp0"
echo Iniciando Recuperador de Datos Forense...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al ejecutar la aplicacion.
    pause
)

