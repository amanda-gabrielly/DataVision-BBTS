import re
import unicodedata


def fold(s: str) -> str:
    """minúsculas e sem acentos, para comparar termos."""
    return "".join(c for c in unicodedata.normalize("NFD", s.lower()) if unicodedata.category(c) != "Mn")


STOPWORDS = set(
    "a o as os um uma uns umas de do da dos das em no na nos nas por para com sem sob sobre e ou mas que se "
    "ao aos qual quais quanto quantos quando onde como qual existe existem ha ser sao foi esta estao tem "
    "tambem entre ate sua seu suas seus este esta isso isto aquele essa esse mais menos muito pelo pela".split()
)


def raw_terms(question: str) -> list[str]:
    """Termos relevantes em minúsculas, COM acento (o índice de texto do PostgreSQL guarda as palavras acentuadas)."""
    out, seen = [], set()
    for w in re.findall(r"[a-zà-ú0-9_]+", question.lower()):
        f = fold(w)
        if len(f) > 2 and f not in STOPWORDS and f not in seen:
            seen.add(f)
            out.append(w)
    return out


def terms(question: str) -> list[str]:
    out, seen = [], set()
    for w in re.findall(r"[a-z0-9_]+", fold(question)):
        if len(w) > 2 and w not in STOPWORDS and w not in seen:
            seen.add(w)
            out.append(w)
    return out


def merge_overlapping(parts: list[str]) -> str:
    """Reconstrói o texto de uma página a partir de trechos consecutivos com sobreposição."""
    if not parts:
        return ""
    out = parts[0]
    for nxt in parts[1:]:
        k = min(len(out), len(nxt), 400)
        while k >= 15 and not out.endswith(nxt[:k]):
            k -= 1
        out += nxt[k:] if k >= 15 else "\n" + nxt
    return out
