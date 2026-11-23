@echo off
chcp 65001 >nul
title Projekt-Dashboard
echo ============================================================
echo   Projekt-Dashboard wird gestartet ...
echo ============================================================
echo.

cd /d "%~dp0"

set "PY="
where python >nul 2>nul && set "PY=python"
if not defined PY where py >nul 2>nul && set "PY=py"
if defined PY goto :found
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python312\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
if not defined PY if exist "%LOCALAPPDATA%\Programs\Python\Python311\python.exe" set "PY=%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
if not defined PY if exist "C:\Program Files\Python313\python.exe" set "PY=C:\Program Files\Python313\python.exe"
if not defined PY if exist "C:\Program Files\Python312\python.exe" set "PY=C:\Program Files\Python312\python.exe"
if not defined PY goto :nopython

:found
echo Python gefunden: %PY%
echo.
echo [1/2] Abhaengigkeiten werden geprueft/installiert (nur beim ersten Start laenger) ...
"%PY%" -m pip install -r requirements.txt
echo.
echo [2/2] Dashboard-Server startet ...
echo Danach oeffnet sich der Browser automatisch unter http://localhost:8000
echo.
echo WICHTIG: dieses Fenster NICHT schliessen, solange das Dashboard laeuft.
echo Beenden: Strg + C druecken oder dieses Fenster schliessen.
echo.
start "" cmd /c "timeout /t 6 /nobreak >nul && start http://localhost:8000"
"%PY%" -m uvicorn backend.main:app --reload --port 8000
goto :end

:nopython
echo ============================================================
echo  FEHLER: Python wurde nicht gefunden!
echo ============================================================
echo.
echo Bitte Python einmalig installieren:
echo   1. Microsoft Store oeffnen (Startmenue - "Microsoft Store")
echo   2. Dort "Python 3.13" suchen und installieren
echo   3. Danach diese Datei erneut per Doppelklick starten
echo.
echo Alternativ: https://www.python.org/downloads/
echo   - beim Installer HAKEN bei "Add python.exe to PATH" setzen!
echo.
pause
goto :eof

:end
echo.
echo Server wurde beendet.
pause
