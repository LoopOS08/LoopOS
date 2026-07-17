from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
from app.core.config import settings

# Database engine
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    future=True
)

# Async session factory
AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False
)

# Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


async def get_db() -> AsyncSession:
    """Dependency for getting async database sessions"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def init_db():
    """Initialize database tables"""
    async with engine.begin() as conn:
        # Import all models here to ensure they're registered
        from app.models.company import Company
        from app.models.user import User
        from app.models.integration import Integration
        from app.models.artifact import Artifact
        from app.models.goal import Goal
        from app.models.decision import Decision
        from app.models.agent_action import AgentAction
        from app.models.outcome import Outcome
        from app.models.spec import Spec
        from app.models.agent_intelligence import AgentIntelligence
        
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)