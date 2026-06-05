@echo off
setlocal
set "LAB=%~dp0"
set "PY=%LAB%LightRAG\.venv\Scripts\pythonw.exe"
if not exist "%PY%" set "PY=%LAB%LightRAG\.venv\Scripts\python.exe"
start "" "%PY%" "%LAB%scripts\telegram_sync_app.py"
