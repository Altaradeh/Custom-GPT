"""
Development server runner for the Custom GPT API
"""
import uvicorn
from models.api import app

if __name__ == "__main__":
    print("🚀 Starting Financial Analytics Custom GPT API")
    print("📊 Available endpoints:")
    print("   • POST /xmetric - Primary time series analysis")
    print("   • POST /ymetric - Secondary metrics analysis") 
    print("   • POST /portfolio/upload - Portfolio processing")
    print("   • POST /portfolio/upload-file - File upload")
    print("   • GET /docs - Interactive API documentation")
    print("   • GET /health - Health check")
    print("\n🌐 API will be available at: http://localhost:8000")
    print("📖 Documentation at: http://localhost:8000/docs")
    
    uvicorn.run(
        "models.api:app",
        host="0.0.0.0", 
        port=8000,
        reload=True,
        reload_dirs=["tools", "models"],
        log_level="info"
    )