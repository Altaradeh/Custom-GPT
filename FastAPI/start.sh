#!/bin/bash
# Startup script for Long-Term Financial Market Simulation API

echo "🚀 Starting Long-Term Financial Market Simulation API..."

# Check if data files exist
if [ ! -f "Long Term Model/Long Term Model/final_path_statistics_library.csv" ]; then
    echo "❌ Error: final_path_statistics_library.csv not found!"
    echo "Please ensure data files are in the correct directory structure."
    exit 1
fi

if [ ! -f "Long Term Model/Long Term Model/param_library.csv" ]; then
    echo "❌ Error: param_library.csv not found!"
    echo "Please ensure data files are in the correct directory structure."
    exit 1
fi

echo "✅ Data files found"

# Install dependencies if requirements.txt exists
if [ -f "requirements.txt" ]; then
    echo "📦 Installing dependencies..."
    pip install -r requirements.txt
fi

# Start the application
echo "🌟 Starting FastAPI application..."
echo "🌐 API will be available at: http://localhost:8000"
echo "📚 Documentation available at: http://localhost:8000/docs"
echo ""

uvicorn main:app --host 0.0.0.0 --port 8000 --reload
