@echo off
REM Build SuccFrame.exe with PyInstaller (one-file, no console window).
REM Run this from the project folder: double-click it, or `build.bat` in a terminal.

echo Installing/updating build tools...
python -m pip install --upgrade pyinstaller >nul

echo Building SuccFrame.exe...
python -m PyInstaller ^
  --noconfirm ^
  --onefile ^
  --windowed ^
  --name SuccFrame ^
  --icon "assets\logo.ico" ^
  --add-data "assets;assets" ^
  main.py

echo.
echo Done. The exe is in the "dist" folder: dist\SuccFrame.exe
pause
