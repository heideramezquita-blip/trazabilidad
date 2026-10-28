@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Instale primero con instalar.bat
  pause
  exit /b 1
)
set "PYTHONPATH=%~dp0src"
".venv\Scripts\python.exe" -m trazabilidad.cli reanudar %*
set "RESULTADO=%ERRORLEVEL%"
echo Codigo de salida: %RESULTADO%
pause
exit /b %RESULTADO%
