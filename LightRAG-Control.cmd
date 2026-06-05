@echo off
setlocal
for %%I in ("%~dp0LightRAG-Control.ps1") do set "PS1=%%~sI"
powershell -STA -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
