"""Controle de acesso: classificação do documento x perfil do usuário."""
import pytest


@pytest.fixture(scope="module")
def pessoas(client):
    info = client.get("/api/usuarios").json()
    out = {}
    for c in info["contas"]:
        r = client.post("/api/login", json={"email": c["email"], "senha": info["senha_demo"]})
        out[c["perfil"]] = {"Authorization": "Bearer " + r.json()["token"]}
    return out


@pytest.fixture()
def contrato_restrito(client, pessoas):
    """Marca o contrato como 'restrita' e devolve ao estado anterior no fim."""
    adm = pessoas["administrador"]
    doc = next(d for d in client.get("/api/documentos", headers=adm).json() if d["codigo"].startswith("CTR_"))
    antes = doc["classificacao"]
    assert client.put(f"/api/documentos/{doc['id']}/classificacao", json={"classificacao": "restrita"}, headers=adm).status_code == 200
    yield doc
    client.put(f"/api/documentos/{doc['id']}/classificacao", json={"classificacao": antes}, headers=adm)


def test_capa_define_classificacao_interna(client, pessoas):
    docs = client.get("/api/documentos", headers=pessoas["administrador"]).json()
    assert docs and all(d["classificacao"] == "interna" for d in docs)


def test_colaborador_nao_ve_restrito(client, pessoas, contrato_restrito):
    h = pessoas["colaborador"]
    assert contrato_restrito["codigo"] not in [d["codigo"] for d in client.get("/api/documentos", headers=h).json()]
    for rota in ("", "/visoes", "/trechos", "/resumo"):
        assert client.get(f"/api/documentos/{contrato_restrito['id']}{rota}", headers=h).status_code == 403
    assert client.put(f"/api/documentos/{contrato_restrito['id']}/salvo", headers=h).status_code == 403
    assert client.get("/api/painel", headers=h).json()["numeros"]["fora_do_perfil"] >= 1


def test_ia_nao_vaza_documento_restrito(client, pessoas, contrato_restrito):
    p = {"pergunta": "Quais são as multas de rescisão do contrato de coworking?"}
    r = client.post("/api/perguntar", json=p, headers=pessoas["colaborador"]).json()
    assert all(not f["codigo"].startswith("CTR_") for f in r["fontes"])  # a NT pública pode responder; o contrato não
    r = client.post("/api/perguntar", json=p, headers=pessoas["juridico"]).json()
    assert r["suficiente"] and any(f["codigo"].startswith("CTR_") for f in r["fontes"])
    # pergunta direcionada a um documento proibido também é bloqueada
    assert client.post("/api/perguntar", json={**p, "documento_id": contrato_restrito["id"]},
                       headers=pessoas["colaborador"]).status_code == 403


def test_perfil_por_pasta(client, pessoas):
    """Jurídico só enxerga Contratos e Geral, mesmo com nível máximo."""
    pastas = {d["pasta"] for d in client.get("/api/documentos", headers=pessoas["juridico"]).json()}
    assert pastas <= {"contratos", "geral"} and pastas


def test_terceiro_nao_ve_nada_interno(client, pessoas):
    assert client.get("/api/documentos", headers=pessoas["terceiro"]).json() == []


def test_so_admin_reclassifica(client, pessoas):
    doc = client.get("/api/documentos", headers=pessoas["administrador"]).json()[0]
    r = client.put(f"/api/documentos/{doc['id']}/classificacao", json={"classificacao": "publica"}, headers=pessoas["gestor"])
    assert r.status_code == 403
    r = client.put(f"/api/documentos/{doc['id']}/classificacao", json={"classificacao": "segredo"}, headers=pessoas["administrador"])
    assert r.status_code == 422


def test_token_invalido(client):
    assert client.get("/api/documentos", headers={"Authorization": "Bearer nada"}).status_code == 401


def test_me_traz_perfil(client, pessoas):
    me = client.get("/api/me", headers=pessoas["gestor"]).json()
    assert me["perfil"]["slug"] == "gestor" and me["perfil"]["nivel"] == 2


def test_resumo_enxuto():
    from app.routes import _enxugar_resumo
    bruto = "### Resumo Executivo\n\n1. **Abertura** [NT v1.0.0, p. 2] inscrição aberta em 01/02/2027.\n2. Pagamento em até 30 dias [NT v1.0.0, p. 2]\n- terceiro tópico longo o bastante\n- quarto tópico que deve sumir"
    out = _enxugar_resumo(bruto).splitlines()
    assert len(out) == 3 and all(l.startswith("- ") for l in out) and "**" not in "".join(out) and "###" not in "".join(out)
    assert _enxugar_resumo("### só título") is None
