
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
