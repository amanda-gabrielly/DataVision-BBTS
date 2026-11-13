import os

os.environ["AI_MODE"] = "offline"  # testes nunca chamam a AWS
os.environ["DEMO_MODE"] = "1"      # cria as contas de exemplo (senha-padrão)

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app import config, db, ingest  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    """Exige um PostgreSQL acessível em DATABASE_URL (use um banco de teste, ex.: datavision_test)."""
    db.apply_schema()
    with db.SessionLocal() as s:
        for pdf in sorted(config.ACERVO_DIR.rglob("*.pdf")):
            rel = pdf.relative_to(config.ACERVO_DIR)
            ingest.import_pdf(s, pdf.name, pdf.read_bytes(), ingest.slug_from_path_parts(rel.parts[:-1]))
    with TestClient(app) as c:
        # os testes de API rodam logados como Colaborador; os de acesso fazem login de cada perfil
        r = c.post("/api/login", json={"email": "colaborador@bbts.example", "senha": config.DEMO_PASSWORD})
        assert r.status_code == 200, r.text
        c.headers["Authorization"] = "Bearer " + r.json()["token"]
        yield c
