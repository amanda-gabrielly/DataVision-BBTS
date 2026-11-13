# Banco de dados (PostgreSQL)

Arquivo: `database/schema.sql` (idempotente; aplicado ao iniciar a API ou com `psql -f`).

```
pastas ──< documentos ──< versoes ──< trechos
                │            └ status: vigente | substituida, vigência, elaborado/aprovado por, SHA-256
                ├──< salvos >── usuarios
consultas ──< consulta_fontes >── trechos     (histórico de perguntas e as fontes usadas)
```

| Tabela | Papel |
|---|---|
| `pastas` | Temas (RH, Inovação, Contratos, Segurança, Geral) com cor. |
| `documentos` | A "família" do documento, por código (ex.: `NG_111`), com tipo e documento de referência (`vinculado_a`). |
| `versoes` | Cada PDF: versão, **situação (em vigor/substituída)**, vigência, responsáveis, arquivo, hash único, páginas. |
| `trechos` | Texto por página e ordem, `embedding REAL[]` (Cohere, 1024) e `busca TSVECTOR` (português) com índice GIN. |
| `salvos` | Bandeirinha do usuário. |
| `consultas` / `consulta_fontes` | Perguntas, respostas, modo (bedrock/offline), se havia evidência e as fontes usadas. |
| `usuarios` | Perfil e preferências (JSONB). |

Regra de vigência (`ingest.reconcile_status`): em cada documento, só a maior versão marcada como "Vigente" na capa fica em vigor; as demais viram `substituida`.

Backup/migração entre máquinas: `pg_dump -Fc datavision > datavision.dump` e `pg_restore -d datavision datavision.dump`.
