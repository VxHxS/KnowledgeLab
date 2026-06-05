@echo off
for %%I in ("%~dp0Import-Telegram-Export.ps1") do set "PS1=%%~sI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
