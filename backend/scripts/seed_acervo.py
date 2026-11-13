"""Carrega o acervo sintético (pasta acervo/) no PostgreSQL.

    python -m scripts.seed_acervo                        # a partir de backend/
    python -m scripts.seed_acervo --demo-classificacao   # contratos como 'restrita' (demonstra o acesso por perfil)

Com credenciais AWS (AI_MODE=auto/bedrock) já gera os embeddings; com AI_MODE=offline não chama a AWS.
Depois, scripts.embed_pending completa os embeddings que faltarem.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db, ingest  # noqa: E402


# Só para a demonstração (--demo-classificacao): as capas do acervo trazem apenas "#interna",
# então marcamos os contratos como "restrita" para mostrar o bloqueio por perfil.
DEMO = {"CTR_": "restrita"}


def main() -> None:
    demo = "--demo-classificacao" in sys.argv
    db.apply_schema()
    ok = dup = 0
    with db.SessionLocal() as s:
        for pdf in sorted(config.ACERVO_DIR.rglob("*.pdf")):
            rel = pdf.relative_to(config.ACERVO_DIR)
            slug = ingest.slug_from_path_parts(rel.parts[:-1])
            r = ingest.import_pdf(s, pdf.name, pdf.read_bytes(), slug)
            if demo:
                for prefixo, nivel in DEMO.items():
                    if pdf.name.startswith(prefixo):
                        s.execute(db.text("UPDATE documentos SET classificacao=:c WHERE id=:i"),
                                  {"c": nivel, "i": r["documento_id"]})
                s.commit()
            if r["duplicado"]:
                dup += 1
                print(f"= já existe  {rel}")
            else:
                ok += 1
                print(f"+ {r['codigo']} v{r['versao']}: {r['trechos']} trechos ({r['com_embedding']} com embedding)")
    print(f"\n{ok} importados, {dup} já existiam.")


if __name__ == "__main__":
    main()
