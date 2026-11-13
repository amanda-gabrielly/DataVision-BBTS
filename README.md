# Data Vision BBTS

**Transformando documentos corporativos em decisões mais claras.**

Plataforma de inteligência documental para colaboradores da BBTS (Desafio 2, HACKA/TS 2026). Responde perguntas sobre contratos, normas e manuais **sempre com a fonte** (documento, versão, página e trecho), indica **qual versão está em vigor** e mostra cada documento em seis visualizações ligadas à origem.

| Camada | Tecnologia |
|---|---|
| Frontend | React + Vite (responsivo, tema claro/escuro) |
| Backend | Python 3.11+ · FastAPI · SQLAlchemy |
| Banco de dados | **PostgreSQL 13+** |
| IA | Amazon Bedrock (Nova Lite para respostas, Cohere Embed Multilingual v3 para busca semântica) |

## Como executar

Pré-requisitos: Python 3.11+, Node 20+ e Docker (ou qualquer PostgreSQL).

```bash
# 1) Configuração (uma vez)
cp .env.example .env              # no Windows: copy .env.example .env

# 2) Banco PostgreSQL local, igual para toda a equipe
docker compose up -d

# 3) Backend
cd backend
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m scripts.seed_acervo      # cria as tabelas e carrega os 14 PDFs sintéticos
uvicorn app.main:app --reload      # http://127.0.0.1:8000  (documentação: /docs)

# 4) Frontend (outro terminal)
cd frontend
npm install
npm run dev                        # http://localhost:5173
```

Sem Docker: aponte `DATABASE_URL` no `.env` para qualquer PostgreSQL (local ou online, como Neon ou Supabase). O esquema é criado sozinho ao iniciar a API (`database/schema.sql`, idempotente).

### Modos da IA (`AI_MODE` no `.env`)

| Modo | Comportamento | Custo |
|---|---|---|
| `offline` | Busca textual do PostgreSQL; a resposta mostra os trechos mais relevantes com fonte. | Zero |
| `auto` (padrão) | Usa o Bedrock se houver credenciais AWS; senão cai para `offline`. | Só quando usa o Bedrock |
| `bedrock` | Exige o Bedrock (erro claro se faltar credencial). | Centavos para o acervo de demonstração |

Com Bedrock: configure `aws configure` (ou as variáveis `AWS_*`) e rode **uma vez** `python -m scripts.embed_pending` para gerar os embeddings dos trechos.

### Testes

```bash
cd backend
pip install -r requirements-dev.txt
# use um banco separado para os testes, por exemplo datavision_test
DATABASE_URL=postgresql+psycopg://datavision:datavision@localhost:5432/datavision_test pytest
cd ../frontend && npm run lint && npm run build
```

Os testes nunca chamam a AWS (`AI_MODE=offline`; o caminho do Bedrock usa um Bedrock simulado).

## O que a plataforma faz

- **Perguntar à IA:** resposta com fontes clicáveis `[NG_111 v3.0.0, p. 2]`. Se não há evidência, diz que não encontrou e não inventa.
- **Versão em vigor, camadas e conflito:** cada documento tem versões (`em vigor` ou `substituída`), lidas da capa do PDF. Perguntas de comparação trazem também os documentos ligados (norma, procedimento, formulário, tabela, fluxo).
- **Documentos por pastas**, com aviso de documentos que têm mais de uma versão, bandeirinha de salvos e envio de PDF (código, versão e vigência são lidos da capa; duplicados são detectados pelo SHA-256).
- **Relatórios (6 visualizações):** painel com resumo por perspectiva (prazos, valores, obrigações, riscos), gráficos, fluxograma, mapa mental, infográfico e quadro. Tudo é gerado do texto real do PDF e cada elemento aponta para a página de origem.
- **Perfil** com foto, dados e preferências.

## Estrutura

```
frontend/        React (src/pages, src/components, src/viz)
backend/app/     API: routes, rag, ingest, pdfmeta, visoes, ai (Bedrock)
backend/scripts/ seed_acervo.py, embed_pending.py
backend/tests/   18 testes
database/        schema.sql
acervo/          PDFs sintéticos da ACME (empresa fictícia)
docs/            BANCO_DE_DADOS.md
docker-compose.yml · .env.example
```

## Segurança e dados

- Use apenas dados sintéticos ou anonimizados no hackathon.
- **Nunca** versionar `.env` nem chaves AWS (já no `.gitignore`).
- O MVP não tem login: usa um usuário padrão. A evolução natural é SSO corporativo (a função `current_user_id` é o único ponto de troca).

## Limitações conhecidas

- PDFs digitalizados (imagem) não têm texto: a API avisa; OCR fica para a evolução.
- O modo `offline` é uma busca por palavras, bem menos precisa que o Bedrock.
- As visões (mapa, quadro, números) dependem de o PDF ter seções numeradas, cláusulas ou tabelas no padrão do acervo; em outros formatos podem sair mais pobres.
- Fluxograma só é desenhado se o PDF trouxer o fluxo em texto (como o FL_1111-001); caso contrário, a tela avisa e mostra a sequência de prazos.
- A busca semântica compara vetores em memória (suficiente para centenas de trechos). Para milhares de documentos, trocar por `pgvector`.


## Controle de acesso
Documentos têm classificação (pública, interna, restrita, confidencial) e cada usuário tem um perfil. Veja `docs/CONTROLE_DE_ACESSO.md`.
