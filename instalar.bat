@echo off
setlocal
cd /d "%~dp0"
echo === Instalador del cargador local ===
where py >nul 2>&1
if not errorlevel 1 (
  py -3.13 -c "import struct,sys;sys.exit(0 if sys.version_info[:2] == (3,13) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
  if not errorlevel 1 (set "PY=py -3.13" & goto python_ok)
)
where python >nul 2>&1
if not errorlevel 1 (
  python -c "import struct,sys;sys.exit(0 if sys.version_info[:2] == (3,13) and struct.calcsize('P')*8 == 64 else 1)" >nul 2>&1
  if not errorlevel 1 (set "PY=python" & goto python_ok)
)
echo ERROR: Instale Python 3.13 de 64 bits desde https://www.python.org/downloads/windows/
echo Luego ejecute instalar.bat de nuevo. No se requieren permisos de administrador.
pause
exit /b 1
:python_ok
if not exist ".venv\Scripts\python.exe" (
  %PY% -m venv ".venv"
  if errorlevel 1 goto error
)
".venv\Scripts\python.exe" -m pip install --disable-pip-version-check -r "requirements.txt"
if errorlevel 1 goto error
echo INSTALACION TERMINADA. Para Edge no se descargan navegadores extra.
echo Alternativa Chromium: ".venv\Scripts\python.exe" -m playwright install chromium
pause
exit /b 0
:error
echo ERROR al preparar el entorno. Consulte README.md.
pause
exit /b 1
