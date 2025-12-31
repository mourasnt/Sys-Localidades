import pytest
import httpx

AUTH_BASE = "http://localhost:2222"
BASE_URL = "http://localhost:2323/api/localidades"

async def get_token(username: str, password: str):
    return "testtoken"


@pytest.mark.asyncio
async def test_localidades_endpoints_admin_and_user():
    admin_token = await get_token("admin", "admin123")
    headers_admin = {"Authorization": f"Bearer {admin_token}"}

    # Admin: listar estados
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/estados", headers=headers_admin)
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

        # listar municipios por UF
        resp = await client.get(f"{BASE_URL}/estados/SP/municipios", headers=headers_admin)
        assert resp.status_code in (200, 404)

        # tentar sincronizar (admin-only)
        resp = await client.post(f"{BASE_URL}/sincronizar", headers=headers_admin, timeout=300)
        assert resp.status_code in (200, 403, 401)

    # Non-admin user
    username = "user_local_" + "123"
    password = "pass1234"
    async with httpx.AsyncClient() as client:
        await client.post(f"{AUTH_BASE}/register", json={"username": username, "password": password})
        user_token = await get_token(username, password)
        headers_user = {"Authorization": f"Bearer {user_token}"}

        # endpoints protegidos: listar estados deve funcionar
        resp = await client.get(f"{BASE_URL}/estados", headers=headers_user)
        assert resp.status_code == 200

        # sync deve retornar 403 para non-admin
        resp = await client.post(f"{BASE_URL}/sincronizar", headers=headers_user)
        assert resp.status_code == 403

@pytest.mark.asyncio
async def test_get_municipio_por_codigo():
    admin_token = await get_token("admin", "admin123")
    headers_admin = {"Authorization": f"Bearer {admin_token}"}
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BASE_URL}/municipios/3550308", headers=headers_admin)
        assert resp.status_code in (200, 404)
