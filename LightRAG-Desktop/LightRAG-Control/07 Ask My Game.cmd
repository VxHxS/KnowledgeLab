@echo off
for %%I in ("%~dp0Ask-My-Game.ps1") do set "PS1=%%~sI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
