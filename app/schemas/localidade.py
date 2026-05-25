from pydantic import BaseModel, ConfigDict, field_validator
import uuid
from typing import List, Optional

# --- Tipos base (sem a geometria, que só faz sentido no Read/Model) ---
class EstadoBase(BaseModel):
    nome: str
    sigla: str
    codigo_ibge: str

    @field_validator('codigo_ibge', mode='before')
    @classmethod
    def transform_to_string(cls, v):
        return str(v) if v is not None else v


class EstadoRead(EstadoBase):
    uuid: uuid.UUID

    model_config = ConfigDict(from_attributes=True)


class EstadoSimple(BaseModel):
    uuid: uuid.UUID
    nome: str
    sigla: str

    model_config = ConfigDict(from_attributes=True)


class MunicipioBase(BaseModel):
    nome: str
    codigo_ibge: str
    estado: EstadoSimple

    @field_validator('codigo_ibge', mode='before')
    @classmethod
    def transform_to_string(cls, v):
        return str(v) if v is not None else v


class MunicipioRead(MunicipioBase):
    uuid: uuid.UUID

    model_config = ConfigDict(from_attributes=True)