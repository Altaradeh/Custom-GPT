# PowerShell setup script for Long-Term Financial Market Simulation API
# Run with: powershell -ExecutionPolicy Bypass -File setup.ps1

Write-Host "🚀 Setting up Long-Term Financial Market Simulation API..." -ForegroundColor Green

# Check if Python is installed
try {
    $pythonVersion = python --version 2>&1
    Write-Host "✅ Found Python: $pythonVersion" -ForegroundColor Green
}
catch {
    Write-Host "❌ Python not found! Please install Python 3.8+ first." -ForegroundColor Red
    Write-Host "Download from: https://www.python.org/downloads/" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

# Check if data files exist
$dataDir = "Long Term Model\Long Term Model"
$libraryFile = "$dataDir\final_path_statistics_library.csv"
$paramFile = "$dataDir\param_library.csv"

if (!(Test-Path $libraryFile)) {
    Write-Host "❌ Error: final_path_statistics_library.csv not found!" -ForegroundColor Red
    Write-Host "Expected location: $libraryFile" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

if (!(Test-Path $paramFile)) {
    Write-Host "❌ Error: param_library.csv not found!" -ForegroundColor Red
    Write-Host "Expected location: $paramFile" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "✅ Data files found" -ForegroundColor Green

# Install pip if not available
try {
    pip --version | Out-Null
    Write-Host "✅ pip is available" -ForegroundColor Green
}
catch {
    Write-Host "❌ pip not found! Please ensure pip is installed with Python." -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Install dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Blue
try {
    pip install -r requirements.txt
    Write-Host "✅ Dependencies installed successfully" -ForegroundColor Green
}
catch {
    Write-Host "❌ Failed to install dependencies" -ForegroundColor Red
    Write-Host "Error: $($_.Exception.Message)" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "🎉 Setup completed successfully!" -ForegroundColor Green
Write-Host ""
Write-Host "To start the API server, run:" -ForegroundColor Yellow
Write-Host "  .\start.bat" -ForegroundColor Cyan
Write-Host "  OR" -ForegroundColor Yellow
Write-Host "  uvicorn main:app --host 0.0.0.0 --port 8000 --reload" -ForegroundColor Cyan
Write-Host ""
Write-Host "The API will be available at:" -ForegroundColor Yellow
Write-Host "  🌐 Main API: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  📚 Documentation: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "  🏥 Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to continue"
