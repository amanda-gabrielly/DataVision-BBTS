import pytest

from app import pdfmeta


def by_code(client, code):
    return next(d for d in client.get("/api/documentos").json() if d["codigo"] == code)


def test_health_offline(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok" and r["banco"] == "postgresql" and r["ia"] == "offline"


def test_pastas_e_contagens(client):
    slugs = {p["slug"]: p for p in client.get("/api/pastas").json()}
    assert slugs["rh"]["documentos"] == 5 and slugs["rh"]["com_versoes"] == 2
    assert slugs["inovacao"]["documentos"] == 4 and slugs["contratos"]["documentos"] == 2


def test_versao_em_vigor_e_substituida(client):
    ng = by_code(client, "NG_111")
    status = {v["versao"]: v["status"] for v in ng["versoes"]}
    assert status == {"3.0.0": "vigente", "2.0.0": "substituida"}
    assert ng["versao_vigente"] == "3.0.0" and ng["tem_varias_versoes"]
    fm = by_code(client, "FM_1111-001")
    assert {v["versao"]: v["status"] for v in fm["versoes"]} == {"2.0.0": "vigente", "1.0.0": "substituida"}


def test_pergunta_com_fonte_e_pagina(client):
    r = client.post("/api/perguntar", json={"pergunta": "Qual a antecedência mínima para solicitar férias?"}).json()
    assert r["suficiente"] and r["fontes"]
    assert any(f["codigo"] == "NG_111" and f["pagina"] == 2 and "45 dias" in f["trecho"] for f in r["fontes"])
    assert all({"codigo", "versao", "status", "pagina", "trecho"} <= f.keys() for f in r["fontes"])


def test_sem_evidencia_nao_inventa(client):
    r = client.post("/api/perguntar", json={"pergunta": "Qual a política de home office da empresa?"}).json()
    assert r["suficiente"] is False and r["fontes"] == []
    assert "Não encontrei informação suficiente" in r["resposta"]


def test_pergunta_muito_curta_ou_vazia(client):
    assert client.post("/api/perguntar", json={"pergunta": "ab"}).status_code == 422
    assert client.post("/api/perguntar", json={"pergunta": "de a o para"}).status_code == 422


def test_fluxograma_vem_do_pdf(client):
    fl = by_code(client, "FL_1111-001")
    v = client.get(f"/api/documentos/{fl['id']}/visoes").json()["fluxo"]
    assert v["origem"] == "mermaid" and len(v["nos"]) == 11
    assert any(n["tipo"] == "decisao" for n in v["nos"])
    assert {"de": "E", "para": "F", "rotulo": "Aprova"} in v["arestas"]


def test_mapa_mental_com_paginas(client):
    ng = by_code(client, "NG_111")
    mapa = client.get(f"/api/documentos/{ng['id']}/visoes").json()["mapa"]
    dir_ = next(r for r in mapa["ramos"] if r["titulo"] == "Diretrizes")
    assert dir_["pagina"] >= 1 and len(dir_["filhos"]) >= 10
    assert all(f["pagina"] >= 1 for f in dir_["filhos"])
    ctr = by_code(client, "CTR_2026-012")
    clausulas = client.get(f"/api/documentos/{ctr['id']}/visoes").json()["mapa"]["ramos"]
    assert len(clausulas) >= 19 and clausulas[6]["titulo"] == "Valor"


def test_quadro_e_numeros_tem_fonte(client):
    nt = by_code(client, "NT_2026-021")
    d = client.get(f"/api/documentos/{nt['id']}/visoes").json()
    assert any(n["valor"] == "R$ 96.000,00" and n["pagina"] == 2 for n in d["numeros"])
    assert all("pagina" in r and "ref" in r for r in d["quadro"])


def test_salvos(client):
    ng = by_code(client, "NG_111")
    assert client.put(f"/api/documentos/{ng['id']}/salvo").json() == {"salvo": True}
    assert [d["codigo"] for d in client.get("/api/documentos?salvos=true").json()] == ["NG_111"]
    client.delete(f"/api/documentos/{ng['id']}/salvo")
    assert client.get("/api/documentos?salvos=true").json() == []


def test_perfil(client):
    r = client.put("/api/me", json={"cargo": "Analista Sênior", "telefone": "(61) 99999-0000"}).json()
    assert r["cargo"] == "Analista Sênior"
    assert client.put("/api/me", json={"foto": "http://x/y.png"}).status_code == 422


def test_upload_duplicado_e_invalido(client):
    from app import config
    pdf = next(config.ACERVO_DIR.rglob("NG_111__FERIAS__v3.0.0.pdf"))
    r = client.post("/api/documentos", files={"file": (pdf.name, pdf.read_bytes(), "application/pdf")}).json()
    assert r["duplicado"] is True
    assert client.post("/api/documentos", files={"file": ("a.txt", b"x", "text/plain")}).status_code == 400
    assert client.post("/api/documentos", files={"file": ("a.pdf", b"nao e pdf", "application/pdf")}).status_code == 400


def test_upload_pdf_sem_texto():
    from io import BytesIO
    from pypdf import PdfWriter
    w = PdfWriter(); w.add_blank_page(100, 100); b = BytesIO(); w.write(b)
    with pytest.raises(pdfmeta.PDFSemTexto):
        pdfmeta.analyze("scan.pdf", b.getvalue())


def test_parse_capa_e_nome_de_arquivo():
    assert pdfmeta.parse_filename("NG_111__FERIAS__v3.0.0.pdf") == {"codigo": "NG_111", "titulo": "Ferias", "versao": "3.0.0"}
    assert pdfmeta.version_key("10.0.0") > pdfmeta.version_key("9.9.9")
