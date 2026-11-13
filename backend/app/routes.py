from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import ai, auth, config, ingest, pdfmeta, rag, visoes
from .textutil import terms as _terms
from .db import get_db

router = APIRouter(prefix="/api")


def _perfil(db: Session, uid: int) -> dict:
    return dict(db.execute(text(
        "SELECT pf.slug, pf.nome, pf.descricao, pf.nivel, pf.pastas, pf.admin FROM usuarios u "
        "JOIN perfis pf ON pf.id=u.perfil_id WHERE u.id=:u"), {"u": uid}).mappings().one())


NIVEIS = {0: "publica", 1: "interna", 2: "restrita", 3: "confidencial"}


def _version_rows(db, ids):
    rows = db.execute(
        text("SELECT * FROM versoes WHERE documento_id = ANY(:ids) ORDER BY documento_id, status='vigente' DESC, id DESC"),
        {"ids": list(ids)},
    ).mappings().all()
    out: dict[int, list] = {}
    for r in rows:
        out.setdefault(r["documento_id"], []).append({
            "id": r["id"], "versao": r["versao"], "status": r["status"], "paginas": r["paginas"],
            "fase_original": r["fase_original"], "elaborado_por": r["elaborado_por"], "aprovado_por": r["aprovado_por"],
            "vigencia_inicio": r["vigencia_inicio"], "vigencia_fim": r["vigencia_fim"],
            "data_documento": r["data_documento"], "arquivo_nome": r["arquivo_nome"],
        })
    return out


def _docs(db: Session, where: str = "", params: dict | None = None, uid: int | None = None):
    """Só devolve documentos que o usuário pode ver (pode_ver no PostgreSQL)."""
    params = dict(params or {})
    params["uid"] = uid or 0
    where = (where + " AND " if where else "WHERE ") + "pode_ver(:uid, d.id)"
    rows = db.execute(
        text(
            "SELECT d.id, d.codigo, d.titulo, d.tipo, d.vinculado_a, d.classificacao, p.slug AS pasta, p.nome AS pasta_nome, p.cor, "
            "EXISTS(SELECT 1 FROM salvos s WHERE s.documento_id=d.id AND s.usuario_id=:uid) AS salvo "
            "FROM documentos d JOIN pastas p ON p.id=d.pasta_id " + where + " ORDER BY d.codigo"
        ),
        params,
    ).mappings().all()
    vers = _version_rows(db, [r["id"] for r in rows]) if rows else {}
    out = []
    for r in rows:
        vs = vers.get(r["id"], [])
        cur = next((v for v in vs if v["status"] == "vigente"), vs[0] if vs else None)
        out.append({**r, "versoes": vs, "versao_vigente": cur["versao"] if cur else None,
                    "paginas": cur["paginas"] if cur else 0, "tem_varias_versoes": len(vs) > 1})
    return out


@router.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok", "banco": "postgresql", "ia": ai.mode()}


# ---------- login ----------
class LoginIn(BaseModel):
    email: str = Field(min_length=3, max_length=200)
    senha: str = Field(min_length=1, max_length=200)


class SenhaIn(BaseModel):
    atual: str = Field(max_length=200)
    nova: str = Field(min_length=8, max_length=200)


@router.get("/config")
def configuracao():
    return {"demo": config.DEMO_MODE}


@router.post("/login")
def entrar(body: LoginIn, db: Session = Depends(get_db)):
    token, uid = auth.login(db, body.email, body.senha)
    return {"token": token, "usuario": me(db, uid)}


@router.post("/logout")
def sair(token: str = Depends(auth.get_token), db: Session = Depends(get_db)):
    auth.logout(db, token)
    return {"ok": True}


@router.put("/me/senha")
def trocar_senha(body: SenhaIn, db: Session = Depends(get_db), uid: int = Depends(auth.get_uid),
                 token: str = Depends(auth.get_token)):
    atual = db.execute(text("SELECT senha_hash FROM usuarios WHERE id=:i"), {"i": uid}).scalar()
    if not auth.confere_senha(body.atual, atual):
        raise HTTPException(403, "A senha atual está incorreta.")
    db.execute(text("UPDATE usuarios SET senha_hash=:h WHERE id=:i"), {"h": auth.hash_senha(body.nova), "i": uid})
    # encerra as outras sessões; mantém a atual
    db.execute(text("DELETE FROM sessoes WHERE usuario_id=:i AND token_hash<>:t"),
               {"i": uid, "t": auth._hash_token(token)})
    db.commit()
    return {"ok": True}


# ---------- usuário ----------
class PerfilIn(BaseModel):
    nome: str | None = Field(None, max_length=120)
    cargo: str | None = Field(None, max_length=120)
    area: str | None = Field(None, max_length=120)
    telefone: str | None = Field(None, max_length=40)
    localizacao: str | None = Field(None, max_length=120)
    foto: str | None = Field(None, max_length=400_000)
    preferencias: dict | None = None


@router.get("/me")
def me(db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    u = dict(db.execute(text(
        "SELECT id,nome,email,cargo,area,telefone,localizacao,foto,preferencias FROM usuarios WHERE id=:i"), {"i": uid}).mappings().one())
    u["perfil"] = _perfil(db, uid)
    return u


@router.get("/usuarios")
def usuarios_demo(db: Session = Depends(get_db)):
    """Contas de exemplo para a tela de login. Só existe com DEMO_MODE=1."""
    if not config.DEMO_MODE:
        raise HTTPException(404, "Não encontrado.")
    rows = db.execute(text(
        "SELECT u.nome, u.email, pf.nome AS perfil_nome, pf.slug AS perfil, pf.descricao FROM usuarios u "
        "JOIN perfis pf ON pf.id=u.perfil_id WHERE u.senha_hash IS NOT NULL ORDER BY pf.nivel, u.id")).mappings().all()
    return {"senha_demo": config.DEMO_PASSWORD, "contas": [dict(r) for r in rows]}


@router.get("/perfis")
def perfis(db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    rows = db.execute(text("SELECT slug, nome, descricao, nivel, pastas, admin FROM perfis ORDER BY nivel, id")).mappings().all()
    return {"perfis": [dict(r) for r in rows], "classificacoes": [{"slug": v, "nivel": k} for k, v in NIVEIS.items()]}


@router.put("/me")
def update_me(body: PerfilIn, db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    data = body.model_dump(exclude_unset=True)
    if data.get("foto") and not data["foto"].startswith("data:image/"):
        raise HTTPException(422, "A foto deve ser uma imagem (data URI).")
    if "preferencias" in data:
        import json
        data["preferencias"] = json.dumps(data["preferencias"] or {})
    if data:
        sets = ", ".join(f"{k}=:{k}" + ("::jsonb" if k == "preferencias" else "") for k in data)
        db.execute(text(f"UPDATE usuarios SET {sets} WHERE id=:id"), {**data, "id": uid})
        db.commit()
    return me(db, uid)


# ---------- painel e pastas ----------
@router.get("/pastas")
def pastas(db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    rows = db.execute(text(
        "SELECT p.slug, p.nome, p.descricao, p.cor, COUNT(DISTINCT d.id) AS documentos, "
        "COUNT(DISTINCT d.id) FILTER (WHERE (SELECT COUNT(*) FROM versoes v WHERE v.documento_id=d.id) > 1) AS com_versoes "
        "FROM pastas p LEFT JOIN documentos d ON d.pasta_id=p.id AND pode_ver(:u, d.id) GROUP BY p.id ORDER BY p.id"
    ), {"u": uid}).mappings().all()
    return [dict(r) for r in rows]


@router.get("/painel")
def painel(db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    num = db.execute(text(
        "SELECT (SELECT COUNT(*) FROM documentos d WHERE pode_ver(:u, d.id)) documentos, "
        "(SELECT COUNT(*) FROM versoes v WHERE pode_ver(:u, v.documento_id)) versoes, "
        "(SELECT COUNT(*) FROM versoes v WHERE v.status='substituida' AND pode_ver(:u, v.documento_id)) substituidas, "
        "(SELECT COUNT(*) FROM trechos t JOIN versoes v ON v.id=t.versao_id WHERE pode_ver(:u, v.documento_id)) trechos, "
        "(SELECT COUNT(*) FROM consultas WHERE usuario_id=:u) consultas, "
        "(SELECT COUNT(*) FROM salvos s WHERE s.usuario_id=:u AND pode_ver(:u, s.documento_id)) salvos, "
        "(SELECT COUNT(*) FROM documentos d WHERE NOT pode_ver(:u, d.id)) fora_do_perfil"
    ), {"u": uid}).mappings().one()
    recentes = db.execute(text(
        "SELECT id, pergunta, modo, suficiente, criado_em FROM consultas WHERE usuario_id=:u ORDER BY id DESC LIMIT 5"
    ), {"u": uid}).mappings().all()
    return {
        "numeros": dict(num), "pastas": pastas(db, uid), "ia": ai.mode(), "perfil": _perfil(db, uid),
        "recentes": [dict(r) for r in recentes],
        "sugestoes": [
            "Qual a antecedência mínima para solicitar férias?",
            "Qual é o orçamento total do programa Ideias em Campo?",
            "Quais são as multas de rescisão do contrato de coworking?",
            "Existem divergências entre os documentos relacionados à NG_111?",
        ],
    }


# ---------- documentos ----------
@router.get("/documentos")
def listar(pasta: str | None = None, q: str | None = None, salvos: bool = False, db: Session = Depends(get_db),
           uid: int = Depends(auth.get_uid)):
    where, params = [], {}
    if pasta:
        where.append("p.slug=:pasta"); params["pasta"] = pasta
    if q:
        where.append("(d.codigo ILIKE :q OR d.titulo ILIKE :q OR d.tipo ILIKE :q)"); params["q"] = f"%{q}%"
    if salvos:
        where.append("EXISTS(SELECT 1 FROM salvos s WHERE s.documento_id=d.id AND s.usuario_id=:uid)")
    return _docs(db, ("WHERE " + " AND ".join(where)) if where else "", params, uid)


def _one(db, doc_id: int, uid: int):
    existe = db.execute(text("SELECT 1 FROM documentos WHERE id=:i"), {"i": doc_id}).first()
    if not existe:
        raise HTTPException(404, "Documento não encontrado.")
    docs = _docs(db, "WHERE d.id=:id", {"id": doc_id}, uid)
    if not docs:
        db.execute(text("INSERT INTO log_acesso (usuario_id, documento_id, acao, detalhe) VALUES (:u,:d,'negado','tentativa de abrir documento fora do perfil')"),
                   {"u": uid, "d": doc_id})
        db.commit()
        raise HTTPException(403, "Seu perfil não tem acesso a este documento.")
    return docs[0]


@router.get("/documentos/{doc_id}")
def detalhe(doc_id: int, db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    d = _one(db, doc_id, uid)
    rel = db.execute(text(
        "SELECT id, codigo, titulo, tipo FROM documentos WHERE (codigo=:v OR vinculado_a=:c) AND pode_ver(:u, id) ORDER BY codigo"
    ), {"v": d["vinculado_a"] or "", "c": d["codigo"], "u": uid}).mappings().all()
    d["relacionados"] = [dict(r) for r in rel]
    return d


def _resolve_version(d: dict, versao_id: int | None) -> dict:
    if versao_id:
        v = next((v for v in d["versoes"] if v["id"] == versao_id), None)
        if not v:
            raise HTTPException(404, "Versão não encontrada neste documento.")
        return v
    if not d["versoes"]:
        raise HTTPException(404, "Documento sem versões.")
    return next((v for v in d["versoes"] if v["status"] == "vigente"), d["versoes"][0])


@router.get("/documentos/{doc_id}/visoes")
def visoes_do_documento(doc_id: int, versao_id: int | None = None, db: Session = Depends(get_db),
                        uid: int = Depends(auth.get_uid)):
    d = _one(db, doc_id, uid)
    v = _resolve_version(d, versao_id)
    return {"documento": {"id": d["id"], "codigo": d["codigo"], "titulo": d["titulo"]}, "versao": v,
            **visoes.build(db, v["id"], d)}


@router.get("/documentos/{doc_id}/trechos")
def trechos(doc_id: int, versao_id: int | None = None, pagina: int | None = None, db: Session = Depends(get_db),
            uid: int = Depends(auth.get_uid)):
    d = _one(db, doc_id, uid)
    v = _resolve_version(d, versao_id)
    sql = "SELECT id, pagina, ordem, conteudo FROM trechos WHERE versao_id=:v"
    params = {"v": v["id"]}
    if pagina:
        sql += " AND pagina=:p"; params["p"] = pagina
    rows = db.execute(text(sql + " ORDER BY pagina, ordem"), params).mappings().all()
    return {"versao": v, "trechos": [dict(r) for r in rows]}


def _enxugar_resumo(texto: str) -> str | None:
    """Garante resumo curto: no máximo 3 linhas de tópico, sem títulos, numeração ou negrito."""
    import re

    linhas = []
    for l in texto.splitlines():
        l = l.strip()
        if not l or l.startswith("#"):
            continue
        l = re.sub(r"^(?:[-•*]|\d+[.)])\s*", "", l).replace("**", "").strip()
        if len(l) > 8:
            linhas.append("- " + l)
    return "\n".join(linhas[:3])[:700] or None


@router.get("/documentos/{doc_id}/resumo")
def resumo(doc_id: int, perspectiva: str = "prazos", versao_id: int | None = None, db: Session = Depends(get_db),
           uid: int = Depends(auth.get_uid)):
    if perspectiva not in visoes.PERSPECTIVAS:
        raise HTTPException(422, f"Perspectiva inválida. Use: {', '.join(visoes.PERSPECTIVAS)}.")
    d = _one(db, doc_id, uid)
    v = _resolve_version(d, versao_id)
    rows = [r for r in visoes.quadro(visoes.load_pages(db, v["id"])) if perspectiva in r["perspectivas"]][:12]
    itens = [{"ref": r["ref"], "texto": r["texto"][:400], "pagina": r["pagina"], "destaque": r["destaque"]} for r in rows]
    modo, texto = "offline", None
    if itens and ai.mode() == "bedrock":
        base = "\n".join(f"[{d['codigo']} v{v['versao']}, p. {i['pagina']}] ({i['ref']}) {i['texto']}" for i in itens)
        try:
            texto = ai.generate(
                f"Resuma sob a perspectiva de {perspectiva}, usando SÓ os itens abaixo. Escreva no máximo 3 tópicos, "
                f"cada um uma linha começando com '- ', com no máximo 20 palavras, direto ao ponto, com números e prazos. "
                f"Sem título, sem negrito, sem introdução, sem explicar o que não está nos itens. "
                f"Termine cada tópico com a fonte no formato [CÓDIGO vX.Y.Z, p. N].\n\n{base}", 260)
            texto = _enxugar_resumo(texto)
            modo = "bedrock"
        except ai.AIUnavailable:
            texto = None
    return {"documento": d["codigo"], "versao": v["versao"], "perspectiva": perspectiva, "modo": modo,
            "resumo": texto, "itens": itens}


@router.post("/documentos")
async def enviar(file: UploadFile = File(...), pasta: str | None = Form(None), classificacao: str | None = Form(None),
                 db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Envie um arquivo PDF.")
    perfil = _perfil(db, uid)
    if classificacao and classificacao not in pdfmeta.CLASSIFICACOES:
        raise HTTPException(422, "Classificação inválida. Use: " + ", ".join(pdfmeta.CLASSIFICACOES) + ".")
    if pasta and perfil["pastas"] is not None and pasta not in perfil["pastas"]:
        raise HTTPException(403, "Seu perfil não pode enviar documentos para esta pasta.")
    if classificacao and pdfmeta.CLASSIFICACOES.index(classificacao) > perfil["nivel"]:
        raise HTTPException(403, "Você não pode classificar acima do seu próprio nível de acesso.")
    content = await file.read()
    if len(content) > config.MAX_UPLOAD_MB * 1024 * 1024:
        raise HTTPException(413, f"O limite por arquivo é {config.MAX_UPLOAD_MB} MB.")
    try:
        r = ingest.import_pdf(db, file.filename, content, pasta, classificacao, uid)
    except pdfmeta.PDFSemTexto as e:
        raise HTTPException(422, str(e))
    except PermissionError as e:
        db.rollback()
        raise HTTPException(403, str(e))
    except ValueError as e:
        db.rollback()
        raise HTTPException(409, str(e))
    except Exception:
        db.rollback()
        raise HTTPException(400, "Não foi possível ler este PDF.")
    if r["duplicado"]:
        return {**r, "mensagem": "Este mesmo arquivo já está no acervo."}
    cl = db.execute(text("SELECT classificacao FROM documentos WHERE id=:i"), {"i": r["documento_id"]}).scalar_one()
    if pdfmeta.CLASSIFICACOES.index(cl) > perfil["nivel"]:  # capa classificada acima do nível de quem enviou
        db.execute(text("UPDATE documentos SET classificacao=:c WHERE id=:i"), {"c": NIVEIS[perfil["nivel"]], "i": r["documento_id"]})
        db.commit()
    return {**r, "mensagem": "PDF processado e indexado."}


@router.put("/documentos/{doc_id}/salvo")
def salvar(doc_id: int, db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    _one(db, doc_id, uid)
    db.execute(text("INSERT INTO salvos (usuario_id, documento_id) VALUES (:u,:d) ON CONFLICT DO NOTHING"),
               {"u": uid, "d": doc_id})
    db.commit()
    return {"salvo": True}


@router.delete("/documentos/{doc_id}/salvo")
def remover_salvo(doc_id: int, db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    db.execute(text("DELETE FROM salvos WHERE usuario_id=:u AND documento_id=:d"), {"u": uid, "d": doc_id})
    db.commit()
    return {"salvo": False}


# ---------- perguntas ----------
class PerguntaIn(BaseModel):
    pergunta: str = Field(min_length=5, max_length=1000)
    pasta: str | None = None
    documento_id: int | None = None


@router.post("/perguntar")
def perguntar(body: PerguntaIn, db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    if not _terms(body.pergunta):
        raise HTTPException(422, "Inclua palavras mais específicas na pergunta.")
    if body.documento_id:
        _one(db, body.documento_id, uid)  # 403 se o documento está fora do perfil
    return rag.ask(db, body.pergunta.strip(), body.pasta, body.documento_id, uid)


@router.get("/consultas")
def historico(db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    rows = db.execute(text(
        "SELECT id, pergunta, modo, suficiente, criado_em FROM consultas WHERE usuario_id=:u ORDER BY id DESC LIMIT 30"
    ), {"u": uid}).mappings().all()
    return [dict(r) for r in rows]


# ---------- classificação (somente perfil administrador) ----------
class ClassifIn(BaseModel):
    classificacao: str


@router.put("/documentos/{doc_id}/classificacao")
def reclassificar(doc_id: int, body: ClassifIn, db: Session = Depends(get_db), uid: int = Depends(auth.get_uid)):
    if not _perfil(db, uid)["admin"]:
        raise HTTPException(403, "Somente o perfil Administrador pode reclassificar documentos.")
    if body.classificacao not in pdfmeta.CLASSIFICACOES:
        raise HTTPException(422, "Classificação inválida. Use: " + ", ".join(pdfmeta.CLASSIFICACOES) + ".")
    d = _one(db, doc_id, uid)
    db.execute(text("UPDATE documentos SET classificacao=:c WHERE id=:i"), {"c": body.classificacao, "i": doc_id})
    db.execute(text("INSERT INTO log_acesso (usuario_id, documento_id, acao, detalhe) VALUES (:u,:d,'reclassificado',:t)"),
               {"u": uid, "d": doc_id, "t": f"{d['classificacao']} -> {body.classificacao}"})
    db.commit()
    return {"id": doc_id, "classificacao": body.classificacao}
