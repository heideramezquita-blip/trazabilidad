@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (echo Instale primero & pause & exit /b 1)
set "PYTHONPATH=%~dp0src"
".venv\Scripts\python.exe" -m pytest
set "RESULTADO=%ERRORLEVEL%"
pause
exit /b %RESULTADO%
