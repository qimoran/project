@echo off
setlocal
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0docker-bigdata.ps1" %*
