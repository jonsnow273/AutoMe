@echo off
title AutoMe Launcher
cd /d %~dp0

powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run_desktop.ps1"
