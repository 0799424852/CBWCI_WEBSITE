@echo off
cd /d %~dp0
if not exist venv ( py -3 -m venv venv )
call venv\Scripts\activate
pip install -r requirements.txt
if "%1"=="dev" ( set FLASK_DEBUG=true & python app.py ) else ( python serve.py )
