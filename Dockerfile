# ================================
# BASE IMAGE
# ================================
FROM python:3.11-slim

# Evita buffering e melhora logs
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Diretório de trabalho
WORKDIR /app

# Instala dependências do sistema
RUN apt-get update && apt-get install -y \
    # Dependências essenciais
    build-essential \
    # Dependências do PostgreSQL (para psycopg2)
    libpq-dev \
    # Dependências para GeoPandas/GDAL/Shapely/Fiona
    libgdal-dev \
    libproj-dev \
    proj-data \
    proj-bin \
    # Limpeza para reduzir o tamanho da imagem
    && rm -rf /var/lib/apt/lists/*

# Copia requirements
COPY requirements.txt /app/

# Instala requirements
RUN pip install --no-cache-dir -r requirements.txt

# Copia o resto do projeto
COPY app/ /app/app/

# Porta padrão do Uvicorn
EXPOSE 8000

# Comando final: Uvicorn workers async
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
