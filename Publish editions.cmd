@echo off
rem Double-click this to put the printed magazine on archive.org.
rem It signs you in the first time, then uploads. Stop it whenever you like —
rem re-running picks up where it left off.
title Beis Moshiach - publish print editions
cd /d "%~dp0"
python tools\upload_editions.py %*
echo.
echo ---------------------------------------------------------------
echo Finished. Close this window, or leave it open to read the log.
pause
