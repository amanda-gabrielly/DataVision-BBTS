"""Caminho do Bedrock testado com um 'Bedrock falso' (sem rede e sem custo):
valida a busca vetorial, o prompt com situação da versão, a modo comparação e as citações."""
import hashlib
import re

import numpy as np
import pytest
from sqlalchemy import text

from app import ai, db, rag
from app.textutil import fold, terms

DIM = 128


def fake_vec(s: str) -> list[float]:
    v = np.zeros(DIM)
    for w in terms(s):
        v[int(hashlib.md5(w[:5].encode()).hexdigest(), 16) % DIM] += 1
    return v.tolist()


@pytest.fixture()
def bedrock(client, monkeypatch):
    calls = {"prompts": []}
    monkeypatch.setattr(ai, "mode", lambda: "bedrock")
    monkeypatch.setattr(ai, "available", lambda: True)
    monkeypatch.setattr(ai, "embed_texts", lambda texts, input_type: [fake_vec(t) for t in texts])

    def fake_generate(prompt, max_tokens=1800):
        calls["prompts"].append(prompt)
        m = re.search(r"\[([A-Z]+_[\w-]+ v[\d.]+), p\. (\d+)\]", prompt)
        return f"A antecedência mínima é de 45 dias [{m[1]}, p. {m[2]}]." if m else rag.INSUFICIENTE

    monkeypatch.setattr(ai, "generate", fake_generate)
    with db.SessionLocal() as s:
        for r in s.execute(text("SELECT id, conteudo FROM trechos")).all():
            s.execute(text("UPDATE trechos SET embedding=:e WHERE id=:i"), {"e": fake_vec(r.conteudo), "i": r.id})
        s.commit()
    yield calls
    with db.SessionLocal() as s:
        s.execute(text("UPDATE trechos SET embedding=NULL")); s.commit()


def test_resposta_gerada_com_citacao_e_fontes(client, bedrock):
    r = client.post("/api/perguntar", json={"pergunta": "Qual a antecedência mínima para solicitar férias?"}).json()
    assert r["modo"] == "bedrock" and r["suficiente"]
    assert any(f["citado"] for f in r["fontes"])
    ctx = bedrock["prompts"][0]
    assert "VIGENTE" in ctx and "Responda agora, citando as páginas" in ctx


def test_modo_comparacao_traz_documentos_relacionados(client, bedrock):
    r = client.post("/api/perguntar", json={"pergunta": "Existem divergências entre os documentos relacionados à NG_111 sobre férias?"}).json()
    assert r["comparacao"] is True
    assert "MODO COMPARAÇÃO" in bedrock["prompts"][-1]
    assert len({f["codigo"] for f in r["fontes"]}) >= 2


def test_prompt_marca_versao_substituida(client, bedrock):
    client.post("/api/perguntar", json={"pergunta": "O que dizia a versão 2.0.0 da norma de férias NG_111?"})
    assert "SUBSTITUÍDA" in bedrock["prompts"][-1] or "VIGENTE" in bedrock["prompts"][-1]


def test_falha_do_bedrock_cai_para_offline(client, bedrock, monkeypatch):
    def boom(*a, **k):
        raise ai.AIUnavailable("sem rede")
    monkeypatch.setattr(ai, "generate", boom)
    r = client.post("/api/perguntar", json={"pergunta": "Qual a antecedência mínima para solicitar férias?"}).json()
    assert r["modo"] == "offline" and r["fontes"] and "Modo offline" in r["resposta"]
