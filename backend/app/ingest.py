"""Importação de um PDF: metadados, versão em vigor, trechos e embeddings."""
import hashlib
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import ai, pdfmeta

PASTA_POR_PREFIXO_DE_NOME = {  # nome da pasta física do acervo -> slug da pasta no sistema
    "ferias": "rh", "inovacao": "inovacao", "locacao": "contratos", "geral": "geral",
    "substituidos": None,
}


def slug_from_path_parts(parts: tuple[str, ...]) -> str | None:
    for p in parts:
        s = PASTA_POR_PREFIXO_DE_NOME.get(p.lower())
        if s:
            return s
    return None


def embed_chunks(chunks: list[tuple[int, str]]) -> list[list[float] | None]:
    """Gera embeddings no Bedrock quando disponível. Sem Bedrock, devolve None: o trecho continua pesquisável por texto."""
    vectors: list[list[float] | None] = [None] * len(chunks)
    if not chunks or not ai.available():
        return vectors
    try:
        for s in range(0, len(chunks), 20):
            got = ai.embed_texts([t for _, t in chunks[s:s + 20]], "search_document")
            vectors[s:s + len(got)] = got
    except ai.AIUnavailable:
        pass
    return vectors


def reconcile_status(db: Session, documento_id: int) -> None:
    """Regra de vigência: só a maior versão marcada 'Vigente' fica em vigor; as demais são substituídas."""
    rows = db.execute(
        text("SELECT id, versao, fase_original FROM versoes WHERE documento_id=:d"), {"d": documento_id}
    ).all()
    if not rows:
        return
    candidates = [r for r in rows if (r.fase_original or "Vigente").lower().startswith("vigente")]
    pool = candidates or rows
    current = max(pool, key=lambda r: pdfmeta.version_key(r.versao))
    for r in rows:
        db.execute(
            text("UPDATE versoes SET status=:s WHERE id=:i"),
            {"s": "vigente" if r.id == current.id else "substituida", "i": r.id},
        )


def import_pdf(db: Session, filename: str, content: bytes, pasta_slug: str | None = None,
               classificacao: str | None = None, usuario_id: int | None = None) -> dict:
    digest = hashlib.sha256(content).hexdigest()
    dup = db.execute(
        text(
            "SELECT d.id, d.codigo, v.versao FROM versoes v JOIN documentos d ON d.id=v.documento_id "
            "WHERE v.arquivo_hash=:h"
        ),
        {"h": digest},
    ).first()
    if dup:
        return {"duplicado": True, "documento_id": dup.id, "codigo": dup.codigo, "versao": dup.versao}

    meta = pdfmeta.analyze(filename, content)

    doc = db.execute(text("SELECT id, pasta_id FROM documentos WHERE codigo=:c"), {"c": meta["codigo"]}).first()
    if doc:
        if usuario_id is not None and not db.execute(
            text("SELECT pode_ver(:u, :d)"), {"u": usuario_id, "d": doc.id}
        ).scalar():
            raise PermissionError("Seu perfil não tem acesso a este documento.")
        documento_id = doc.id
    else:
        slug = pasta_slug
        if not slug and meta.get("vinculado_a"):  # herda a pasta do documento de referência
            ref = db.execute(
                text("SELECT p.slug FROM documentos d JOIN pastas p ON p.id=d.pasta_id WHERE d.codigo=:c"),
                {"c": meta["vinculado_a"]},
            ).first()
            slug = ref.slug if ref else None
        pasta = db.execute(text("SELECT id FROM pastas WHERE slug=:s"), {"s": slug or "geral"}).first()
        if not pasta:
            raise ValueError(f"Pasta inexistente: {slug}")
        documento_id = db.execute(
            text(
                "INSERT INTO documentos (pasta_id, codigo, titulo, tipo, vinculado_a, classificacao) "
                "VALUES (:p,:c,:t,:ti,:v,:cl) RETURNING id"
            ),
            {"p": pasta.id, "c": meta["codigo"], "t": meta["titulo"], "ti": meta["tipo"], "v": meta.get("vinculado_a"),
             "cl": classificacao or meta.get("classificacao") or "interna"},
        ).scalar_one()

    if db.execute(
        text("SELECT 1 FROM versoes WHERE documento_id=:d AND versao=:v"), {"d": documento_id, "v": meta["versao"]}
    ).first():
        raise ValueError(f"{meta['codigo']} v{meta['versao']} já existe com outro conteúdo.")

    versao_id = db.execute(
        text(
            "INSERT INTO versoes (documento_id, versao, status, fase_original, elaborado_por, aprovado_por, "
            "vigencia_inicio, vigencia_fim, data_documento, arquivo_nome, arquivo_hash, tamanho_bytes, paginas) "
            "VALUES (:d,:v,'vigente',:f,:e,:a,:vi,:vf,:dd,:n,:h,:s,:p) RETURNING id"
        ),
        {
            "d": documento_id, "v": meta["versao"], "f": meta.get("fase"), "e": meta.get("elaborado_por"),
            "a": meta.get("aprovado_por"), "vi": meta.get("vigencia_inicio"), "vf": meta.get("vigencia_fim"),
            "dd": meta.get("data_documento"), "n": re.sub(r".*[\\/]", "", filename)[:240], "h": digest,
            "s": len(content), "p": meta["paginas"],
        },
    ).scalar_one()

    chunks = pdfmeta.split_into_chunks(meta["pages"])
    vectors = embed_chunks(chunks)
    for ordem, ((pagina, conteudo), vec) in enumerate(zip(chunks, vectors)):
        db.execute(
            text("INSERT INTO trechos (versao_id, pagina, ordem, conteudo, embedding) VALUES (:v,:p,:o,:c,:e)"),
            {"v": versao_id, "p": pagina, "o": ordem, "c": conteudo, "e": vec},
        )
    reconcile_status(db, documento_id)
    db.commit()
    return {
        "duplicado": False, "documento_id": documento_id, "versao_id": versao_id, "codigo": meta["codigo"],
        "versao": meta["versao"], "trechos": len(chunks), "com_embedding": sum(v is not None for v in vectors),
        "paginas_sem_texto": meta["empty_pages"],
    }
