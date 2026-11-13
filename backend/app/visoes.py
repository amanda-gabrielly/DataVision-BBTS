"""Visões de um documento (mapa mental, fluxograma, quadro, números, gráfico).

Tudo é derivado do texto real do PDF e cada elemento carrega a página de origem (`fonte`).
Nada é inventado: se o documento não tem a informação, a visão volta vazia com um aviso.
"""
import re

from sqlalchemy import text
from sqlalchemy.orm import Session

from .textutil import merge_overlapping

PERSPECTIVAS = {
    "prazos": re.compile(r"\b\d+\s*(?:dias?|meses|m[êe]s|anos?|horas?)\b|\bD-\d+\b|\bat[ée]\s+\d{1,2}\s+de\s+\w+", re.I),
    "valores": re.compile(r"R\$\s?[\d.]+(?:,\d{2})?|\b\d+(?:,\d+)?\s?%", re.I),
    "obrigacoes": re.compile(r"\b(?:deve|devem|dever[aá]|cabe|compete|obriga\w*|obrigat\w*|exige|exigid|necess[áa]ri)\w*", re.I),
    "riscos": re.compile(r"\b(?:multa|penalidade|rescis|veda|vedad|n[ãa]o pode|san[çc][ãa]o|descumpr|proibid|inadimpl|perda)\w*", re.I),
}
NUM_ITEM = re.compile(r"^(\d+(?:\.\d+){1,3})\.\s+(.+)$")
HEAD1 = re.compile(r"^(\d{1,2})\.\s+([A-ZÀ-Ú][^\n.:;]{2,44})$")  # "4. Diretrizes" (curto, sem pontuação)
CLAUSE = re.compile(r"^CL[ÁA]USULA\s+([A-ZÀ-Ú ]+?)\s+[—–-]\s+([^.]{2,80})\.\s*(.*)$")
TABELA = re.compile(r"^Tabela\s+(\d+)\s+[—–-]\s+(.+)$")
ANEXO = re.compile(r"^Anexo\b")
SKIP_TEXT = re.compile(r"^Hist[óo]rico de vers", re.I)
ORDINAIS = {"PRIMEIRA": 1, "SEGUNDA": 2, "TERCEIRA": 3, "QUARTA": 4, "QUINTA": 5, "SEXTA": 6, "SÉTIMA": 7, "SETIMA": 7,
            "OITAVA": 8, "NONA": 9, "DÉCIMA": 10, "DECIMA": 10, "VIGÉSIMA": 20, "VIGESIMA": 20}


def _starter(ln: str) -> bool:
    return bool(NUM_ITEM.match(ln) or HEAD1.match(ln) or CLAUSE.match(ln) or TABELA.match(ln) or ANEXO.match(ln))


def load_pages(db: Session, versao_id: int) -> dict[int, str]:
    rows = db.execute(
        text("SELECT pagina, conteudo FROM trechos WHERE versao_id=:v ORDER BY pagina, ordem"), {"v": versao_id}
    ).all()
    by_page: dict[int, list[str]] = {}
    for r in rows:
        by_page.setdefault(r.pagina, []).append(r.conteudo)
    return {p: merge_overlapping(parts) for p, parts in by_page.items()}


def logical_lines(pages: dict[int, str]) -> list[tuple[int, str]]:
    """Linhas lógicas (página onde começam). Une linhas quebradas pelo PDF, inclusive entre páginas."""
    out: list[tuple[int, str]] = []
    for page, body in sorted(pages.items()):
        for ln in (l.strip() for l in body.split("\n")):
            if not ln or ln.startswith("--- p."):
                continue
            if out and not _starter(ln) and not HEAD1.match(out[-1][1]) and not TABELA.match(out[-1][1]):
                out[-1] = (out[-1][0], out[-1][1] + " " + ln)
            else:
                out.append((page, ln))
    return out


def _ordinal(words: str) -> int:
    n = 0
    for w in words.split():
        n += ORDINAIS.get(w, 0)
    return n or 0


def items(pages: dict[int, str]) -> list[dict]:
    """Itens citáveis: numerados (4.3.1), cláusulas (CLÁUSULA SÉTIMA) e tabelas. Sempre com a página."""
    out, seen = [], set()
    for page, ln in logical_lines(pages):
        if m := NUM_ITEM.match(ln):
            ref, txt = m[1], m[2].strip()
            if ref in seen or SKIP_TEXT.match(txt):
                continue
            seen.add(ref)
            out.append({"ref": ref, "titulo": None, "texto": txt, "pagina": page})
        elif m := CLAUSE.match(ln):
            n = _ordinal(m[1])
            ref = f"Cláusula {n}" if n else f"Cláusula {m[1].title()}"
            if ref in seen:
                continue
            seen.add(ref)
            out.append({"ref": ref, "titulo": m[2].strip(), "texto": (m[2].strip() + ". " + m[3]).strip(), "pagina": page})
    return out


def _short(s: str, n: int = 56) -> str:
    s = re.split(r"[:;]", s, maxsplit=1)[0].strip().rstrip(".")
    return s if len(s) <= n else s[: n - 1].rsplit(" ", 1)[0] + "…"


def mapa(doc: dict, pages: dict[int, str]) -> dict:
    ramos: dict[str, dict] = {}
    lines = logical_lines(pages)
    for page, ln in lines:
        if m := HEAD1.match(ln):
            ramos.setdefault(m[1], {"id": m[1], "titulo": m[2].rstrip("."), "pagina": page, "filhos": []})
    its = items(pages)
    for it in its:
        parts = it["ref"].split(".")
        if len(parts) == 2 and parts[0] in ramos:
            ramos[parts[0]]["filhos"].append({
                "id": it["ref"], "titulo": _short(it["texto"]), "pagina": it["pagina"], "trecho": it["texto"][:280],
            })
    lista = [r for r in sorted(ramos.values(), key=lambda r: int(r["id"]))]
    if not lista:  # contratos: cada cláusula vira um ramo
        lista = [{"id": it["ref"], "titulo": it["titulo"] or _short(it["texto"]), "pagina": it["pagina"], "filhos": [],
                  "trecho": it["texto"][:280]} for it in its if it["ref"].startswith("Cláusula")]
    if not lista:  # tabelas
        for page, ln in lines:
            if m := TABELA.match(ln):
                lista.append({"id": f"Tabela {m[1]}", "titulo": m[2].strip()[:70], "pagina": page, "filhos": []})
    return {
        "raiz": {"codigo": doc["codigo"], "titulo": doc["titulo"]},
        "ramos": lista,
        "aviso": None if lista else "Este documento não tem seções, cláusulas ou tabelas identificáveis para montar o mapa.",
    }


def classify(txt: str) -> list[str]:
    return [k for k, rx in PERSPECTIVAS.items() if rx.search(txt)]


def quadro(pages: dict[int, str]) -> list[dict]:
    rows = []
    for it in items(pages):
        tags = classify(it["texto"])
        if not tags:
            continue
        val = None
        for k in ("valores", "prazos"):
            if m := PERSPECTIVAS[k].search(it["texto"]):
                val = m[0]
                break
        rows.append({**it, "perspectivas": tags, "destaque": val})
    if not rows:  # tabelas: cada linha que traz prazo/valor
        tabela = None
        for page, ln in logical_lines(pages):
            if m := TABELA.match(ln):
                tabela = f"Tabela {m[1]}"
            elif tabela and (tags := classify(ln)) and not ln.startswith(("Etapa ", "Faltas ")):
                v = next((mm[0] for k in ("valores", "prazos") if (mm := PERSPECTIVAS[k].search(ln))), None)
                rows.append({"ref": tabela, "titulo": None, "texto": ln, "pagina": page, "perspectivas": tags, "destaque": v})
    return rows


def numeros(rows: list[dict], limite: int = 6) -> list[dict]:
    out, seen = [], set()
    for r in rows:
        if r["destaque"] and r["destaque"] not in seen and ("valores" in r["perspectivas"] or "prazos" in r["perspectivas"]):
            seen.add(r["destaque"])
            out.append({"valor": r["destaque"], "contexto": r.get("titulo") or _short(r["texto"], 110), "pagina": r["pagina"], "ref": r["ref"],
                        "tipo": "valor" if "valores" in r["perspectivas"] else "prazo"})
    return out[:limite]


def grafico(rows: list[dict]) -> dict:
    por_persp = {k: sum(1 for r in rows if k in r["perspectivas"]) for k in PERSPECTIVAS}
    barras = []
    for r in rows:
        if "prazos" not in r["perspectivas"] or not r["destaque"]:
            continue
        m = re.search(r"(\d+)\s*(dias?|meses|m[êe]s|anos?)", r["destaque"], re.I)
        if not m:
            continue
        n = int(m[1]); un = m[2].lower()
        dias = n if un.startswith("dia") else n * 30 if un.startswith("m") else n * 365
        barras.append({"rotulo": r.get("titulo") or _short(r["texto"], 38), "dias": dias, "texto": r["destaque"], "pagina": r["pagina"], "ref": r["ref"]})
    return {"por_perspectiva": por_persp, "prazos": barras[:10]}


# ---------- fluxograma ----------
_NODE = r"(\w+)(?:\s*([\[\{\(])([^\]\}\)]*)[\]\}\)])?"
EDGE_RX = re.compile(_NODE + r"\s*(?:--\s*([^\->|]+?)\s*-->|-->\s*(?:\|([^|]+)\|)?)\s*" + _NODE, re.S)


def parse_mermaid(src: str):
    src = re.sub(r"\s+", " ", src)
    labels, shapes, edges, order = {}, {}, [], []

    def reg(i, br, lab):
        if i not in order:
            order.append(i)
        if lab:
            labels[i] = lab.strip()
            shapes[i] = br
    pos = 0
    while pos < len(src):
        m = EDGE_RX.search(src, pos)
        if not m:
            break
        a, br1, l1, e1, e2, b, br2, l2 = m.groups()
        reg(a, br1, l1); reg(b, br2, l2)
        edges.append({"de": a, "para": b, "rotulo": (e1 or e2 or "").strip() or None})
        pos = m.start(5) if False else m.end() - len(b) - (len(l2) + 2 if l2 else 0)  # permite encadear A-->B-->C
    return order, labels, shapes, edges


def fluxo(doc: dict, pages: dict[int, str], rows: list[dict]) -> dict:
    for page, body in sorted(pages.items()):
        if "flowchart" in body or "graph TD" in body or "graph LR" in body:
            blk = body.split("flowchart", 1)[-1] if "flowchart" in body else body
            blk = re.sub(r"^\s*(TD|LR|TB|RL)\b", "", blk)
            blk = re.split(r"Legenda:", blk)[0]
            order, labels, shapes, edges = parse_mermaid(blk)
            if edges:
                saem = {e["de"] for e in edges}; entram = {e["para"] for e in edges}
                nos = []
                for i in order:
                    tipo = "decisao" if shapes.get(i) == "{" else "inicio" if i not in entram else "fim" if i not in saem else "etapa"
                    nos.append({"id": i, "rotulo": labels.get(i, i), "tipo": tipo, "pagina": page})
                legenda = re.search(r"Legenda:\s*(.+)", body)
                return {"origem": "mermaid", "nos": nos, "arestas": edges, "legenda": legenda[1].strip() if legenda else None, "aviso": None}
    prazos = [r for r in rows if "prazos" in r["perspectivas"]][:9]
    if not prazos:
        return {"origem": None, "nos": [], "arestas": [], "legenda": None,
                "aviso": "Este documento não traz um fluxo desenhado nem prazos suficientes para montar uma sequência."}
    nos = [{"id": f"n{i}", "rotulo": _short(r["texto"], 70), "tipo": "inicio" if i == 0 else "fim" if i == len(prazos) - 1 else "etapa",
            "pagina": r["pagina"], "ref": r["ref"]} for i, r in enumerate(prazos)]
    arestas = [{"de": nos[i]["id"], "para": nos[i + 1]["id"], "rotulo": None} for i in range(len(nos) - 1)]
    return {"origem": "prazos", "nos": nos, "arestas": arestas, "legenda": None,
            "aviso": "O PDF não traz fluxograma: a sequência abaixo vem dos prazos citados no texto."}


def build(db: Session, versao_id: int, doc: dict) -> dict:
    pages = load_pages(db, versao_id)
    rows = quadro(pages)
    return {
        "mapa": mapa(doc, pages),
        "fluxo": fluxo(doc, pages, rows),
        "quadro": rows,
        "numeros": numeros(rows),
        "grafico": grafico(rows),
    }
