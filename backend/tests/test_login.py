"""Login, sessão, troca de senha e proteção das rotas."""
from fastapi.testclient import TestClient

from app import config
from app.main import app

EMAIL = "gestora@bbts.example"


def novo():
    return TestClient(app)  # sem cabeçalho de login


def test_rotas_exigem_login(client):
    c = novo()
    for rota in ("/api/documentos", "/api/painel", "/api/pastas", "/api/me", "/api/consultas"):
        assert c.get(rota).status_code == 401, rota
    assert c.post("/api/perguntar", json={"pergunta": "qual o prazo de férias?"}).status_code == 401
    assert c.get("/api/health").status_code == 200  # saúde é pública


def test_login_senha_errada_e_usuario_inexistente(client):
    c = novo()
    assert c.post("/api/login", json={"email": EMAIL, "senha": "errada"}).status_code == 401
    assert c.post("/api/login", json={"email": "ninguem@x.com", "senha": "qualquer"}).status_code == 401


def test_login_logout(client):
    c = novo()
    r = c.post("/api/login", json={"email": EMAIL.upper(), "senha": config.DEMO_PASSWORD})
    assert r.status_code == 200 and r.json()["usuario"]["perfil"]["slug"] == "gestor"
    h = {"Authorization": "Bearer " + r.json()["token"]}
    assert c.get("/api/me", headers=h).status_code == 200
    assert c.post("/api/logout", headers=h).status_code == 200
    assert c.get("/api/me", headers=h).status_code == 401


def test_trocar_senha(client):
    c = novo()
    h = {"Authorization": "Bearer " + c.post("/api/login", json={"email": "terceiro@bbts.example", "senha": config.DEMO_PASSWORD}).json()["token"]}
    assert c.put("/api/me/senha", json={"atual": "errada", "nova": "novaSenha123"}, headers=h).status_code == 403
    assert c.put("/api/me/senha", json={"atual": config.DEMO_PASSWORD, "nova": "curta"}, headers=h).status_code == 422
    assert c.put("/api/me/senha", json={"atual": config.DEMO_PASSWORD, "nova": "novaSenha123"}, headers=h).status_code == 200
    assert c.post("/api/login", json={"email": "terceiro@bbts.example", "senha": config.DEMO_PASSWORD}).status_code == 401
    # volta ao normal para não afetar outros testes
    assert c.put("/api/me/senha", json={"atual": "novaSenha123", "nova": config.DEMO_PASSWORD}, headers=h).status_code == 200


def test_bloqueio_apos_varias_falhas(client):
    c = novo()
    codigos = [c.post("/api/login", json={"email": "juridico@bbts.example", "senha": "x"}).status_code for _ in range(7)]
    assert codigos[:5] == [401] * 5 and codigos[-1] == 429
    from app import auth
    auth._falhas.clear()
