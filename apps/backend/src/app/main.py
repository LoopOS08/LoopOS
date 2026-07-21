from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.db.database import init_db
from app.api import health, auth, companies, integrations, artifacts, agents, query, webhooks, approvals, mcp, rest_connectors
import contextlib
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO if settings.DEBUG else logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_db()
    yield
    # Shutdown
    pass


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="LoopOS API - Connective Intelligence Layer for SMB Operations",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(health.router, prefix="/api/health", tags=["health"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(companies.router, prefix="/api/companies", tags=["companies"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["integrations"])
app.include_router(artifacts.router, prefix="/api/artifacts", tags=["artifacts"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])
app.include_router(query.router, prefix="/api/query", tags=["query"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["webhooks"])
app.include_router(approvals.router, prefix="/api/approvals", tags=["approvals"])
app.include_router(mcp.router, prefix="/api/mcp", tags=["mcp"])
app.include_router(rest_connectors.router, prefix="/api/rest-connectors", tags=["rest-connectors"])


@app.get("/")
async def root():
    return {
        "message": "LoopOS API",
        "version": settings.APP_VERSION,
        "status": "operational"
    }