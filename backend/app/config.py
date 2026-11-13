"""Configuração por variáveis de ambiente (ver .env.example na raiz do projeto)."""
import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _normalize_db_url(url: str) -> str:
    """Aceita postgres://, postgresql:// e já converte para o driver psycopg 3."""
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = _normalize_db_url(
    os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://datavision:datavision@localhost:5432/datavision",
    )
)

# auto    -> usa Bedrock se houver credenciais AWS; senão, modo offline
# bedrock -> exige Bedrock (erro claro se faltar credencial)
# offline -> nunca chama a AWS (busca textual do PostgreSQL, sem custo)
AI_MODE = os.getenv("AI_MODE", "auto").lower()
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
GENERATION_MODEL_ID = os.getenv("BEDROCK_GENERATION_MODEL", "amazon.nova-lite-v1:0")
EMBEDDING_MODEL_ID = os.getenv("BEDROCK_EMBEDDING_MODEL", "cohere.embed-multilingual-v3")

CHUNK_SIZE = int(os.getenv("CHUNK_SIZE", "1100"))
CHUNK_OVERLAP = int(os.getenv("CHUNK_OVERLAP", "180"))
TOP_K = int(os.getenv("TOP_K", "8"))
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

ACERVO_DIR = Path(os.getenv("ACERVO_DIR", ROOT / "acervo"))

CORS_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]

# Login
SESSAO_HORAS = int(os.getenv("SESSAO_HORAS", "12"))
# Modo demonstração: lista os usuários de exemplo na tela de login e usa a senha-padrão abaixo.
# Em produção deixe DEMO_MODE=0 e crie usuários reais com scripts/criar_usuario.py.
DEMO_MODE = os.getenv("DEMO_MODE", "0").lower() in ("1", "true", "sim")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "datavision@2026")
