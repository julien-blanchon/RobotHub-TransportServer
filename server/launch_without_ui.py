import logging
import os

import uvicorn

# Import the existing API

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("server.log")],
)

logger = logging.getLogger(__name__)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "localhost")

    logger.info("🤖 Starting RobotHub TransportServer API Server (Hot Reload Mode)...")
    logger.info(f"   - API available at: http://{host}:{port}/")
    logger.info(f"   - API docs at: http://{host}:{port}/docs")
    logger.info("   - Hot reload enabled for development")

    print(
        f"🤖 Starting RobotHub TransportServer API Server on {host}:{port} (Hot Reload)"
    )

    uvicorn.run(
        "src.api:app",
        host=host,
        port=port,
        reload=True,
        log_level="info",
    )
