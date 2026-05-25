import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession
)
from sqlalchemy.orm import sessionmaker, declarative_base

# Carregar variáveis de ambiente
load_dotenv()

# DATABASE_URL deve ser algo como:
#   postgresql+asyncpg://user:senha@host:5432/banco
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@db-sys-localidades:5432/sys_localidades")

# -----------------------------------------
# ENGINE ASSÍNCRONO
# -----------------------------------------
engine = create_async_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

# -----------------------------------------
# SESSIONMAKER ASSÍNCRONO
# -----------------------------------------
AsyncSessionLocal = sessionmaker(
    bind=engine,
    class_=AsyncSession,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
)

# -----------------------------------------
# MODELS BASE
# -----------------------------------------
Base = declarative_base()

# -----------------------------------------
# DEPENDENCY PARA FASTAPI (ASYNC)
# -----------------------------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session