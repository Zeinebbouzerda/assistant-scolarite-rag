<<<<<<< HEAD
"""Découpage des documents en fragments (exigences 4.2 de l'énoncé).

Deux stratégies, écrites à la main et configurables :

  (a) "fixed"      taille fixe + chevauchement, sur le flux de texte du
                   document entier (les fragments peuvent donc traverser un
                   saut de page). On coupe de préférence à une fin de ligne,
                   de phrase ou entre deux mots, jamais au milieu d'un mot.

  (b) "structural" un fragment par section : on suit les titres détectés
                   (Titre / Article / Q-R de la FAQ / 2.1 ...). Une section
                   plus grande que `chunk_size` est redécoupée en regroupant
                   des blocs entiers (une ligne de tableau n'est jamais
                   coupée) ; un bloc trop gros est coupé comme en (a).

Chaque fragment porte : identifiant, fichier, référence, type, date, page,
section, plus le titre/statut/version et les liens de modification.
"""
from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass, field

from backend.app.services.extraction import Block, ParsedDocument

STRATEGIES = ("fixed", "structural")


def validate_params(strategy: str, chunk_size: int, overlap: int) -> None:
    if strategy not in STRATEGIES:
        raise ValueError(f"Stratégie inconnue : {strategy!r} (attendu : {STRATEGIES}).")
    if chunk_size < 50:
        raise ValueError("chunk_size doit valoir au moins 50 caractères.")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_overlap doit être >= 0 et < chunk_size.")


@dataclass
class Chunk:
    chunk_id: str
    text: str                 # texte affiché / transmis au LLM
    embed_text: str           # texte réellement encodé (avec en-tête contextuel)
    metadata: dict
    strategy: str
    start: int | None = None  # positions dans le flux (stratégie "fixed")
    end: int | None = None
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = {"chunk_id": self.chunk_id, "text": self.text,
             "metadata": self.metadata, "strategy": self.strategy}
        if self.start is not None:
            d["start"], d["end"] = self.start, self.end
        return d


# ------------------------------------------------------------------ fenêtres
def window_spans(text: str, size: int, overlap: int) -> list[tuple[int, int]]:
    """Fenêtres [début, fin) de ~`size` caractères avec `overlap` de recouvrement."""
    if size <= 0 or not 0 <= overlap < size:
        raise ValueError("paramètres de fenêtre invalides")
    n, start, spans = len(text), 0, []
    while start < n:
        end = min(start + size, n)
        if end < n:
            # coupure naturelle dans le dernier quart de la fenêtre
            lo = start + int(size * 0.75)
            for sep in ("\n", ". ", " "):
                idx = text.rfind(sep, lo, end)
                if idx != -1:
                    end = idx + len(sep)
                    break
        spans.append((start, end))
        if end >= n:
            break
        nxt = end - overlap
        # ne pas démarrer au milieu d'un mot : avancer jusqu'au début du mot suivant
        while overlap and nxt < end and not text[nxt - 1].isspace():
            nxt += 1
        start = nxt if nxt > start else end   # garantit la progression
    return spans


# ------------------------------------------------------------------ sections
def section_paths(doc: ParsedDocument) -> list[str]:
    """Chemin hiérarchique de chaque bloc : « Titre III > Article 6 — ... »."""
    stack: list[tuple[int, str]] = []
    out = []
    for b in doc.blocks:
        if b.kind == "heading":
            while stack and stack[-1][0] >= b.level:
                stack.pop()
            stack.append((b.level, b.text))
        out.append(" > ".join(t for _, t in stack) or doc.metadata["title"])
    return out


def _chunk_metadata(doc: ParsedDocument, page: int, section: str,
                    strategy: str, index: int) -> dict:
    m = doc.metadata
    return {
        "source": m["source"], "document_id": m["document_id"],
        "reference": m["reference"], "title": m["title"], "type": m["type"],
        "date": m["date"], "version": m["version"], "status": m["status"],
        "organisme": m["organisme"],
        "modifies": ",".join(m["modifies"]),
        "modified_by": ",".join(m["modified_by"]),
        "page": page, "section": section,
        "strategy": strategy, "chunk_index": index,
    }


def _embed_text(doc: ParsedDocument, section: str, text: str, contextual: bool) -> str:
    # En-tête contextuel : le titre du document et la section précèdent le
    # texte encodé. Il aide la recherche (« Article 14 » ne figure parfois pas
    # dans le corps du fragment) sans modifier le texte montré à l'utilisateur.
    return f"{doc.metadata['title']} — {section}\n{text}" if contextual else text


# --------------------------------------------------------------- stratégie (a)
def chunk_fixed(doc: ParsedDocument, size: int, overlap: int,
                contextual_header: bool = True) -> list[Chunk]:
    text, starts = "", []
    for b in doc.blocks:
        if text:
            text += "\n"
        starts.append(len(text))
        text += b.text
    paths = section_paths(doc)

    chunks = []
    for s, e in window_spans(text, size, overlap):
        raw = text[s:e]
        piece = raw.strip()
        if not piece:
            continue
        s_real = s + (len(raw) - len(raw.lstrip()))
        bi = max(bisect_right(starts, s_real) - 1, 0)
        idx = len(chunks)
        meta = _chunk_metadata(doc, doc.blocks[bi].page, paths[bi], "fixed", idx)
        chunks.append(Chunk(
            chunk_id=f"{doc.metadata['reference']}::fixed::{idx:03d}",
            text=piece, embed_text=_embed_text(doc, paths[bi], piece, contextual_header),
            metadata=meta, strategy="fixed", start=s_real, end=e,
        ))
    return chunks


# --------------------------------------------------------------- stratégie (b)
def chunk_structural(doc: ParsedDocument, size: int, overlap: int,
                     contextual_header: bool = True) -> list[Chunk]:
    paths = section_paths(doc)

    # une « section » = un titre (de n'importe quel niveau) et les blocs qui
    # le suivent jusqu'au titre suivant ; un parent sans texte propre est ignoré
    sections: list[dict] = [{"heading": None, "path": doc.metadata["title"], "body": []}]
    for i, b in enumerate(doc.blocks):
        if b.kind == "heading":
            sections.append({"heading": b, "path": paths[i], "body": []})
        else:
            sections[-1]["body"].append(b)

    chunks: list[Chunk] = []

    def emit(path: str, text: str, page: int):
        idx = len(chunks)
        chunks.append(Chunk(
            chunk_id=f"{doc.metadata['reference']}::structural::{idx:03d}",
            text=text, embed_text=_embed_text(doc, path, text, contextual_header),
            metadata=_chunk_metadata(doc, page, path, "structural", idx),
            strategy="structural",
        ))

    for sec in sections:
        body: list[Block] = sec["body"]
        if not body:
            continue
        head: Block | None = sec["heading"]
        prefix = (head.text + "\n") if head else ""
        room = max(size - len(prefix), 100)
        current: list[Block] = []
        length = 0

        def flush():
            nonlocal current, length
            if current:
                emit(sec["path"], prefix + "\n".join(b.text for b in current), current[0].page)
            current, length = [], 0

        for b in body:
            if len(b.text) > room:              # bloc trop gros : fenêtres avec chevauchement
                flush()
                for s, e in window_spans(b.text, room, min(overlap, room - 1)):
                    part = b.text[s:e].strip()
                    if part:
                        emit(sec["path"], prefix + part, b.page)
                continue
            if current and length + 1 + len(b.text) > room:
                flush()
            current.append(b)
            length += len(b.text) + 1
        flush()
    return chunks


def chunk_document(doc: ParsedDocument, strategy: str, chunk_size: int,
                   overlap: int, contextual_header: bool = True) -> list[Chunk]:
    validate_params(strategy, chunk_size, overlap)
    fn = chunk_fixed if strategy == "fixed" else chunk_structural
    return fn(doc, chunk_size, overlap, contextual_header)
=======

import re


def fixed_size_chunking(
    pages: list[dict],
    chunk_size: int = 800,
    overlap: int = 150,
) -> list[dict]:
    """Découpe le texte en morceaux de taille fixe avec chevauchement."""
    if chunk_size <= 0:
        raise ValueError("chunk_size doit être positif.")

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap doit être >= 0 et < chunk_size.")

    chunks = []

    for page_data in pages:
        text = page_data["text"]
        start = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end].strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": (
                        f'{page_data["document_id"]}'
                        f'_p{page_data["page"]}_{start}'
                    ),
                    "text": chunk_text,
                    "metadata": dict(page_data["metadata"]),
                    "start": start,
                    "end": end,
                    "strategy": "fixed_size",
                })

            if end == len(text):
                break

            start = end - overlap

    return chunks


def structural_chunking(
    pages: list[dict],
    max_chars: int = 1200,
) -> list[dict]:
    """Découpe selon les paragraphes en préservant leur ordre."""
    if max_chars <= 0:
        raise ValueError("max_chars doit être positif.")

    chunks = []

    for page_data in pages:
        paragraphs = re.split(
            r"\n\s*\n",
            page_data["text"].strip(),
        )

        current_parts = []
        current_length = 0
        chunk_number = 0

        def save_chunk():
            nonlocal chunk_number

            if not current_parts:
                return

            chunk_text = "\n\n".join(current_parts).strip()

            if chunk_text:
                chunks.append({
                    "chunk_id": (
                        f'{page_data["document_id"]}'
                        f'_p{page_data["page"]}_s{chunk_number}'
                    ),
                    "text": chunk_text,
                    "metadata": dict(page_data["metadata"]),
                    "strategy": "structural",
                })
                chunk_number += 1

        for paragraph in paragraphs:
            paragraph = paragraph.strip()

            if not paragraph:
                continue

            # Un très long paragraphe doit lui aussi être découpé.
            if len(paragraph) > max_chars:
                save_chunk()
                current_parts.clear()
                current_length = 0

                for start in range(0, len(paragraph), max_chars):
                    part = paragraph[start:start + max_chars].strip()

                    if part:
                        chunks.append({
                            "chunk_id": (
                                f'{page_data["document_id"]}'
                                f'_p{page_data["page"]}_s{chunk_number}'
                            ),
                            "text": part,
                            "metadata": dict(page_data["metadata"]),
                            "strategy": "structural",
                        })
                        chunk_number += 1

                continue

            extra_length = len(paragraph) + (
                2 if current_parts else 0
            )

            if current_length + extra_length > max_chars:
                save_chunk()
                current_parts.clear()
                current_length = 0

            current_length += len(paragraph) + (
                2 if current_parts else 0
            )
            current_parts.append(paragraph)

        save_chunk()

    return chunks
>>>>>>> f6178066c50f1531a66589daf2331eb41ba65e30
