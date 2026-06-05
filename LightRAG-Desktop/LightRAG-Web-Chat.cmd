@echo off
setlocal
for %%I in ("%~dp0LightRAG-Web-Chat.ps1") do set "PS1=%%~sI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"

