@echo off
setlocal
for %%I in ("%~dp0Game-Guard.ps1") do set "PS1=%%~sI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
