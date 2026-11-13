# Controle de acesso por classificação

Nem todo colaborador pode ver todo documento. O acesso é decidido por **classificação do documento × perfil do usuário**.

## Classificações (da menos à mais sensível)
`publica` (0) < `interna` (1) < `restrita` (2) < `confidencial` (3)

- A capa dos PDFs do acervo traz a etiqueta `#interna`; ela é lida no upload. Sem etiqueta, o padrão é `interna`.
- No upload é possível escolher a classificação (não acima do próprio nível). O perfil **Administrador** reclassifica depois.

## Perfis (padrão, ajustáveis na tabela `perfis`)
| Perfil | Nível máximo | Pastas |
|---|---|---|
| Terceirizado | pública | todas |
| Colaborador | interna | todas |
| Gestor | restrita | todas |
| Jurídico e Contratos | confidencial | Contratos, Geral |
| Administrador | confidencial | todas (reclassifica) |

Regra única (função SQL `pode_ver(usuario, documento)`): `nível do perfil >= nível da classificação` **e** pasta permitida.

## Onde a regra é aplicada
Listagem e busca, pastas e contagens do painel, detalhe, visões, trechos, resumos, salvos, upload de nova versão e a **IA**: os trechos de documentos proibidos são filtrados na consulta ao banco, antes de a busca e do prompt, então a IA nunca recebe nem cita o que o usuário não pode ver. Acesso direto negado devolve 403 e fica em `log_acesso`.

## Login
- E-mail e senha. A senha é guardada com hash (scrypt), nunca em texto. O login devolve um token aleatório de sessão (guardado só como hash no banco, validade de `SESSAO_HORAS`, padrão 12 h). Todas as rotas da API, exceto `/api/health`, `/api/config` e `/api/login`, exigem o token.
- Cinco erros seguidos de senha bloqueiam o e-mail por 1 minuto. Sair encerra a sessão. Trocar a senha (menu Perfil) encerra as outras sessões.
- Criar usuários reais: `python -m scripts.criar_usuario "Nome" email@bbts.com.br gestor` (a senha é pedida no terminal).
- Em produção o login deve ser servido por HTTPS e, na evolução, trocado pelo SSO/AD do BBTS: só a função `get_uid` em `backend/app/auth.py` muda.

## Demonstração
- `DEMO_MODE=1` no `.env` cria as contas de exemplo (uma por perfil, senha `DEMO_PASSWORD`) e mostra atalhos na tela de login. **Desligue em produção.**
- `python -m scripts.seed_acervo --demo-classificacao` marca os contratos como `restrita` para mostrar o bloqueio.
- Limitação conhecida: um documento visível (ex.: nota técnica) pode resumir um contrato restrito; a classificação vale por documento, não por assunto.
