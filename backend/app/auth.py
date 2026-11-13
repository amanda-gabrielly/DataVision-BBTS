"""Autenticação: senha com scrypt (biblioteca padrão), sessões por token e limite de tentativas."""
import hashlib
import hmac
import os
import secrets
import time

from fastapi import Depends, HTTPException, Request
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import config
from .db import get_db

_N, _R, _P = 2**14, 8, 1


def hash_senha(senha: str) -> str:
    salt = os.urandom(16)
    dk = hashlib.scrypt(senha.encode(), salt=salt, n=_N, r=_R, p=_P, dklen=32)
    return f"scrypt${salt.hex()}${dk.hex()}"


def confere_senha(senha: str, armazenado: str | None) -> bool:
    """Tempo parecido exista ou não o usuário (evita descobrir e-mails pelo tempo de resposta)."""
    if not armazenado or not armazenado.startswith("scrypt$"):
        hashlib.scrypt(b"x", salt=b"0" * 16, n=_N, r=_R, p=_P, dklen=32)
        return False
    _, salt, esperado = armazenado.split("$")
    dk = hashlib.scrypt(senha.encode(), salt=bytes.fromhex(salt), n=_N, r=_R, p=_P, dklen=32)
    return hmac.compare_digest(dk.hex(), esperado)


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


# limite de tentativas: 5 erros por e-mail => bloqueia 60 s (em memória; em produção, SSO/AD faz isso)
_falhas: dict[str, list[float]] = {}
MAX_FALHAS, JANELA = 5, 60


def _bloqueado(chave: str) -> bool:
    agora = time.time()
    _falhas[chave] = [t for t in _falhas.get(chave, []) if agora - t < JANELA]
    return len(_falhas[chave]) >= MAX_FALHAS


def login(db: Session, email: str, senha: str) -> tuple[str, int]:
    chave = email.strip().lower()
    if _bloqueado(chave):
        raise HTTPException(429, "Muitas tentativas. Aguarde um minuto e tente de novo.")
    u = db.execute(text("SELECT id, senha_hash, ativo FROM usuarios WHERE lower(email)=:e"), {"e": chave}).first()
    if not confere_senha(senha, u.senha_hash if u else None) or not (u and u.ativo):
        _falhas.setdefault(chave, []).append(time.time())
        raise HTTPException(401, "E-mail ou senha incorretos.")
    _falhas.pop(chave, None)
    token = secrets.token_urlsafe(32)
    db.execute(
        text("INSERT INTO sessoes (token_hash, usuario_id, expira_em) VALUES (:h,:u, now() + make_interval(hours => :h2))"),
        {"h": _hash_token(token), "u": u.id, "h2": config.SESSAO_HORAS},
    )
    db.execute(text("DELETE FROM sessoes WHERE expira_em < now()"))
    db.commit()
    return token, u.id


def logout(db: Session, token: str) -> None:
    db.execute(text("DELETE FROM sessoes WHERE token_hash=:h"), {"h": _hash_token(token)})
    db.commit()


def _bearer(request: Request) -> str | None:
    h = request.headers.get("authorization", "")
    return h[7:].strip() if h.lower().startswith("bearer ") else None


def get_token(request: Request) -> str:
    t = _bearer(request)
    if not t:
        raise HTTPException(401, "Faça login para continuar.")
    return t


def get_uid(request: Request, db: Session = Depends(get_db)) -> int:
    """Usuário da requisição = dono do token de sessão válido. Único ponto a trocar por SSO/AD do BBTS."""
    t = _bearer(request)
    if not t:
        raise HTTPException(401, "Faça login para continuar.")
    uid = db.execute(
        text("SELECT s.usuario_id FROM sessoes s JOIN usuarios u ON u.id=s.usuario_id "
             "WHERE s.token_hash=:h AND s.expira_em > now() AND u.ativo"),
        {"h": _hash_token(t)},
    ).scalar()
    if not uid:
        raise HTTPException(401, "Sessão expirada. Entre novamente.")
    return uid
