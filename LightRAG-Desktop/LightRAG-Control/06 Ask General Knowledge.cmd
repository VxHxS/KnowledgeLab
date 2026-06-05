@echo off
for %%I in ("%~dp0Ask-General-Knowledge.ps1") do set "PS1=%%~sI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
