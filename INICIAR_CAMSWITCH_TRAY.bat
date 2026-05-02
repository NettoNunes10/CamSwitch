@echo off
cd /d "%~dp0"
set "PYTHON=C:\Users\MASSA STREAM\AppData\Local\Programs\Python\Python314\python.exe"
"%PYTHON%" tray_app.py
if errorlevel 1 pause
