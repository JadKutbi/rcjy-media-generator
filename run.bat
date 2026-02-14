@echo off
cd /d "%~dp0"
if "%GEMINI_API_KEY%"=="" (
    echo GEMINI_API_KEY not set. Add it as env var or to .env file.
    echo Get a free key: https://aistudio.google.com/apikey
    echo.
)
python -m pip install -q -r requirements.txt
python -m streamlit run app.py
