
import hashlib
import re
from pathlib import Path

import pymupdf


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
