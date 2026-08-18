from contextlib import asynccontextmanager
from fastapi import FastAPI
import redis.asyncio as aioredis
from app.core.settings import settings
from app.db.session import engine 
import structlog

logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # ==========================================
    # STARTUP: Code here runs before the app accepts requests
    # ==========================================
    logger.info("Starting Eveto API", env=settings.env)
    
    # Initialize Redis connection pool and attach to app state
    app.state.redis = aioredis.from_url(
        str(settings.redis.url), 
        decode_responses=True
    )
    
    yield  # The app runs and handles requests here
    
    # ==========================================
    # SHUTDOWN: Code here runs when the app is stopping
    # ==========================================
    logger.info("Shutting down Eveto API")
    
    # Close Redis
    if app.state.redis:
        await app.state.redis.close()
        
    # Dispose of DB connections
    await engine.dispose() 