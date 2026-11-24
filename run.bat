@echo off
title Student Academic Performance Analyzer
cd /d "%~dp0"
echo =================================================================
echo   Starting Academic Performance Analyzer...
echo   Opening in your browser: http://localhost:8000
echo   Default Credentials: admin / admin123
echo =================================================================
python run.py
pause
