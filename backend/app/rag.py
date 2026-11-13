"""Recuperação + resposta com fontes (documento, versão, situação, página)."""
import re

import numpy as np
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import ai, config
from .textutil import fold, raw_terms, terms

SELECT_BASE = """
SELECT t.id AS trecho_id, t.pagina, t.conteudo, v.versao, v.status, d.id AS documento_id,
       d.codigo, d.titulo, d.tipo, d.vinculado_a, p.slug AS pasta
FROM trechos t JOIN versoes v ON v.id=t.versao_id JOIN documentos d ON d.id=v.documento_id
JOIN pastas p ON p.id=d.pasta_id
"""


def _scope_sql(pasta_slug, documento_id, uid):
    """Filtro de escopo + permissão: o que o usuário não pode ver nunca chega à busca nem ao prompt."""
    where, params = ["pode_ver(:uid, d.id)"], {"uid": uid or 0}
    if pasta_slug:
        where.append("p.slug=:pasta"); params["pasta"] = pasta_slug
    if documento_id:
        where.append("d.id=:doc"); params["doc"] = documento_id
    return (" WHERE " + " AND ".join(where)) if where else "", params


def _row_to_source(r, score: float) -> dict:
    return {
        "trecho_id": r.trecho_id, "documento_id": r.documento_id, "codigo": r.codigo, "titulo": r.titulo,
        "versao": r.versao, "status": r.status, "pagina": r.pagina, "trecho": r.conteudo,
        "score": round(float(score), 4), "pasta": r.pasta,
    }


def retrieve_vector(db: Session, question: str, pasta, doc, k: int, uid=None):
    where, params = _scope_sql(pasta, doc, uid)
    where = (where + " AND " if where else " WHERE ") + "t.embedding IS NOT NULL"
    rows = db.execute(text(SELECT_BASE.replace("t.conteudo,", "t.conteudo, t.embedding,") + where), params).all()
    if not rows:
        return None
    q = np.array(ai.embed_texts([question], "search_query")[0], dtype=float)
    mat = np.array([r.embedding for r in rows], dtype=float)
    sims = mat @ q / (np.linalg.norm(mat, axis=1) * np.linalg.norm(q) + 1e-12)
    order = np.argsort(-sims)[:k]
    return [_row_to_source(rows[i], sims[i]) for i in order]


def retrieve_text(db: Session, question: str, pasta, doc, k: int, uid=None):
    """Busca textual do PostgreSQL (português) + cobertura dos termos da pergunta."""
    ts = terms(question)
    if not ts:
        return []
    query = " | ".join(raw_terms(question))
    where, params = _scope_sql(pasta, doc, uid)
    cond = "t.busca @@ to_tsquery('portuguese', :q)"
    where = (where + " AND " if where else " WHERE ") + cond
    params["q"] = query
    sql = (
        SELECT_BASE.replace("t.conteudo,", "t.conteudo, ts_rank_cd(t.busca, to_tsquery('portuguese', :q), 32) AS rank,")
        + where + " ORDER BY rank DESC LIMIT 40"
    )
    rows = db.execute(text(sql), params).all()
    out = []
    for r in rows:
        body = fold(r.conteudo)
        cov = sum(1 for t in ts if t[:5] in body) / len(ts)
        # cobertura dos termos pesa mais; ts_rank desempata; versão substituída perde pontos
        score = cov + 0.3 * float(r.rank) - (0.0 if r.status == "vigente" else 0.15)
        src = _row_to_source(r, score)
        src["cobertura"] = round(cov, 3)
        out.append(src)
    out.sort(key=lambda x: x["score"], reverse=True)
    return out[:k]


def unknown_terms(db: Session, question: str, pasta, doc, uid=None) -> list[str]:
    """Termos relevantes da pergunta que não aparecem em NENHUM trecho do escopo (ex.: 'salário').
    Sinal forte de que o acervo não responde — evita apresentar trechos parecidos como se fossem a resposta."""
    ts = [t for t in raw_terms(question) if len(fold(t)) >= 5]
    if not ts:
        return []
    where, params = _scope_sql(pasta, doc, uid)
    cols = []
    for i, t in enumerate(ts):
        params[f"t{i}"] = t
        cols.append(f"COALESCE(bool_or(t.busca @@ to_tsquery('portuguese', :t{i})), false) AS c{i}")
    row = db.execute(
        text("SELECT " + ", ".join(cols) + " FROM trechos t JOIN versoes v ON v.id=t.versao_id "
             "JOIN documentos d ON d.id=v.documento_id JOIN pastas p ON p.id=d.pasta_id" + where), params
    ).mappings().one()
    return [t for i, t in enumerate(ts) if not row[f"c{i}"]]


def related_chunks(db: Session, sources: list[dict], per_doc: int = 2, max_docs: int = 6, uid=None) -> list[dict]:
    """Para perguntas de comparação: traz também trechos dos documentos ligados aos já recuperados."""
    codes = {s["codigo"] for s in sources}
    rows = db.execute(text("SELECT codigo, vinculado_a FROM documentos")).all()
    linked = set()
    for r in rows:
        if r.codigo in codes and r.vinculado_a:
            linked.add(r.vinculado_a)
        if r.vinculado_a in codes:
            linked.add(r.codigo)
    linked -= codes
    extra = []
    for code in list(linked)[:max_docs]:
        rs = db.execute(
            text(SELECT_BASE + " WHERE d.codigo=:c AND pode_ver(:uid, d.id) ORDER BY v.status='vigente' DESC, t.ordem LIMIT :n"),
            {"c": code, "n": per_doc, "uid": uid or 0},
        ).all()
        extra += [_row_to_source(r, 0.0) for r in rs]
    return extra


COMPARE_WORDS = ("diverg", "conflit", "compar", "inconsist", "vigente", "vigor", "substitu", "versao", "versoes", "relacionad", "audit")


def is_comparison(question: str) -> bool:
    f = fold(question)
    return any(w in f for w in COMPARE_WORDS)


def _label(s: dict) -> str:
    return f"{s['codigo']} v{s['versao']}"


def build_prompt(question: str, sources: list[dict], comparison: bool) -> str:
    rules = """Você é o assistente documental do Data Vision BBTS. Responda em português usando EXCLUSIVAMENTE o contexto.

REGRAS:
- Não invente informações, prazos, valores ou fontes. Não use conhecimento externo.
- Toda afirmação factual deve citar a fonte no formato exato [CÓDIGO vX.Y.Z, p. N], copiando código, versão e página do rótulo do trecho usado.
- Cada trecho do contexto informa se a versão é VIGENTE ou SUBSTITUÍDA. Responda com base na versão vigente e,
  se citar uma substituída, diga claramente que ela foi substituída.
- Diferencie documentos vigentes, substituídos e complementares. Uma versão antiga substituída não é, por si só, conflito.
- Se não houver evidência suficiente, responda exatamente: "Não encontrei informação suficiente nos documentos recuperados."
- ESTILO: escreva como se explicasse a um colega, em linguagem simples, sem jargão jurídico. Respostas curtas.
- Comece pela resposta direta em 1 ou 2 frases curtas. Se houver condições, exceções ou prazos importantes, acrescente no máximo 3 tópicos curtos (uma linha cada).
- No total, no máximo 90 palavras. Sem títulos, sem tabelas, sem negrito, sem repetir a pergunta."""
    if comparison:
        rules += """

MODO COMPARAÇÃO:
- Declare divergência somente quando duas orientações do mesmo assunto forem incompatíveis (cite as duas fontes).
- Diferença de detalhamento não é divergência. Não trate ausência de informação como prova de consistência.
- Formato curto: 1ª linha diz se há ou não divergência comprovada. Depois, no máximo 3 tópicos de uma linha cada, com a fonte. Sem tabela. Se algo não puder ser verificado, diga em uma frase."""
    ctx = "\n\n".join(
        f"[{_label(s)}, p. {s['pagina']}] (situação: {'VIGENTE' if s['status'] == 'vigente' else 'SUBSTITUÍDA'}; {s['titulo']})\n{s['trecho']}"
        for s in sources
    )
    return f"{rules}\n\nPERGUNTA:\n{question}\n\nCONTEXTO:\n{ctx}\n\nResponda agora, citando as páginas."


def mark_cited(answer: str, sources: list[dict]) -> None:
    cited = set()
    for m in re.finditer(r"\[([A-Z]+_[\w-]+)\s+v([\d.]+),\s*p\.?\s*(\d+)\]", answer):
        cited.add((m[1], m[2], int(m[3])))
    for s in sources:
        s["citado"] = (s["codigo"], s["versao"], s["pagina"]) in cited


def best_excerpt(trecho: str, question: str, limit: int = 380) -> str:
    """Frases do trecho que mais cobrem os termos da pergunta (para o modo offline)."""
    ts = terms(question)
    flat = re.sub(r"\n(?!\d+(?:\.\d+)*\.\s)", " ", trecho)  # une linhas quebradas pelo PDF
    parts = [p.strip() for p in re.split(r"\n|(?<=[.;])\s+(?=\d+(?:\.\d+)*\.\s|[A-ZÀ-Ú])", flat) if len(p.strip()) > 12]
    if not parts or not ts:
        return re.sub(r"\s+", " ", trecho)[:limit]
    scored = sorted(range(len(parts)), key=lambda i: -sum(1 for t in ts if t[:5] in fold(parts[i])))
    keep = sorted(scored[:2])
    return re.sub(r"\s+", " ", " ".join(parts[i] for i in keep))[:limit]


def offline_answer(sources: list[dict], question: str = "") -> str:
    lines = ["Modo offline (sem IA): estes são os trechos mais relevantes.\n"]
    for s in sources[:2]:
        aviso = "" if s["status"] == "vigente" else " ⚠ versão substituída"
        lines.append(f"• [{s['codigo']} v{s['versao']}, p. {s['pagina']}]{aviso} {best_excerpt(s['trecho'], question, 260)}")
    return "\n".join(lines)


INSUFICIENTE = "Não encontrei informação suficiente nos documentos recuperados."
MIN_COVERAGE = 0.6


def ask(db: Session, question: str, pasta: str | None = None, documento_id: int | None = None,
        usuario_id: int | None = None) -> dict:
    comparison = is_comparison(question)
    modo, sources = "offline", None
    if ai.mode() == "bedrock":
        try:
            sources = retrieve_vector(db, question, pasta, documento_id, config.TOP_K, usuario_id)
            modo = "bedrock" if sources else "offline"
        except ai.AIUnavailable:
            sources = None
    if sources is None:
        sources = retrieve_text(db, question, pasta, documento_id, config.TOP_K, usuario_id)
        modo = "offline"

    suficiente = bool(sources)
    if modo == "offline" and sources:
        if max(x.get("cobertura", 0) for x in sources) < MIN_COVERAGE or unknown_terms(db, question, pasta, documento_id, usuario_id):
            suficiente = False
    if modo == "bedrock" and comparison:
        have = {s["trecho_id"] for s in sources}
        sources += [s for s in related_chunks(db, sources, uid=usuario_id) if s["trecho_id"] not in have]

    if not suficiente:
        resposta, sources, suficiente = INSUFICIENTE, [], False
    elif modo == "bedrock":
        try:
            resposta = ai.generate(build_prompt(question, sources, comparison), 450)
            suficiente = INSUFICIENTE not in resposta
        except ai.AIUnavailable:
            modo, resposta = "offline", offline_answer(sources, question)
    else:
        resposta = offline_answer(sources, question)
    mark_cited(resposta, sources)

    pasta_id = None
    if pasta:
        row = db.execute(text("SELECT id FROM pastas WHERE slug=:s"), {"s": pasta}).first()
        pasta_id = row.id if row else None
    cid = db.execute(
        text("INSERT INTO consultas (usuario_id, pasta_id, pergunta, resposta, modo, suficiente) "
             "VALUES (:u,:p,:q,:r,:m,:s) RETURNING id"),
        {"u": usuario_id, "p": pasta_id, "q": question, "r": resposta, "m": modo, "s": suficiente},
    ).scalar_one()
    for pos, s in enumerate(sources):
        db.execute(
            text("INSERT INTO consulta_fontes (consulta_id, trecho_id, posicao, score) VALUES (:c,:t,:p,:s) "
                 "ON CONFLICT DO NOTHING"),
            {"c": cid, "t": s["trecho_id"], "p": pos, "s": s["score"]},
        )
    db.commit()
    return {"consulta_id": cid, "pergunta": question, "resposta": resposta, "modo": modo,
            "suficiente": suficiente, "comparacao": comparison, "fontes": sources}
