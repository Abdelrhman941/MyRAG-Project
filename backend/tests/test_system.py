import pytest
from httpx import AsyncClient, ASGITransport
from app.main import create_app
from fastapi import FastAPI


@pytest.fixture
def app() -> FastAPI:
    return create_app()


@pytest.fixture
async def client(app: FastAPI):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_healthz(client: AsyncClient):
    response = await client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_readyz_warming(client: AsyncClient, app: FastAPI):
    app.state.model_ready = False
    app.state.model_error = None
    response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "warming"}


@pytest.mark.asyncio
async def test_readyz_ready(client: AsyncClient, app: FastAPI):
    app.state.model_ready = True
    app.state.model_error = None
    response = await client.get("/readyz")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}


@pytest.mark.asyncio
async def test_readyz_error(client: AsyncClient, app: FastAPI):
    app.state.model_ready = False
    app.state.model_error = "Model loading failed"
    response = await client.get("/readyz")
    assert response.status_code == 503
    assert response.json() == {"status": "error", "detail": "Model loading failed"}
