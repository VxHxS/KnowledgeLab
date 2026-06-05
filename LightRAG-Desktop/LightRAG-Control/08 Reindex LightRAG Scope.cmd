@echo off
for %%I in ("%~dp0Reindex-LightRAG-Scope.ps1") do set "PS1=%%~sI"
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS1%"
