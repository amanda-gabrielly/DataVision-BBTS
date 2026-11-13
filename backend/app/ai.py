"""Acesso ao Amazon Bedrock. O cliente é criado só no primeiro uso, então importar o módulo não exige credenciais."""
import json
import os
import threading
from functools import lru_cache

from . import config


class AIUnavailable(RuntimeError):
    """Bedrock indisponível (modo offline, sem credenciais ou erro de rede)."""


_lock = threading.Lock()
_available: bool | None = None


@lru_cache(maxsize=1)
def _client():
    import boto3

    return boto3.client("bedrock-runtime", region_name=config.AWS_REGION)


def available() -> bool:
    """True se o Bedrock pode ser usado agora. Não faz chamada paga: só verifica credenciais."""
    global _available
    if config.AI_MODE == "offline":
        return False
    with _lock:
        if _available is None:
            try:
                import boto3

                # chave de API do Bedrock (token) ou credenciais AWS comuns
                _available = bool(os.getenv("AWS_BEARER_TOKEN_BEDROCK")) or boto3.Session().get_credentials() is not None
            except Exception:
                _available = False
        ok = _available
    if config.AI_MODE == "bedrock" and not ok:
        raise AIUnavailable("AI_MODE=bedrock, mas não há credenciais AWS configuradas.")
    return ok


def mode() -> str:
    try:
        return "bedrock" if available() else "offline"
    except AIUnavailable:
        return "offline"


def embed_texts(texts: list[str], input_type: str) -> list[list[float]]:
    if not texts:
        return []
    if not available():
        raise AIUnavailable("Embeddings indisponíveis no modo offline.")
    body = {"texts": texts, "input_type": input_type, "truncate": "END"}
    try:
        resp = _client().invoke_model(
            modelId=config.EMBEDDING_MODEL_ID,
            body=json.dumps(body, ensure_ascii=False),
            contentType="application/json",
            accept="application/json",
        )
        return json.loads(resp["body"].read())["embeddings"]
    except Exception as exc:  # rede, permissão, limite de taxa
        raise AIUnavailable(f"Falha ao chamar embeddings no Bedrock: {exc}") from exc


def generate(prompt: str, max_tokens: int = 1800) -> str:
    if not available():
        raise AIUnavailable("Geração indisponível no modo offline.")
    try:
        resp = _client().converse(
            modelId=config.GENERATION_MODEL_ID,
            messages=[{"role": "user", "content": [{"text": prompt}]}],
            inferenceConfig={"maxTokens": max_tokens, "temperature": 0.1},
        )
        return resp["output"]["message"]["content"][0]["text"]
    except Exception as exc:
        raise AIUnavailable(f"Falha ao gerar resposta no Bedrock: {exc}") from exc
