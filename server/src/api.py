import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("server.log")],
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager (preserves original startup/shutdown)."""

    # Startup
    async def _startup():
        # Wait 0.1s before starting
        await asyncio.sleep(0.1)
        print("Starting server...")

    await _startup()

    yield

    # Shutdown
    async def _shutdown():
        # Wait 0.1s before shutting down
        await asyncio.sleep(0.1)
        print("Shutting down server...")

    await _shutdown()


# FastAPI application (preserves original configuration)
app = FastAPI(
    title="LeRobot Arena Server",
    description="WebRTC video streaming server for robotics applications",
    version="2.0.0",
    lifespan=lifespan,
)

# CORS middleware (preserves original settings)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from .robotics.api import robotics_router
from .video.api import video_router

# Include the API routers
app.include_router(video_router)
app.include_router(robotics_router)


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "server_running": True,
    }


if __name__ == "__main__":
    import uvicorn

    logger.info("🤖 Starting LeRobot Arena Modular Server...")
    print("🤖 Starting LeRobot Arena Modular Server...")
    uvicorn.run(
        "api:app",
        reload=False,
        log_level="info",
    )
