@echo off
cd /d "%~dp0"
C:\Python314\python.exe -m pytest tests/e2e/test_live_e2e.py -v --tb=short %*
