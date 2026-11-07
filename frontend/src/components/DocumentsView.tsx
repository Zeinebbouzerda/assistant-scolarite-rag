import { FormEvent, useState } from "react";
import { api, describeError } from "../api/client";
import type { DocumentInfo, IngestResult } from "../api/types";

interface Props {
  documents: DocumentInfo[];
  loading: boolean;
  error: string | null;
  onReload: () => void;
}

export default function DocumentsView({ documents, loading, error, onReload }: Props) {
  const [strategy, setStrategy] = useState<"structural" | "fixed">("structural");
  const [size, setSize] = useState("");
  const [overlap, setOverlap] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<IngestResult | null>(null);
  const [ingestError, setIngestError] = useState<string | null>(null);

  async function ingest(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setIngestError(null);
    setResult(null);
    try {
      setResult(await api.ingest({
        strategy,
        chunk_size: size ? Number(size) : undefined,
        chunk_overlap: overlap ? Number(overlap) : undefined,
      }));
      onReload();
    } catch (err) {
      setIngestError(describeError(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section className="page" aria-label="Documents">
      <h2>Documents indexés</h2>
      {loading && <p className="muted"><span className="spinner" aria-hidden /> Chargement…</p>}
      {error && <p className="bubble error" role="alert">{error}</p>}
      {!loading && !error && documents.length === 0 && (
        <p className="muted">Aucun document indexé. Lancez l'indexation ci-dessous.</p>
      )}

      <ul className="doc-list">
        {documents.map((d) => (
          <li key={d.file} className="doc">
            <div className="doc-head">
              <h3>{d.title}</h3>
              <span className="doc-ref">{d.reference}</span>
            </div>
            <dl className="doc-meta">
              <div><dt>Type</dt><dd>{d.type}</dd></div>
              <div><dt>Publié le</dt><dd>{d.date ?? "—"}</dd></div>
              <div><dt>Version</dt><dd>{d.version || "—"}</dd></div>
              <div><dt>Pages</dt><dd>{d.pages}</dd></div>
              <div><dt>Fragments</dt><dd>{d.chunks}</dd></div>
            </dl>
            <p className="doc-status">{d.status}</p>
            {d.modifies.length > 0 && (
              <p className="tag tag-new">Texte modificatif : modifie {d.modifies.join(", ")}</p>
            )}
            {d.modified_by.length > 0 && (
              <p className="tag tag-old">Modifié par {d.modified_by.join(", ")}</p>
            )}
          </li>
        ))}
      </ul>

      <form className="ingest" onSubmit={ingest}>
        <h3>Indexer le corpus</h3>
        <p className="muted">Relancer l'indexation remplace les fragments existants, sans doublon.</p>
        <div className="ingest-fields">
          <label>
            Découpage
            <select value={strategy} onChange={(e) => setStrategy(e.target.value as "fixed" | "structural")}>
              <option value="structural">Structurel (par article / question)</option>
              <option value="fixed">Taille fixe</option>
            </select>
          </label>
          <label>
            Taille (caractères)
            <input type="number" min={50} placeholder="défaut" value={size} onChange={(e) => setSize(e.target.value)} />
          </label>
          <label>
            Chevauchement
            <input type="number" min={0} placeholder="défaut" value={overlap} onChange={(e) => setOverlap(e.target.value)} />
          </label>
          <button type="submit" className="primary" disabled={busy}>
            {busy ? "Indexation…" : "Lancer l'indexation"}
          </button>
        </div>
        {busy && <p className="muted"><span className="spinner" aria-hidden /> Calcul des embeddings, cela peut prendre une minute.</p>}
        {ingestError && <p className="bubble error" role="alert">{ingestError}</p>}
        {result && (
          <p className="ok" role="status">
            {result.documents} documents et {result.chunks} fragments indexés
            (découpage {result.strategy}, taille {result.chunk_size}, chevauchement {result.chunk_overlap}).
          </p>
        )}
      </form>
    </section>
  );
}
