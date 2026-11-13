"""Cria (ou atualiza a senha de) um usuário real.

    python -m scripts.criar_usuario "Maria Souza" maria@bbts.com.br gestor
    (a senha é pedida no terminal; não aparece na tela nem fica no histórico)

Perfis: terceiro, colaborador, gestor, juridico, administrador.
"""
import getpass
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import text  # noqa: E402

from app import auth, db  # noqa: E402


def main() -> None:
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    nome, email, perfil = sys.argv[1:]
    senha = getpass.getpass("Senha (mínimo 8 caracteres): ")
    if len(senha) < 8 or senha != getpass.getpass("Repita a senha: "):
        sys.exit("Senha curta demais ou diferente da repetição.")
    db.apply_schema()
    with db.SessionLocal() as s:
        pid = s.execute(text("SELECT id FROM perfis WHERE slug=:p"), {"p": perfil}).scalar()
        if not pid:
            sys.exit(f"Perfil inexistente: {perfil}")
        s.execute(
            text("INSERT INTO usuarios (nome, email, perfil_id, senha_hash) VALUES (:n,:e,:p,:h) "
                 "ON CONFLICT (email) DO UPDATE SET senha_hash=EXCLUDED.senha_hash, perfil_id=EXCLUDED.perfil_id, nome=EXCLUDED.nome"),
            {"n": nome, "e": email.strip().lower(), "p": pid, "h": auth.hash_senha(senha)},
        )
        s.commit()
    print(f"Usuário {email} salvo com o perfil {perfil}.")


if __name__ == "__main__":
    main()
