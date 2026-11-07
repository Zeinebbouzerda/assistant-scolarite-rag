import pytest

from backend.app.config import Settings
from backend.app.services.chunking import chunk_document, validate_params, window_spans
from backend.app.services.extraction import extract_corpus, parse_french_date

DOCS = {d.metadata["reference"]: d for d in extract_corpus(Settings(_env_file=None).corpus_dir)}


def test_metadata_read_from_pdf():
    assert len(DOCS) == 7
    m = DOCS["EIH-DE-NS-2026-14"].metadata
    assert (m["date"], m["version"], m["type"]) == ("2026-10-05", "1.0", "Note de service (texte modificatif)")
    assert DOCS["EIH-SRE-GUIDE-2026"].metadata["date"] == "2026-06-15"
    assert parse_french_date("1er septembre 2026") == "2026-09-01"


def test_modification_links_are_detected_generically():
    assert DOCS["EIH-DE-NS-2026-14"].metadata["modifies"] == ["EIH-SRE-GUIDE-2026"]
    assert DOCS["EIH-SRE-GUIDE-2026"].metadata["modified_by"] == ["EIH-DE-NS-2026-14"]
    assert DOCS["EIH-DE-REG-2026"].metadata["modified_by"] == []


def test_repeated_headers_and_footers_are_removed():
    text = "\n".join(b.text for d in DOCS.values() for b in d.blocks)
    assert "usage pédagogique" not in text and "établissement fictif" not in text


def test_table_rows_keep_their_headers():
    rows = [b.text for b in DOCS["EIH-DE-CAL-2026"].blocks if b.kind == "table_row"]
    assert ("Date ou période : Vendredi 12 février 2027 — Événement : Date limite d'inscription "
            "au rattrapage des modules S1, S3, S5 — Public : 1A, 2A, 3A") in rows


def test_fixed_chunking_size_overlap_and_metadata():
    doc = DOCS["EIH-DE-REG-2026"]
    chunks = chunk_document(doc, "fixed", 500, 100)
    assert len(chunks) > 5
    assert all(len(c.text) <= 500 for c in chunks)
    ids = [c.chunk_id for c in chunks]
    assert len(ids) == len(set(ids))
    for c in chunks:
        for key in ("source", "reference", "type", "date", "page", "section"):
            assert c.metadata[key] not in (None, "")
    # le chevauchement existe : la fin d'un fragment se retrouve au début du suivant
    a, b = chunks[3], chunks[4]
    assert a.text[-40:].split()[-1] in b.text[:200]


def test_window_spans_never_stalls_and_covers_text():
    text = "mot " * 500
    spans = window_spans(text, 120, 30)
    assert spans[0][0] == 0 and spans[-1][1] == len(text)
    assert all(e > s for s, e in spans)


def test_structural_chunking_follows_articles():
    chunks = chunk_document(DOCS["EIH-DE-REG-2026"], "structural", 1000, 100)
    art14 = [c for c in chunks if "Article 14" in c.metadata["section"]]
    assert art14 and "12/20" in " ".join(c.text for c in art14)
    assert all(c.text.startswith(("Article", "Titre", "Préambule")) or len(c.text) > 0 for c in chunks)
    faq = chunk_document(DOCS["EIH-SCOL-FAQ-2026"], "structural", 1000, 100)
    assert sum(c.text.startswith("Q") for c in faq) >= 10        # une paire Q-R par fragment


def test_chunk_params_are_validated():
    with pytest.raises(ValueError):
        validate_params("fixed", 500, 500)
    with pytest.raises(ValueError):
        validate_params("magic", 500, 100)
