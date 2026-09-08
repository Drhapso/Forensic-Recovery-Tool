@echo off
title Recuperador de Datos Forense (Modo Administrador)
cd /d "%~dp0"

:: Comprobar permisos de administrador
net session >nul 2>&1
if %ERRORLEVEL% == 0 (
    echo Iniciando con privilegios de Administrador...
    python main.py
) else (
    echo Solicitando permisos de Administrador (UAC)...
    powershell -Command "Start-Process cmd -ArgumentList '/c cd /d ""%~dp0"" && python main.py' -Verb RunAs"
)

