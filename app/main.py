from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import localidades
from app.database import engine, AsyncSessionLocal
from app.services.localidades_service import LocalidadesService
from app import models
import logging
import os


# Desabilitar logs do SQLAlchemy completamente
logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.pool").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.dialects").setLevel(logging.WARNING)
logging.getLogger("sqlalchemy.orm").setLevel(logging.WARNING)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logging.info("🚀 Iniciando aplicação...")

    # Criar tabelas usando engine assíncrono
    async with engine.begin() as conn:
        await conn.run_sync(models.Base.metadata.create_all)

    # Sincronizar localidades com IBGE no startup (se habilitado)
    if os.getenv("SYNC_IBGE_ON_STARTUP", "true").lower() == "true":
        logging.info("📍 Verificando sincronização com IBGE...")
        async with AsyncSessionLocal() as db:
            try:
                # Verificar se já existem estados no banco
                estados = await LocalidadesService.get_estados(db)
                if not estados:
                    logging.info("📍 Base vazia, sincronizando com IBGE...")
                    await LocalidadesService.sincronizar_com_ibge(db)
                    logging.info("✅ Sincronização com IBGE concluída!")
                else:
                    logging.info(f"✅ Base já contém {len(estados)} estados, pulando sincronização.")
            except Exception as e:
                logging.error(f"❌ Erro ao sincronizar com IBGE: {e}")

    yield

    logging.info("⏹️ Encerrando aplicação...")


# Criar instância do FastAPI
app = FastAPI(
    title="API para gestão da base de Localidades",
    description="API para gestão de localidades",
    version="1.0.0",
    lifespan=lifespan
)


# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Success-Count", "X-Error-Count", "X-Total-Count", "Content-Disposition"],
)

# Incluir routers
app.include_router(localidades.router, prefix="/api/localidades", tags=["Localidades"])


@app.get("/")
def read_root():
    return {
        "message": "Micro Serviço de Gestão de Localidades - API",
        "version": "1.0.0",
        "status": "online"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}