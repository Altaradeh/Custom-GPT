@echo off
REM Startup script for Long-Term Financial Market Simulation API (Windows)

echo 🚀 Starting Long-Term Financial Market Simulation API...

REM Check if data files exist
if not exist "Long Term Model\Long Term Model\final_path_statistics_library.csv" (
    echo ❌ Error: final_path_statistics_library.csv not found!
    echo Please ensure data files are in the correct directory structure.
    pause
    exit /b 1
)

if not exist "Long Term Model\Long Term Model\param_library.csv" (
    echo ❌ Error: param_library.csv not found!
    echo Please ensure data files are in the correct directory structure.
    pause
    exit /b 1
)

echo ✅ Data files found

REM Install dependencies if requirements.txt exists
if exist "requirements.txt" (
    echo 📦 Installing dependencies...
    pip install -r requirements.txt
)

REM Start the application
echo 🌟 Starting FastAPI application...
echo 🌐 API will be available at: http://localhost:8000
echo 📚 Documentation available at: http://localhost:8000/docs
echo.

uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
