import os
from dotenv import load_dotenv

from sqlalchemy.ext.asyncio import (
    create_async_engine,
    AsyncSession
)
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import event

# Carregar variáveis de ambiente
load_dotenv()

# DATABASE_URL deve ser algo como:
#   sqlite+aiosqlite:///./gestao_gr.db
#   postgresql+asyncpg://user:senha@host:5432/banco
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./gestao_gr.db")

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
# OTIMIZAÇÕES PARA SQLITE
# -----------------------------------------
if DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        try:
            cursor.execute("PRAGMA journal_mode=WAL;")
            cursor.execute("PRAGMA synchronous=NORMAL;")
            cursor.execute("PRAGMA busy_timeout=5000;")
        finally:
            cursor.close()


# -----------------------------------------
# DEPENDENCY PARA FASTAPI (ASYNC)
# -----------------------------------------
async def get_db():
    async with AsyncSessionLocal() as session:
        yield session