# Relatório de mudanças — para sua aprovação

Nada foi enviado ao GitHub. Tudo está nesta pasta local, montada a partir dos seus três pacotes (`main`, `feat-processamento-documentos` e `datavision-ai-lab`). Os nomes `frontend/` e `backend/` foram mantidos, então esta pasta pode substituir o conteúdo do repositório quando você aprovar.

## Problemas encontrados e o que foi feito

| # | Problema | Solução |
|---|---|---|
| 1 | `main`: o backend não subia (`DATABASE_URL` ausente, sem `.env.example`). | `.env.example` completo; `config.py` com padrão que funciona com o `docker-compose`. |
| 2 | `main`: duas arquiteturas misturadas. O `main.py` tinha um modelo e `domain/services/controllers` descreviam outro (UUID), com imports de `app.domain...` que não existem. | Uma só arquitetura, simples e testada. As pastas vazias/esqueleto não foram migradas (veja "Decisões suas"). |
| 3 | `main`: ~18 arquivos vazios e controllers que só devolviam `None`. | Substituídos por rotas reais (`app/routes.py`). |
| 4 | `init.py` com nome errado (deveria ser `__init__.py`). | Corrigido. |
| 5 | A IA (Bedrock) estava fora do backend; `/api/ask` só contava palavras. | RAG do laboratório integrado: busca semântica, resposta com fonte, "evidência insuficiente", modo comparação. |
| 6 | O cliente Bedrock era criado ao importar o módulo (exigia credencial até para testar). | Criação sob demanda; modo `offline` sem custo. |
| 7 | Auditoria da NG_111 com regras fixas (`D-45`, `V3.0.0` no código). | Regras de vigência vêm da capa do PDF; a comparação é genérica e o modelo recebe a situação de cada versão. |
| 8 | Banco só local, com senha por variável. | `docker-compose.yml`, `schema.sql`, `seed`, e `DATABASE_URL` aceita PostgreSQL online. |
| 9 | Migração da `feat` frágil (divide SQL por `;` a cada start). | Esquema idempotente com trava (`pg_advisory_xact_lock`). |
| 10 | Sem versão em vigor, camadas, salvos, perfil, relatórios. | Tabelas, API e telas para todos. |
| 11 | `.venv` do Windows dentro do zip do laboratório de IA. | Fora do projeto; `.gitignore` cobre. |
| 12 | `embeddings.json` não corresponde aos PDFs (0 de 142 trechos casam). | Removido; os embeddings ficam no PostgreSQL e se geram uma vez (`scripts.embed_pending`). |
| 13 | Frontend era o template padrão do Vite. | Frontend completo a partir do protótipo aprovado. |

## O que foi aproveitado

Da `feat`: upload de PDF, SHA-256 contra duplicidade, versão/data lidas, aviso de PDF digitalizado. Do laboratório de IA: modelos, chunking (1.100/180), prompts e as regras de "não inventar". Do protótipo: telas, cores (Power BI), pastas, perfil, bandeirinha.

## O que mudou na experiência

- **Mapa mental e fluxograma refeitos.** O mapa agora é uma árvore horizontal que abre e fecha por ramo, com a página em cada item. O fluxograma é desenhado a partir do próprio PDF FL_1111-001: decisão em hexágono, etapas com prazo em laranja e retorno tracejado.
- Todo elemento clicável mostra a **fonte** (documento, versão, página, trecho) e abre o PDF na página.

## Verificado aqui

- 18 testes automatizados passam em PostgreSQL 16 real (incluindo o caminho do Bedrock com um Bedrock simulado).
- Instalação do zero (banco novo, seed duas vezes sem duplicar) e API no ar.
- Front: lint e build limpos; telas conferidas no navegador em claro, escuro e celular (sem rolagem horizontal).

## Não foi possível verificar (honesto)

- **Bedrock de verdade:** não há credenciais AWS aqui. O código foi testado com um Bedrock simulado; a primeira execução real deve ser acompanhada (`AI_MODE=bedrock`, depois `python -m scripts.embed_pending`).
- **`docker compose`:** o ambiente não tem Docker. O esquema foi validado no PostgreSQL 16 nativo; o compose usa `postgres:16-alpine` padrão.
- **Qualidade das respostas offline:** é busca por palavras (a pergunta "salário do diretor do programa" não é rejeitada offline, porque "salário" aparece no 13º salário). Com Bedrock o modelo decide a suficiência.

## Decisões suas

1. As pastas `domain/`, `services/`, `controllers/` da `main` (arquitetura limpa, vazias em sua maioria) foram descartadas para manter o MVP simples. Se a banca valoriza essa organização, posso reaproveitar os nomes nas camadas.
2. Login: o MVP usa um usuário padrão. Quer um login simples para a demonstração?
3. Pasta "Segurança" existe, mas está vazia (sem PDFs sintéticos para ela).

## Para enviar ao GitHub depois da sua aprovação (não executado)

Sugestão: criar uma branch (`feat/mvp-integrado`), copiar o conteúdo desta pasta, conferir que `.env` não entra, abrir um pull request e só então fazer o merge na `main`.

## Pendente

Roteiro do pitch (5 min + 3 min de perguntas), slides e plano de evolução de 6 meses com cronograma.
