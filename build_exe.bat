@echo off
cd /d "%~dp0"

set PY=
where python >nul 2>nul && set PY=python
if not defined PY (where py >nul 2>nul && set PY=py)
if not defined PY (
  echo Python is not installed. Install it from python.org and tick "Add Python to PATH", then run this file again.
  pause
  exit /b 1
)

if not exist todo_widget.pyw (
  echo todo_widget.pyw must be in the same folder as this file.
  pause
  exit /b 1
)

echo Installing PyInstaller...
%PY% -m pip install --upgrade pyinstaller
if errorlevel 1 (
  echo Could not install PyInstaller. Check your internet connection.
  pause
  exit /b 1
)

copy /y todo_widget.pyw todo_widget_build.py >nul
echo Building the exe...
%PY% -m PyInstaller --noconsole --onefile --clean --name TodoWidget todo_widget_build.py
del todo_widget_build.py >nul 2>nul

if exist dist\TodoWidget.exe (
  copy /y dist\TodoWidget.exe TodoWidget.exe >nul
  rmdir /s /q build >nul 2>nul
  rmdir /s /q dist >nul 2>nul
  del TodoWidget.spec >nul 2>nul
  echo.
  echo Done. Your file is here: %~dp0TodoWidget.exe
) else (
  echo.
  echo Build failed. Please send me the messages above.
)
pause
