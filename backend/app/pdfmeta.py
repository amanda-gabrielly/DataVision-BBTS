"""Leitura do PDF: texto por página, metadados da capa (padrão ACME) e divisão em trechos."""
import re
from datetime import date
from io import BytesIO

from pypdf import PdfReader

from . import config

TIPOS = {
    "NG": "Norma Geral", "PX": "Procedimento", "PP": "Padrão Operacional", "GU": "Guia",
    "FM": "Formulário", "TB": "Tabela", "FL": "Fluxo", "RG": "Regulamento de Programa",
    "CT": "Comunicado Temporário", "DV": "Documento Diverso", "CTR": "Contrato",
    "NT": "Nota Técnica", "CAT": "Catálogo",
}


class PDFSemTexto(ValueError):
    pass


def read_pages(content: bytes) -> list[tuple[int, str]]:
    reader = PdfReader(BytesIO(content))
    return [(n, (p.extract_text() or "").strip()) for n, p in enumerate(reader.pages, start=1)]


def split_into_chunks(pages: list[tuple[int, str]], size: int | None = None, overlap: int | None = None):
    """Mesma regra do laboratório de IA (1100/180), para reaproveitar os embeddings já calculados."""
    size = size or config.CHUNK_SIZE
    overlap = overlap if overlap is not None else config.CHUNK_OVERLAP
    out: list[tuple[int, str]] = []
    for page, text in pages:
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            piece = text[start:end].strip()
            if piece:
                out.append((page, piece))
            if end == len(text):
                break
            start = max(end - overlap, start + 1)
    return out


def _d(s: str) -> date | None:
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", s or "")
    if not m:
        return None
    try:
        return date(int(m[3]), int(m[2]), int(m[1]))
    except ValueError:
        return None


def _one_line(s: str | None) -> str | None:
    return re.sub(r"\s+", " ", s).strip() if s else None


def parse_filename(name: str) -> dict:
    m = re.match(r"^([A-Za-z]+_[\w-]+?)__(.+?)__v(\d+(?:\.\d+)*)", name)
    if not m:
        return {}
    return {"codigo": m[1], "titulo": m[2].replace("_", " ").title(), "versao": m[3]}


CLASSIFICACOES = ("publica", "interna", "restrita", "confidencial")


def _fold_classif(v: str) -> str:
    return v.lower().replace("ú", "u")


def parse_cover(first_page: str) -> dict:
    """Extrai os campos da capa: Documento, Título, Sigla e Número, Versão, Fase, Vigência etc."""
    t = first_page
    meta: dict = {}
    if m := re.search(r"Documento:\s*(.+)", t):
        meta["tipo"] = _one_line(m[1])
    if m := re.search(r"Título:\s*(.+?)\s*Sigla e Número:", t, re.S):
        meta["titulo"] = _one_line(m[1])
    if m := re.search(r"Sigla e Número:\s*(\S+)\s+Versão:\s*(\d+(?:\.\d+)*)", t):
        meta["codigo"], meta["versao"] = m[1], m[2]
    if m := re.search(r"Elaborado por:\s*(.+?)\s*(?:Aprovado por:|Refer[êe]ncia:|Vinculado a:|Fase:)", t, re.S):
        meta["elaborado_por"] = _one_line(m[1])
    if m := re.search(r"Aprovado por:\s*(.+?)\s*(?:Fase:|Refer[êe]ncia:|Vinculado a:)", t, re.S):
        meta["aprovado_por"] = _one_line(m[1])
    if m := re.search(r"Fase:\s*(Vigente|Vers[ãa]o anterior|Revogad[oa]|Rascunho)", t, re.I):
        meta["fase"] = m[1].strip()
    if m := re.search(r"Vig[êe]ncia:\s*(\d{2}/\d{2}/\d{4})\s*a\s*(\d{2}/\d{2}/\d{4})", t):
        meta["vigencia_inicio"], meta["vigencia_fim"] = _d(m[1]), _d(m[2])
    if m := re.search(r"(?:Aprovado em|Assinada? em|Assinada em):\s*(\d{2}/\d{2}/\d{4})", t):
        meta["data_documento"] = _d(m[1])
    if m := re.search(r"(?:Vinculado a|Refer[êe]ncia):\s*([A-Z]+_[\w-]+)", t):
        meta["vinculado_a"] = m[1]
    if m := re.search(r"#\s*(p[úu]blica|interna|restrita|confidencial)\b", t, re.I):
        meta["classificacao"] = _fold_classif(m[1])
    return meta


def version_key(v: str) -> tuple:
    return tuple(int(x) for x in re.findall(r"\d+", v))


def analyze(filename: str, content: bytes) -> dict:
    pages = read_pages(content)
    if not any(t for _, t in pages):
        raise PDFSemTexto(
            "Este PDF não contém texto selecionável. Parece digitalizado; OCR ainda não está ativo."
        )
    meta = parse_cover(pages[0][1])
    fn = parse_filename(filename)
    for k in ("codigo", "titulo", "versao"):
        meta.setdefault(k, fn.get(k))
    if not meta.get("codigo"):
        stem = re.sub(r"\.pdf$", "", filename, flags=re.I)
        meta["codigo"] = re.sub(r"[^\w-]+", "_", stem)[:40].upper()
        meta["titulo"] = meta.get("titulo") or stem
    meta["versao"] = meta.get("versao") or "1.0.0"
    if not meta.get("tipo"):
        meta["tipo"] = TIPOS.get(meta["codigo"].split("_")[0].upper(), "Documento")
    meta["paginas"] = len(pages)
    meta["pages"] = pages
    meta["empty_pages"] = sum(1 for _, t in pages if not t)
    return meta
