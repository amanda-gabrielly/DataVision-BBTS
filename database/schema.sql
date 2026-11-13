-- Data Vision BBTS — esquema PostgreSQL (>= 13)
-- Idempotente: pode ser executado mais de uma vez.

CREATE TABLE IF NOT EXISTS pastas (
    id         SERIAL PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    nome       TEXT NOT NULL,
    descricao  TEXT NOT NULL DEFAULT '',
    cor        TEXT NOT NULL DEFAULT '#3599B8'
);

CREATE TABLE IF NOT EXISTS usuarios (
    id           SERIAL PRIMARY KEY,
    nome         TEXT NOT NULL,
    email        TEXT NOT NULL UNIQUE,
    cargo        TEXT NOT NULL DEFAULT '',
    area         TEXT NOT NULL DEFAULT '',
    telefone     TEXT NOT NULL DEFAULT '',
    localizacao  TEXT NOT NULL DEFAULT '',
    foto         TEXT,                                -- data URI (foto pequena)
    preferencias JSONB NOT NULL DEFAULT '{}'::jsonb,
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Um documento é a "família" (ex.: NG_111). Cada arquivo enviado é uma versão.
CREATE TABLE IF NOT EXISTS documentos (
    id            SERIAL PRIMARY KEY,
    pasta_id      INTEGER NOT NULL REFERENCES pastas(id),
    codigo        TEXT NOT NULL UNIQUE,
    titulo        TEXT NOT NULL,
    tipo          TEXT NOT NULL DEFAULT 'Documento',
    vinculado_a   TEXT,                               -- código do documento de referência
    criado_em     TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_documentos_pasta ON documentos(pasta_id);

CREATE TABLE IF NOT EXISTS versoes (
    id               SERIAL PRIMARY KEY,
    documento_id     INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    versao           TEXT NOT NULL,
    status           TEXT NOT NULL CHECK (status IN ('vigente','substituida')),
    fase_original    TEXT,                            -- texto da capa do PDF
    elaborado_por    TEXT,
    aprovado_por     TEXT,
    vigencia_inicio  DATE,
    vigencia_fim     DATE,
    data_documento   DATE,                            -- aprovação/assinatura
    arquivo_nome     TEXT NOT NULL,
    arquivo_hash     CHAR(64) NOT NULL UNIQUE,        -- SHA-256: evita duplicidade
    tamanho_bytes    BIGINT NOT NULL DEFAULT 0,
    paginas          INTEGER NOT NULL DEFAULT 0,
    criado_em        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (documento_id, versao)
);

CREATE TABLE IF NOT EXISTS trechos (
    id         BIGSERIAL PRIMARY KEY,
    versao_id  INTEGER NOT NULL REFERENCES versoes(id) ON DELETE CASCADE,
    pagina     INTEGER NOT NULL,
    ordem      INTEGER NOT NULL,
    conteudo   TEXT NOT NULL,
    embedding  REAL[],                                -- Cohere Embed Multilingual v3 (1024)
    busca      TSVECTOR GENERATED ALWAYS AS (to_tsvector('portuguese', conteudo)) STORED
);
CREATE INDEX IF NOT EXISTS ix_trechos_versao ON trechos(versao_id, pagina);
CREATE INDEX IF NOT EXISTS ix_trechos_busca  ON trechos USING GIN (busca);

CREATE TABLE IF NOT EXISTS salvos (
    usuario_id   INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    documento_id INTEGER NOT NULL REFERENCES documentos(id) ON DELETE CASCADE,
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (usuario_id, documento_id)
);

CREATE TABLE IF NOT EXISTS consultas (
    id          BIGSERIAL PRIMARY KEY,
    usuario_id  INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    pasta_id    INTEGER REFERENCES pastas(id) ON DELETE SET NULL,
    pergunta    TEXT NOT NULL,
    resposta    TEXT NOT NULL,
    modo        TEXT NOT NULL CHECK (modo IN ('bedrock','offline')),
    suficiente  BOOLEAN NOT NULL DEFAULT TRUE,        -- FALSE = "evidência insuficiente"
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_consultas_usuario ON consultas(usuario_id, criado_em DESC);

CREATE TABLE IF NOT EXISTS consulta_fontes (
    consulta_id BIGINT  NOT NULL REFERENCES consultas(id) ON DELETE CASCADE,
    trecho_id   BIGINT  NOT NULL REFERENCES trechos(id) ON DELETE CASCADE,
    posicao     INTEGER NOT NULL,
    score       REAL,
    PRIMARY KEY (consulta_id, trecho_id)
);

-- ============================================================================
-- Controle de acesso: classificação do documento x perfil do usuário
--   classificação (do menos ao mais sensível): publica < interna < restrita < confidencial
--   perfil: define o nível máximo que o usuário enxerga e, opcionalmente, as pastas (NULL = todas)
--   regra: usuário vê o documento se nivel_do_perfil >= nivel_da_classificação E a pasta é permitida
-- ============================================================================
CREATE TABLE IF NOT EXISTS perfis (
    id         SERIAL PRIMARY KEY,
    slug       TEXT NOT NULL UNIQUE,
    nome       TEXT NOT NULL,
    descricao  TEXT NOT NULL DEFAULT '',
    nivel      INTEGER NOT NULL CHECK (nivel BETWEEN 0 AND 3),
    pastas     TEXT[],                               -- NULL = todas as pastas
    admin      BOOLEAN NOT NULL DEFAULT FALSE        -- pode reclassificar documentos
);

ALTER TABLE documentos ADD COLUMN IF NOT EXISTS classificacao TEXT NOT NULL DEFAULT 'interna';
DO $$ BEGIN
    ALTER TABLE documentos ADD CONSTRAINT ck_documentos_classificacao
        CHECK (classificacao IN ('publica','interna','restrita','confidencial'));
EXCEPTION WHEN duplicate_object THEN NULL; END $$;

ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS perfil_id INTEGER REFERENCES perfis(id);

CREATE OR REPLACE FUNCTION classif_nivel(c TEXT) RETURNS INTEGER LANGUAGE sql IMMUTABLE AS $$
    SELECT CASE c WHEN 'publica' THEN 0 WHEN 'interna' THEN 1 WHEN 'restrita' THEN 2 ELSE 3 END
$$;

-- Única regra de acesso do sistema: listagem, detalhe, visões, busca/RAG e resumos passam por aqui.
CREATE OR REPLACE FUNCTION pode_ver(uid INTEGER, doc_id INTEGER) RETURNS BOOLEAN LANGUAGE sql STABLE AS $$
    SELECT EXISTS (
        SELECT 1
          FROM documentos d
          JOIN pastas pa ON pa.id = d.pasta_id
          JOIN usuarios u ON u.id = uid
          JOIN perfis pf ON pf.id = u.perfil_id
         WHERE d.id = doc_id
           AND pf.nivel >= classif_nivel(d.classificacao)
           AND (pf.pastas IS NULL OR pa.slug = ANY (pf.pastas))
    )
$$;

CREATE TABLE IF NOT EXISTS log_acesso (
    id           BIGSERIAL PRIMARY KEY,
    usuario_id   INTEGER REFERENCES usuarios(id) ON DELETE SET NULL,
    documento_id INTEGER REFERENCES documentos(id) ON DELETE SET NULL,
    acao         TEXT NOT NULL,                      -- negado | reclassificado
    detalhe      TEXT,
    criado_em    TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================
-- Login: senha com hash (scrypt, nunca em texto) e sessões com token aleatório (guardado só o hash)
-- ============================================================================
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS senha_hash TEXT;
ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS ativo BOOLEAN NOT NULL DEFAULT TRUE;

CREATE TABLE IF NOT EXISTS sessoes (
    token_hash  CHAR(64) PRIMARY KEY,
    usuario_id  INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    criado_em   TIMESTAMPTZ NOT NULL DEFAULT now(),
    expira_em   TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_sessoes_usuario ON sessoes(usuario_id);
