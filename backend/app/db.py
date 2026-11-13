from pathlib import Path

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from . import config
from .config import DATABASE_URL, ROOT

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

SCHEMA_FILE = ROOT / "database" / "schema.sql"

PASTAS_PADRAO = [
    ("rh", "Recursos Humanos", "Férias, jornada e benefícios", "#01B8AA"),
    ("inovacao", "Inovação", "Programas, funil e orçamento", "#F2C811"),
    ("contratos", "Contratos", "Locações, notas técnicas e aditivos", "#FE9666"),
    ("seguranca", "Segurança", "Políticas e normas de segurança", "#A66999"),
    ("geral", "Geral", "Catálogos e documentos transversais", "#3599B8"),
]


# (slug, nome, descrição, nível máximo, pastas permitidas ou None, admin)
PERFIS_PADRAO = [
    ("terceiro", "Terceirizado", "Apenas documentos públicos", 0, None, False),
    ("colaborador", "Colaborador", "Documentos públicos e internos", 1, None, False),
    ("gestor", "Gestor", "Até documentos restritos", 2, None, False),
    ("juridico", "Jurídico e Contratos", "Todos os níveis, só nas pastas Contratos e Geral", 3, ["contratos", "geral"], False),
    ("administrador", "Administrador", "Todos os níveis e pastas; reclassifica documentos", 3, None, True),
]

# Usuários de demonstração (um por perfil). Em produção vêm do SSO/AD do BBTS.
USUARIOS_DEMO = [
    ("Carla Mendes", "colaborador@bbts.example", "Analista", "Operações", "colaborador"),
    ("Marina Costa", "gestora@bbts.example", "Gerente", "Operações", "gestor"),
    ("Rafael Lima", "juridico@bbts.example", "Analista Jurídico", "Jurídico", "juridico"),
    ("Ana Paula Rocha", "admin@bbts.example", "Gestora do acervo", "Governança", "administrador"),
    ("Pedro Alves", "terceiro@bbts.example", "Consultor externo", "Externo", "terceiro"),
]


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def apply_schema(path: Path = SCHEMA_FILE) -> None:
    """Cria as tabelas (idempotente) e as pastas-padrão. Um lock evita corrida entre instâncias."""
    sql = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.execute(text("SELECT pg_advisory_xact_lock(74120918)"))
        # psycopg executa vários comandos separados por ';' quando não há parâmetros
        conn.exec_driver_sql(sql)
        for slug, nome, desc, cor in PASTAS_PADRAO:
            conn.execute(
                text(
                    "INSERT INTO pastas (slug, nome, descricao, cor) "
                    "VALUES (:s, :n, :d, :c) ON CONFLICT (slug) DO NOTHING"
                ),
                {"s": slug, "n": nome, "d": desc, "c": cor},
            )
        for slug, nome, desc, nivel, pastas, adm in PERFIS_PADRAO:
            conn.execute(
                text(
                    "INSERT INTO perfis (slug, nome, descricao, nivel, pastas, admin) VALUES (:s,:n,:d,:v,:p,:a) "
                    "ON CONFLICT (slug) DO NOTHING"
                ),
                {"s": slug, "n": nome, "d": desc, "v": nivel, "p": pastas, "a": adm},
            )
        if config.DEMO_MODE:  # usuários de exemplo só existem no modo demonstração
            from .auth import hash_senha

            senha = hash_senha(config.DEMO_PASSWORD)
            for nome, email, cargo, area, perfil in USUARIOS_DEMO:
                conn.execute(
                    text(
                        "INSERT INTO usuarios (nome, email, cargo, area, perfil_id, senha_hash) "
                        "VALUES (:n,:e,:c,:a,(SELECT id FROM perfis WHERE slug=:p), :s) ON CONFLICT (email) DO UPDATE "
                        "SET senha_hash = COALESCE(usuarios.senha_hash, EXCLUDED.senha_hash), "
                        "nome = CASE WHEN usuarios.nome IN ('Colaborador BBTS','Gestora de Área','Analista Jurídico',"
                        "'Administrador do Acervo','Prestador Terceirizado') THEN EXCLUDED.nome ELSE usuarios.nome END"
                    ),
                    {"n": nome, "e": email, "c": cargo, "a": area, "p": perfil, "s": senha},
                )
        # bases criadas antes do controle de acesso: usuário sem perfil vira colaborador
        conn.execute(text("UPDATE usuarios SET perfil_id=(SELECT id FROM perfis WHERE slug='colaborador') WHERE perfil_id IS NULL"))
