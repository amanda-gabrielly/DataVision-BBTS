# Documentação simples — Data Vision BBTS

## O que é
Plataforma que responde perguntas sobre documentos corporativos (contratos, manuais, normas) sempre com fonte, versão em vigor e controle de acesso.

## Como rodar
1. Requisitos: Docker, ou Python 3.12, Node 20 e PostgreSQL 16.
2. Copie `.env.example` para `.env` (a chave AWS é opcional; sem ela o sistema funciona em modo offline).
3. `docker compose up --build` e abra `http://localhost:8000`.
4. Para carregar o acervo: `cd backend && python -m scripts.seed_acervo` (use `--demo-classificacao` para a demonstração de acesso).
5. Com credenciais AWS no `.env`: `python -m scripts.embed_pending` gera os embeddings.

## Como usar
- **Painel:** perguntas rápidas e indicadores.
- **Perguntar à IA:** resposta com documento, versão, página e trecho; citações clicáveis.
- **Documentos:** pastas, versões (em vigor x substituída), classificação.
- **Relatórios:** mapa mental, fluxograma, quadro, infográfico, gráfico e resumo por perspectiva, cada item com página de origem.
- **Login e Perfil:** entrada com e-mail e senha, favoritos, dados do usuário e troca de senha. Com `DEMO_MODE=1` a tela de login mostra atalhos para as contas de exemplo (uma por perfil).

## Arquitetura
React (front) → FastAPI (back) → PostgreSQL. Amazon Bedrock: Nova Lite (respostas) e Cohere Embed Multilingual v3 (embeddings). Detalhes do banco em `BANCO_DE_DADOS.md`; acesso em `CONTROLE_DE_ACESSO.md`.

## Fluxo de uma pergunta
1. O usuário pergunta. 2. O banco filtra os documentos que o perfil pode ver. 3. Recupera os trechos mais relevantes (vetorial na Bedrock; texto em português no modo offline). 4. A IA responde só com esses trechos e cita `[código vX.Y.Z, p. N]`. 5. Sem evidência suficiente, responde que não encontrou.

## Testes
`cd backend && pytest` (26 testes; usam um banco de testes e nunca chamam a AWS).

## Limites conhecidos
Bedrock ainda não testada com credenciais reais; modo offline é busca por palavras; PDFs escaneados sem OCR; login próprio (sem SSO) e sem recuperação de senha por e-mail.
