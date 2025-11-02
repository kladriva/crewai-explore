"""
VPS Monitoring AI - Main FastAPI Application
Entry point for the master server
"""
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from loguru import logger
import sys

from backend.config.settings import settings
from backend.database.connection import init_database
from backend.agents.crew_orchestrator import CrewOrchestrator
from backend.ml.anomaly_detector import AnomalyDetector

# Configure loguru
logger.remove()
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>",
    level=settings.log_level
)
logger.add(
    "logs/app.log",
    rotation="100 MB",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function} - {message}",
    level=settings.log_level
)


# Global instances
crew_orchestrator: CrewOrchestrator = None
anomaly_detector: AnomalyDetector = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan events for startup and shutdown"""
    global crew_orchestrator, anomaly_detector
    
    # Startup
    logger.info("🚀 Starting VPS Monitoring AI System...")
    logger.info(f"Environment: {settings.environment}")
    logger.info(f"Debug Mode: {settings.debug}")
    
    try:
        # Initialize database
        logger.info("Initializing database...")
        init_database()
        
        # Initialize CrewAI Orchestrator
        logger.info("Initializing CrewAI Orchestrator...")
        crew_orchestrator = CrewOrchestrator()
        
        # Initialize ML Anomaly Detector
        logger.info("Initializing ML Anomaly Detector...")
        anomaly_detector = AnomalyDetector()
        
        logger.success("✅ System initialization complete!")
    
    except Exception as e:
        logger.error(f"❌ Failed to initialize system: {e}")
        raise
    
    yield
    
    # Shutdown
    logger.info("🛑 Shutting down VPS Monitoring AI System...")


# Create FastAPI app
app = FastAPI(
    title="VPS Monitoring AI",
    description="Intelligent VPS monitoring system with multi-agent AI orchestration",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "environment": settings.environment,
        "version": "1.0.0"
    }


# API Root
@app.get("/", tags=["Root"])
async def root():
    """API root endpoint"""
    return {
        "message": "VPS Monitoring AI API",
        "version": "1.0.0",
        "docs": "/api/docs",
        "health": "/health"
    }


# Example endpoint - Get system status
@app.get("/api/v1/status", tags=["System"])
async def get_system_status():
    """Get overall system status"""
    return {
        "status": "operational",
        "agents": {
            "observer": "active",
            "analyzer": "active",
            "executor": "active",
            "alerter": "active"
        },
        "ml_models": {
            "isolation_forest": "loaded",
            "lstm": "loaded"
        },
        "database": "connected",
        "timestamp": "2025-11-01T23:52:51Z"
    }


# Example endpoint - Process metrics (will be called by gRPC in production)
@app.post("/api/v1/metrics/process", tags=["Metrics"])
async def process_metrics(metrics_data: dict):
    """
    Process incoming metrics through CrewAI pipeline
    
    In production, this is called internally when gRPC receives metrics from slaves
    This HTTP endpoint is for testing/debugging purposes
    """
    try:
        # Get ML predictions
        ml_predictions = anomaly_detector.predict(
            current_metrics=metrics_data.get("system_metrics", {}),
            historical_sequence=metrics_data.get("historical_data", [])
        )
        
        # Process through CrewAI orchestrator
        result = await crew_orchestrator.process_metrics(
            metrics_data=metrics_data,
            ml_predictions=ml_predictions,
            historical_data=metrics_data.get("historical_data", []),
            recent_alerts=[]  # Would fetch from DB in production
        )
        
        return {
            "status": "success",
            "result": result
        }
    
    except Exception as e:
        logger.error(f"Error processing metrics: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to process metrics: {str(e)}"
        )


# Exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host=settings.master_host,
        port=settings.master_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )
