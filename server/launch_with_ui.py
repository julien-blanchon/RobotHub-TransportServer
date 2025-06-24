import logging
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

# Import the existing API
from src.api import app as api_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("server.log")],
)

logger = logging.getLogger(__name__)

# Create a new FastAPI app that combines API and frontend
app = FastAPI(
    title="LeRobot Arena Transport Server with UI",
    description="Combined API and web interface for LeRobot Arena transport server",
    version="2.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Add the health endpoint BEFORE other routes to avoid conflicts
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "server_running": True,
        "frontend_enabled": os.getenv("SERVE_FRONTEND", "false").lower() == "true",
        "api_available": True,
    }


# Mount the API under /api prefix
app.mount("/api", api_app)

# Check if we should serve frontend
serve_frontend = os.getenv("SERVE_FRONTEND", "false").lower() == "true"

if serve_frontend:
    # Get the frontend static files path
    frontend_path = Path(__file__).parent.parent / "static-frontend"

    if frontend_path.exists():
        logger.info(f"Serving frontend from: {frontend_path}")

        # Mount static files (JS, CSS, etc.)
        app.mount("/static", StaticFiles(directory=frontend_path), name="static")

        # Serve the main app for all other routes (SPA)
        @app.get("/{full_path:path}")
        async def serve_frontend_app(full_path: str):
            """Serve the SvelteKit app for all non-API routes."""
            # Don't serve frontend for API routes
            if full_path.startswith("api/"):
                return {"error": "API route not found"}

            # Check if requesting a specific file
            file_path = frontend_path / full_path
            if file_path.is_file():
                return FileResponse(file_path)

            # For all other routes, serve the main index.html (SPA behavior)
            index_path = frontend_path / "index.html"
            if index_path.exists():
                return FileResponse(index_path)
            return {"error": "Frontend not available"}

    else:
        logger.warning(f"Frontend path not found: {frontend_path}")

        @app.get("/")
        async def no_frontend():
            return {
                "message": "LeRobot Arena Transport Server",
                "frontend": "not available",
                "api": "available at /api/",
                "docs": "available at /api/docs",
            }

else:

    @app.get("/")
    async def api_only():
        return {
            "message": "LeRobot Arena Transport Server - API Only",
            "api": "available at /api/",
            "docs": "available at /api/docs",
        }


if __name__ == "__main__":
    port = int(os.getenv("PORT", 7860))
    host = os.getenv("HOST", "0.0.0.0")

    logger.info("🤖 Starting LeRobot Arena Combined Server...")
    logger.info(f"   - API available at: http://{host}:{port}/api/")
    logger.info(f"   - API docs at: http://{host}:{port}/api/docs")

    if serve_frontend:
        logger.info(f"   - Frontend available at: http://{host}:{port}/")
    else:
        logger.info("   - Frontend disabled (set SERVE_FRONTEND=true to enable)")

    print(f"🤖 Starting LeRobot Arena Combined Server on {host}:{port}")

    uvicorn.run(
        "launch_with_ui:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
