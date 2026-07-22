from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import MetaData
from app.core.config import settings
from typing import Optional
import logging

logger = logging.getLogger(__name__)

_engine = None
_async_session_local = None

# Base class for models
Base = declarative_base()

# Metadata for migrations
metadata = MetaData()


def get_engine():
    global _engine
    if _engine is None:
        _engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            future=True
        )
    return _engine


def get_async_session_local():
    global _async_session_local
    if _async_session_local is None:
        _async_session_local = async_sessionmaker(
            get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
            autocommit=False,
            autoflush=False
        )
    return _async_session_local


async def get_db() -> AsyncSession:
    session = get_async_session_local()
    async with session() as db_session:
        try:
            yield db_session
        finally:
            await db_session.close()


async def init_db():
    engine = get_engine()
    async with engine.begin() as conn:
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
        from app.models.mcp_server import MCPServer
        from app.models.rest_connector import RESTConnector
        from app.models.webhook_config import WebhookConfig
        
        await conn.run_sync(Base.metadata.create_all)