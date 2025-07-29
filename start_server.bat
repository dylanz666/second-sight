@echo off
echo Starting Remote Viewer Server...
echo.
echo Make sure you have installed the required packages:
echo pip install fastapi uvicorn pillow pywin32
echo.
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
python server.py
pause 