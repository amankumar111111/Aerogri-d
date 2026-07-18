import sys
from pathlib import Path

# Add backend to Python path so `app.*` imports resolve
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infrastructure.db import Base


@pytest.fixture
def anyio_backend():
    return "asyncio"
