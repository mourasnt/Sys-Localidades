import pytest
import httpx

BASE_URL = "http://localhost:2323/api/localidades"
API_TOKEN = "testtoken"


@pytest.mark.asyncio
async def test_localidades_endpoints():
    headers = {"x-token": API_TOKEN}

    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/estados", headers=headers)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        resp = await client.get(f"{BASE_URL}/estados/SP/municipios", headers=headers)
        assert resp.status_code in (200, 404)

        resp = await client.post(f"{BASE_URL}/sincronizar", headers=headers, timeout=300)
        assert resp.status_code == 200


@pytest.mark.asyncio
async def test_get_municipio_por_codigo():
    headers = {"x-token": API_TOKEN}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/municipios/3550308", headers=headers)
        assert resp.status_code in (200, 404)


@pytest.mark.asyncio
async def test_unauthorized():
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/estados")
        assert resp.status_code == 401

        resp = await client.get(f"{BASE_URL}/estados", headers={"x-token": "invalid"})
        assert resp.status_code == 401
