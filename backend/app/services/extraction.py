<<<<<<< HEAD
"""Extraction des PDF avec PyMuPDF.

Ce que fait ce module (exigences 4.1 de l'énoncé) :
  * extrait le texte en conservant le numéro de page ;
  * lit les métadonnées du document (référence, type, date, version, statut)
    dans le tableau clé/valeur de la page 1 ;
  * supprime les en-têtes et pieds de page répétés (détection générique :
    une ligne en haut/bas de page qui se répète sur plusieurs pages) ;
  * détecte les titres grâce à la police (gras + taille > corps du texte) ;
  * relie chaque ligne de tableau à ses en-têtes de colonnes :
      « Date ou période : ... — Événement : ... — Public : ... ».

Aucune règle n'est écrite en dur pour ce corpus : tout repose sur la structure
des PDF (polices, tableaux, libellés de la fiche signalétique).
"""
from __future__ import annotations

import hashlib
import re
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
=======

import hashlib
import re
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
from pathlib import Path

import pymupdf

<<<<<<< HEAD
MONTHS = {
    "janvier": 1, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11,
    "decembre": 12,
}
# Référence de document, ex. EIH-SRE-GUIDE-2026 ou EIH-DE-NS-2026-14
REF_RE = re.compile(r"\b[A-Z]{2,6}(?:-[A-Z0-9]+){2,}\b")

# Libellés (normalisés) de la fiche signalétique -> champ de métadonnée
FIELD_MAP = {
    "organisme emetteur": "organisme",
    "type de document": "type",
    "reference": "reference",
    "date de publication": "date_text",
    "version": "version_raw",
    "public vise": "public",
    "statut": "status",
}


@dataclass
class Block:
    """Unité de texte : titre, paragraphe, puce ou ligne de tableau."""
    kind: str            # "heading" | "para" | "bullet" | "table_row"
    text: str
    page: int
    level: int = 0       # niveau du titre (1 = le plus haut), 0 sinon
    size: float = 0.0    # taille de police (titres uniquement)


@dataclass
class ParsedDocument:
    file: str
    metadata: dict
    blocks: list[Block] = field(default_factory=list)


@dataclass
class _Line:
    text: str
    top: float
    bottom: float
    x0: float
    size: float
    bold: bool
    page: int


# ---------------------------------------------------------------- utilitaires
def _strip_accents(s: str) -> str:
    return "".join(
        c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c)
    )


def _norm_key(s: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents(s).lower()).strip(" :")


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = s.replace("\u00a0", " ").replace("\x00", "").replace("(cid:127)", "•")
    return re.sub(r"[ \t]+", " ", s).strip()


def parse_french_date(text: str) -> str | None:
    """'5 octobre 2026' / '1er septembre 2026' -> '2026-10-05'."""
    m = re.search(r"(\d{1,2})\s*(?:er)?\s+([A-Za-zéèêûôîàç]+)\s+(\d{4})", text or "")
    if not m:
        return None
    month = MONTHS.get(_strip_accents(m.group(2)).lower())
    if not month:
        return None
    return f"{int(m.group(3)):04d}-{month:02d}-{int(m.group(1)):02d}"


# ------------------------------------------------------------- lecture d'une page
def _is_bold(span: dict) -> bool:
    return bool(span["flags"] & 16) or "bold" in span["font"].lower()


def _merge_rows(lines: list[_Line]) -> list[_Line]:
    """Fusionne les morceaux situés sur la même ligne visuelle (même ordonnée)."""
    lines = sorted(lines, key=lambda l: (round(l.top), l.x0))
    merged: list[_Line] = []
    for ln in lines:
        if merged and abs(ln.top - merged[-1].top) < 2.5:
            prev = merged[-1]
            big = ln if len(ln.text) > len(prev.text) else prev
            merged[-1] = _Line(
                f"{prev.text} {ln.text}", min(prev.top, ln.top),
                max(prev.bottom, ln.bottom), min(prev.x0, ln.x0),
                big.size, prev.bold and ln.bold, prev.page,
            )
        else:
            merged.append(ln)
    return merged


def _page_lines(page, pno: int) -> list[_Line]:
    raw: list[_Line] = []
    for block in page.get_text("dict", sort=True)["blocks"]:
        if block.get("type") != 0:
            continue
        for line in block["lines"]:
            spans = [s for s in line["spans"] if s["text"].strip()]
            text = clean("".join(s["text"] for s in line["spans"]))
            if not spans or not text:
                continue
            sizes: Counter = Counter()
            bold_chars = total = 0
            for s in spans:
                n = len(s["text"].strip())
                sizes[round(s["size"], 1)] += n
                total += n
                if _is_bold(s):
                    bold_chars += n
            raw.append(_Line(
                text, line["bbox"][1], line["bbox"][3], line["bbox"][0],
                sizes.most_common(1)[0][0], bold_chars >= 0.98 * total, pno,
            ))
    return _merge_rows(raw)


def _cell_text(page, bbox) -> str:
    # find_tables().extract() perd les espaces : on relit chaque cellule
    # par sa géométrie, ce qui donne un texte propre.
    return clean(" ".join(page.get_text("text", clip=pymupdf.Rect(bbox)).split()))


def _page_tables(page) -> list[tuple[pymupdf.Rect, list[list[str]]]]:
    out = []
    try:
        finder = page.find_tables()
    except Exception:
        return out
    for t in finder.tables:
        rows = []
        for row in t.rows:
            cells = [_cell_text(page, c) if c else "" for c in row.cells]
            if any(cells):
                rows.append(cells)
        if rows:
            out.append((pymupdf.Rect(t.bbox), rows))
    return out


def _inside(ln: _Line, rect: pymupdf.Rect) -> bool:
    mid = (ln.top + ln.bottom) / 2
    return rect.y0 - 1 <= mid <= rect.y1 + 1 and rect.x0 - 2 <= ln.x0 <= rect.x1


def _table_blocks(rows: list[list[str]], page: int) -> list[Block]:
    """Chaque ligne devient « En-tête : valeur — En-tête : valeur ... »."""
    if len(rows) < 2:
        return []
    header = [h or f"Colonne {i + 1}" for i, h in enumerate(rows[0])]
    blocks = []
    for r in rows[1:]:
        parts = [f"{h} : {c}" for h, c in zip(header, r) if c]
        if parts:
            blocks.append(Block("table_row", " — ".join(parts), page))
    return blocks


# ------------------------------------------------------------------ métadonnées
def _parse_meta_table(rows: list[list[str]]) -> dict:
    meta = {}
    for r in rows:
        if len(r) >= 2:
            key = FIELD_MAP.get(_norm_key(r[0]))
            if key:
                meta[key] = r[1]
    return meta


def _is_meta_table(rows: list[list[str]]) -> bool:
    return any(len(r) >= 2 and _norm_key(r[0]) == "reference" for r in rows)


def _build_metadata(raw: dict, file: str, title: str, subtitle: str,
                    n_pages: int, document_id: str) -> dict:
    reference = raw.get("reference") or (REF_RE.search(file) or [Path(file).stem])[0]
    version_raw = raw.get("version_raw", "")
    vm = re.match(r"\s*v?(\d+(?:\.\d+)*)", version_raw)
    status = raw.get("status", "")
    doc_type = raw.get("type", "")

    # Un document « se déclare modificatif » quand son statut ou son type parle
    # de modification ET cite la référence d'un autre document.
    modifies: list[str] = []
    if re.search(r"modifi", f"{status} {doc_type}", re.I):
        modifies = [r for r in dict.fromkeys(REF_RE.findall(status)) if r != reference]

    return {
        "source": file,
        "document_id": document_id,
        "title": title,
        "subtitle": subtitle,
        "organisme": raw.get("organisme", ""),
        "type": doc_type or "Document",
        "reference": reference,
        "date": parse_french_date(raw.get("date_text", "")) or "",
        "date_text": raw.get("date_text", ""),
        "version": vm.group(1) if vm else "",
        "version_raw": version_raw,
        "status": status,
        "public": raw.get("public", ""),
        "n_pages": n_pages,
        "modifies": modifies,
        "modified_by": [],   # calculé à l'ingestion, quand tous les documents sont connus
    }


# ---------------------------------------------------------------- extraction
def extract_document(pdf_path: Path) -> ParsedDocument:
    pdf_path = Path(pdf_path)
    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Fichier PDF invalide : {pdf_path}")
    document_id = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]

    pages = []   # (lines, tables) par page
    with pymupdf.open(pdf_path) as pdf:
        pdf_title = (pdf.metadata or {}).get("title") or ""
        n_pages = len(pdf)
        for pno, page in enumerate(pdf, start=1):
            pages.append((_page_lines(page, pno), _page_tables(page)))

    # 1. lignes hors tableaux
    free_lines: list[list[_Line]] = []
    for lines, tables in pages:
        free_lines.append([l for l in lines if not any(_inside(l, r) for r, _ in tables)])

    # 2. en-têtes / pieds de page : 2 premières et 2 dernières lignes de page
    #    qui se répètent (chiffres neutralisés) sur au moins 2 pages
    def norm(l: _Line) -> str:
        return re.sub(r"\d+", "#", l.text)

    counts: Counter = Counter()
    for lines in free_lines:
        cands = lines[:2] + lines[-2:] if len(lines) > 4 else lines
        counts.update({norm(l) for l in cands})
    repeated = {k for k, c in counts.items() if c >= 2 and n_pages >= 2}
    free_lines = [
        [l for l in lines
         if not (norm(l) in repeated and (l in lines[:2] or l in lines[-2:]))]
        for lines in free_lines
    ]

    # 3. fiche signalétique + page de garde (page 1)
    raw_meta: dict = {}
    meta_rect = None
    non_meta_tables: list[list[tuple]] = []
    for i, (_, tables) in enumerate(pages):
        keep = []
        for rect, rows in tables:
            if i == 0 and meta_rect is None and _is_meta_table(rows):
                raw_meta, meta_rect = _parse_meta_table(rows), rect
            else:
                keep.append((rect, rows))
        non_meta_tables.append(keep)

    cover: list[_Line] = []
    if meta_rect is not None:
        cover = [l for l in free_lines[0] if l.bottom <= meta_rect.y0 + 2]
        free_lines[0] = [l for l in free_lines[0] if l not in cover]
    title = clean(pdf_title)
    subtitle = ""
    if cover:
        big = max(l.size for l in cover)
        main = [l.text for l in cover if l.size >= big - 0.1]
        subtitle = " ".join(l.text for l in cover if l.size < big - 0.1)
        title = title or " ".join(main)
    title = title or pdf_path.stem

    # 4. taille du corps de texte = taille la plus fréquente (pondérée)
    size_counts: Counter = Counter()
    for lines in free_lines:
        for l in lines:
            size_counts[l.size] += len(l.text)
    body = size_counts.most_common(1)[0][0] if size_counts else 10.0

    def is_heading(l: _Line) -> bool:
        return l.bold and l.size >= body + 0.3 and len(l.text) <= 160

    # 5. construction des blocs dans l'ordre de lecture
    blocks: list[Block] = []
    buf: dict | None = None
    last_heading = None  # (size, bottom, page)

    def flush():
        nonlocal buf
        if buf and buf["text"].strip():
            blocks.append(Block(buf["kind"], buf["text"].strip(), buf["page"]))
        buf = None

    for pno in range(1, n_pages + 1):
        items = [(l.top, "line", l) for l in free_lines[pno - 1]]
        items += [(r.y0, "table", rows) for r, rows in non_meta_tables[pno - 1]]
        for _, kind, obj in sorted(items, key=lambda x: x[0]):
            if kind == "table":
                flush()
                blocks.extend(_table_blocks(obj, pno))
                last_heading = None
                continue
            ln: _Line = obj
            if is_heading(ln):
                if (last_heading and not buf and blocks and blocks[-1].kind == "heading"
                        and last_heading[0] == ln.size and last_heading[2] == pno
                        and ln.top - last_heading[1] < ln.size * 0.9):
                    blocks[-1].text += " " + ln.text      # titre sur 2 lignes
                else:
                    flush()
                    blocks.append(Block("heading", ln.text, pno, size=ln.size))
                last_heading = (ln.size, ln.bottom, pno)
                continue
            last_heading = None
            starts_item = ln.text.startswith("•") or re.match(r"^\d{1,2}[.)]\s+\S", ln.text)
            if starts_item:
                flush()
                buf = {"kind": "bullet", "text": ln.text, "page": pno, "bottom": ln.bottom}
                continue
            if buf:
                same_page = buf["page"] == pno or True
                gap = ln.top - buf["bottom"]
                cross_page = ln.page != buf.get("last_page", buf["page"])
                joined = (
                    not re.search(r"[.;:!?]$", buf["text"]) if cross_page
                    else gap <= 0.45 * ln.size
                )
                if joined and same_page:
                    sep = "" if buf["text"].endswith("-") else " "
                    buf["text"] = buf["text"].rstrip("-") + sep + ln.text if sep == "" \
                        else buf["text"] + sep + ln.text
                    buf["bottom"], buf["last_page"] = ln.bottom, ln.page
                    continue
            flush()
            buf = {"kind": "para", "text": ln.text, "page": pno, "bottom": ln.bottom}
    flush()

    # 6. niveaux de titres : taille la plus grande = niveau 1
    sizes = sorted({b.size for b in blocks if b.kind == "heading"}, reverse=True)
    for b in blocks:
        if b.kind == "heading":
            b.level = sizes.index(b.size) + 1

    metadata = _build_metadata(raw_meta, pdf_path.name, title, subtitle, n_pages, document_id)
    return ParsedDocument(file=pdf_path.name, metadata=metadata, blocks=blocks)


def extract_corpus(corpus_dir: Path) -> list[ParsedDocument]:
    """Extrait tous les PDF du dossier (non récursif) et relie les documents
    modificatifs aux documents qu'ils modifient (champ `modified_by`)."""
    corpus_dir = Path(corpus_dir)
    if not corpus_dir.exists():
        raise FileNotFoundError(f"Le dossier du corpus n'existe pas : {corpus_dir}")
    docs = [extract_document(p) for p in sorted(corpus_dir.glob("*.pdf"))]

    by_ref = {d.metadata["reference"]: d for d in docs}
    for d in docs:
        d.metadata["modifies"] = [r for r in d.metadata["modifies"] if r in by_ref]
        for target in d.metadata["modifies"]:
            by_ref[target].metadata["modified_by"].append(d.metadata["reference"])
    return docs
=======

def normalize_text(text: str) -> str:
    """Nettoie le texte extrait sans supprimer les paragraphes."""
    text = text.replace("\x00", "")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_pdf(pdf_path: Path) -> list[dict]:
    """Extrait le texte de chaque page d'un PDF avec ses métadonnées."""
    pdf_path = Path(pdf_path)

    if not pdf_path.exists() or pdf_path.suffix.lower() != ".pdf":
        raise ValueError(f"Fichier PDF invalide : {pdf_path}")

    document_id = hashlib.sha256(pdf_path.read_bytes()).hexdigest()[:16]
    pages = []

    with pymupdf.open(pdf_path) as pdf:
        pdf_metadata = pdf.metadata or {}

        for page_number, page in enumerate(pdf, start=1):
            text = normalize_text(page.get_text("text"))

            # On conserve les pages même si elles ne contiennent pas de texte.
            pages.append({
                "document_id": document_id,
                "source": pdf_path.name,
                "page": page_number,
                "text": text,
                "metadata": {
                    "title": pdf_metadata.get("title") or pdf_path.stem,
                    "source": pdf_path.name,
                    "document_id": document_id,
                    "page": page_number,
                    "type": infer_document_type(pdf_path.stem),
                    "version": infer_version(pdf_path.stem),
                    "status": "active",
                },
            })

    return pages


def infer_document_type(filename: str) -> str:
    """Déduit une catégorie à partir du nom du fichier."""
    name = filename.lower()

    categories = {
        "reglement": "reglement",
        "règlement": "reglement",
        "stage": "stage",
        "pfe": "stage",
        "mobilite": "mobilite",
        "mobilité": "mobilite",
        "calendrier": "calendrier",
        "faq": "faq",
        "vie_etudiante": "vie_etudiante",
        "vie-etudiante": "vie_etudiante",
        "note_service": "note_service",
        "note-service": "note_service",
    }

    for keyword, category in categories.items():
        if keyword in name:
            return category

    return "autre"


def infer_version(filename: str) -> str | None:
    """Repère une version explicite comme v1 ou version_2."""
    match = re.search(
        r"(?:version[_ -]?|v)(\d+(?:\.\d+)*)",
        filename.lower(),
    )
    return match.group(1) if match else None


def extract_corpus(corpus_dir: Path) -> list[dict]:
    """Extrait toutes les pages des PDF présents dans un dossier."""
    corpus_dir = Path(corpus_dir)

    if not corpus_dir.exists():
        raise FileNotFoundError(
            f"Le dossier du corpus n'existe pas : {corpus_dir}"
        )

    all_pages = []

    for pdf_path in sorted(corpus_dir.glob("*.pdf")):
        print(f"Extraction : {pdf_path.name}")
        all_pages.extend(extract_pdf(pdf_path))

    return all_pages
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
