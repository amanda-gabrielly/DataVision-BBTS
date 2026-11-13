"""Gera embeddings (Bedrock) para trechos que ainda não têm. Custa centavos para o acervo de demonstração.

    python -m scripts.embed_pending
"""
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app import ai, db  # noqa: E402


def main() -> None:
    if not ai.available():
        sys.exit("Bedrock indisponível (AI_MODE=offline ou sem credenciais AWS).")
    with db.SessionLocal() as s:
        rows = s.execute(text("SELECT id, conteudo FROM trechos WHERE embedding IS NULL ORDER BY id")).all()
        print(f"{len(rows)} trechos sem embedding")
        for i in range(0, len(rows), 20):
            batch = rows[i:i + 20]
            vecs = ai.embed_texts([r.conteudo for r in batch], "search_document")
            for r, v in zip(batch, vecs):
                s.execute(text("UPDATE trechos SET embedding=:e WHERE id=:i"), {"e": v, "i": r.id})
            s.commit()
            print(f"  {min(i + 20, len(rows))}/{len(rows)}")
            time.sleep(1.1)  # respeita o limite de taxa do modelo
if __name__ == "__main__":
    main()
