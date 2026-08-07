@echo off
REM ORIGAMI local sandbox — double-click or run from cmd
cd /d "%~dp0\.."
powershell -ExecutionPolicy Bypass -File "%~dp0run_sandbox.ps1" %*
