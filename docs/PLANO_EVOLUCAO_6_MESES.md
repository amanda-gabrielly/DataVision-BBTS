# Plano de evolução — 6 meses

Ponto de partida: MVP navegável com perguntas com fonte, versão em vigor, comparação, visuais, resumos, classificação e perfis de acesso.

## Cronograma

| Mês | Semanas | Foco | Entregas principais |
|---|---|---|---|
| 1 | 1–4 | Piloto seguro | Implantação na AWS (aplicação em contêiner, PostgreSQL gerenciado); login corporativo (SSO/AD) no lugar do seletor de perfil; perfis e classificações validados com o BBTS; backup e monitoramento |
| 2 | 5–8 | Mais documentos | OCR (Amazon Textract) para PDFs digitalizados; ingestão em lote e agendada; leitura de DOCX; revisão dos metadados de capa |
| 3 | 9–12 | Qualidade da busca | pgvector no PostgreSQL (busca vetorial no banco); busca híbrida (vetor + texto); melhoria da detecção de conflitos entre documentos; alertas de vigência a vencer |
| 4 | 13–16 | Confiança e conformidade | Conjunto de perguntas de referência e métricas de acerto e de citação; guardrails do Bedrock; revisão de LGPD; trilha de auditoria completa |
| 5 | 17–20 | Integração e uso | Conector com a base documental do BBTS; painel de governança (uso, perguntas sem resposta, documentos vencendo); PWA para celular; feedback "útil / não útil" nas respostas |
| 6 | 21–24 | Escala e entrada em produção | Teste de carga e custo; treinamento das áreas; documentação operacional; go-live gradual por área; plano de suporte |

## Marcos de decisão
- **Semana 4:** piloto no ar com 1 área. Decisão: ampliar ou ajustar perfis.
- **Semana 16:** métricas de qualidade. Decisão: liberar para todas as áreas ou reforçar a base.
- **Semana 24:** entrada em produção.

## Riscos e respostas
| Risco | Resposta |
|---|---|
| Resposta errada | Citação obrigatória, "evidência insuficiente", conjunto de referência (mês 4) |
| Acesso indevido | Filtro no banco, SSO, auditoria, revisão periódica de perfis |
| Capas fora do padrão | Revisão de metadados e regras de leitura por tipo de documento |
| Custo de IA | Modelos de baixo custo, cache de embeddings, limite de uso por perfil |
| PDFs escaneados | OCR no mês 2 |

## Equipe sugerida
2 desenvolvedores (back/front), 1 especialista em dados/IA, 1 responsável de produto/negócio do BBTS. Dados e código permanecem com o BBTS.
