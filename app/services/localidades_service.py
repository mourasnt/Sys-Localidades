import asyncio
import httpx
import json

from sqlalchemy import select, text, func, cast
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.engine import URL
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import selectinload, joinedload

try:
    import geopandas as gpd
    import pandas as pd
except ImportError:
    raise ImportError(
        "As bibliotecas 'geopandas' e 'pandas' são necessárias para geoprocessamento."
    )

from app.models import Estado, Municipio


# -------------------------------------------------------------------
# CONSTANTES
# -------------------------------------------------------------------

IBGE_ESTADOS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados"
IBGE_MUNIS_URL = "https://servicodados.ibge.gov.br/api/v1/localidades/municipios"

SHAPEFILE_MUNICIPIOS_PATH = "./dados_geo/BR_Municipios_2024.shp"


# -------------------------------------------------------------------
# SERVICE
# -------------------------------------------------------------------

class LocalidadesService:

    # ===============================================================
    # URL SÍNCRONA (GeoPandas / psycopg2)
    # ===============================================================
    @staticmethod
    def _get_sync_db_url(db: AsyncSession) -> str:
        async_engine = db.get_bind()
        if not async_engine:
            raise ConnectionError("AsyncSession não está associada a um Engine.")

        url: URL = async_engine.url

        return (
            f"postgresql+psycopg2://{url.username}:{url.password}"
            f"@{url.host}:{url.port}/{url.database}"
        )

    @staticmethod
    async def get_municipios_por_raio(db: AsyncSession, codigo_ibge: int, raio_km: float):
        """
        Retorna municípios dentro de um raio (em km) a partir de um município base.
        """

        result = await db.execute(
            select(Municipio.geometria).where(Municipio.codigo_ibge == codigo_ibge)
        )
        geom_base = result.scalar_one_or_none()

        if not geom_base:
            return None

        stmt = (
            select(Municipio)
            .options(joinedload(Municipio.estado))
            .where(
                func.ST_DWithin(
                    Municipio.geometria,
                    func.ST_Transform(geom_base, 3857),
                    raio_km * 1000
                )
            )
            .order_by(Municipio.nome)
        )

        result = await db.execute(stmt)
        results = result.scalars().all()
        for r in results:
            r.codigo_ibge = str(r.codigo_ibge)
        return results

    # CONSULTAS
    @staticmethod
    async def get_estados(db: AsyncSession):
        result = await db.execute(
            select(Estado).order_by(Estado.sigla)
        )
        return result.scalars().all()

    # MUNICÍPIOS COMO GEOJSON (SEM ORM NA RESPOSTA)
    @staticmethod
    async def get_municipios_por_uf(db: AsyncSession, uf: str):
        uf = uf.upper()

        result = await db.execute(
            select(Estado.uuid).where(Estado.sigla == uf)
        )
        estado_uuid = result.scalar_one_or_none()

        if not estado_uuid:
            return None

        result = await db.execute(
            select(Municipio).options(selectinload(Municipio.estado)).where(Municipio.estado_uuid == estado_uuid).order_by(Municipio.nome)
        )
        return result.scalars().all()

    # ---------------------------------------------------------------
    @staticmethod
    async def get_municipio_por_codigo(db: AsyncSession, codigo_ibge: int):
        result = await db.execute(
            select(Municipio).options(selectinload(Municipio.estado)).where(Municipio.codigo_ibge == codigo_ibge)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_estado_por_codigo(db: AsyncSession, codigo_ibge: int):
        result = await db.execute(
            select(Estado).where(Estado.codigo_ibge == codigo_ibge)
        )
        return result.scalar_one_or_none()

    # ===============================================================
    # FUNÇÃO SÍNCRONA — SHAPEFILE
    # ===============================================================
    @staticmethod
    def _importar_municipios_do_shapefile_sync(db_url: str):
        try:
            print(f"[SHP] Lendo: {SHAPEFILE_MUNICIPIOS_PATH}")
            gdf = gpd.read_file(SHAPEFILE_MUNICIPIOS_PATH)

            gdf = gdf.rename(columns={
                "CD_MUN": "codigo_ibge",
                "NM_MUN": "nome_shape",
            })

            gdf["codigo_ibge"] = (
                pd.to_numeric(gdf["codigo_ibge"], errors="coerce")
                .astype(str).str.split(".").str[0].astype(int)
            )

            if gdf.crs is None or gdf.crs.to_epsg() != 4674:
                gdf = gdf.set_crs(epsg=4674, allow_override=True)

            # Converte para CRS métrico (EPSG:3857) para permitir consultas espaciais eficientes
            gdf = gdf.to_crs(epsg=3857)

            engine = create_engine(db_url)

            with engine.begin() as conn:
                gdf.to_postgis(
                    name="municipios_temp_geometria",
                    con=conn,
                    if_exists="replace",
                    schema="public",
                    index=True,
                    chunksize=1000,
                )

            print("[SHP] Importação concluída.")
            return True

        except Exception as e:
            print(f"[ERRO SHP] {type(e).__name__}: {e}")
            return False

    # ===============================================================
    # SINCRONIZAÇÃO COMPLETA
    # ===============================================================
    @staticmethod
    async def sincronizar_com_ibge(db: AsyncSession):

        print("=== SINCRONIZAÇÃO DE LOCALIDADES ===")

        db_url_sync = LocalidadesService._get_sync_db_url(db)

        async with httpx.AsyncClient(timeout=60) as client:

            # ----------------------------------------------------------
            # ESTADOS
            # ----------------------------------------------------------
            estados = (await client.get(IBGE_ESTADOS_URL)).json()
            estado_map = {}

            for e in estados:
                result = await db.execute(
                    select(Estado).where(Estado.codigo_ibge == e["id"])
                )
                estado = result.scalar_one_or_none()

                if not estado:
                    estado = Estado(
                        codigo_ibge=e["id"],
                        sigla=e["sigla"],
                        nome=e["nome"],
                    )
                    db.add(estado)
                else:
                    estado.sigla = e["sigla"]
                    estado.nome = e["nome"]

                estado_map[e["id"]] = estado

            await db.commit()
            print("✔ Estados sincronizados")

            # ----------------------------------------------------------
            # MUNICÍPIOS (SEM GEOMETRIA)
            # ----------------------------------------------------------
            municipios = (await client.get(IBGE_MUNIS_URL)).json()

            for m in municipios:
                microrregiao = m.get("microrregiao")
                mesorregiao = microrregiao.get("mesorregiao") if isinstance(microrregiao, dict) else {}
                uf = mesorregiao.get("UF") if isinstance(mesorregiao, dict) else {}
                uf_uuid = uf.get("id") if isinstance(uf, dict) else None
                if not uf_uuid:
                    continue

                estado = estado_map.get(uf_uuid)
                if not estado:
                    continue

                result = await db.execute(
                    select(Municipio)
                    .where(Municipio.codigo_ibge == m["id"])
                )
                municipio = result.scalar_one_or_none()

                if not municipio:
                    db.add(Municipio(
                        codigo_ibge=m["id"],
                        nome=m["nome"],
                        estado_uuid=estado.uuid,
                    ))
                else:
                    municipio.nome = m["nome"]
                    municipio.estado_uuid = estado.uuid
            await db.commit()
            print("✔ Municípios sincronizados")

        # --------------------------------------------------------------
        # GEOMETRIA
        # --------------------------------------------------------------
        print("✔ Importando geometria...")
        ok = await asyncio.to_thread(
            LocalidadesService._importar_municipios_do_shapefile_sync,
            db_url_sync,
        )

        if not ok:
            return

        await db.execute(text("""
            UPDATE municipios m
            SET geometria = ST_Multi(ST_Transform(t.geometry, 3857))
            FROM municipios_temp_geometria t
            WHERE m.codigo_ibge = t.codigo_ibge;
        """))

        await db.execute(text("DROP TABLE IF EXISTS municipios_temp_geometria;"))
        await db.commit()

        print("=== SINCRONIZAÇÃO FINALIZADA COM SUCESSO ===")