@echo off
setlocal
for %%I in ("%~dp0Install-AI-Knowledge-Lab.ps1") do set "PS1=%%~sI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"

