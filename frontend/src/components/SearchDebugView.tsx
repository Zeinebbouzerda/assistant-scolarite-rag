import { FormEvent, useState } from "react";
import { api, describeError } from "../api/client";
import type { SearchHit } from "../api/types";

export default function SearchDebugView({ types }: { types: string[] }) {
  const [question, setQuestion] = useState("");
  const [topK, setTopK] = useState(5);
  const [type, setType] = useState("");
  const [hits, setHits] = useState<SearchHit[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run(e: FormEvent) {
    e.preventDefault();
    if (!question.trim() || loading) return;
    setLoading(true);
    setError(null);
    try {
      setHits((await api.search(question.trim(), topK, { type: type || null })).results);
    } catch (err) {
      setHits(null);
      setError(describeError(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="page" aria-label="Recherche">
      <h2>Recherche brute</h2>
      <p className="muted">
        Mode débogage : affiche les fragments les plus proches et leur score, sans appeler le
        modèle de langage. Utile pour comprendre pourquoi une réponse est bonne ou mauvaise.
      </p>
      <form className="debug-form" onSubmit={run}>
        <input
          type="text" value={question} aria-label="Question"
          placeholder="Votre question" onChange={(e) => setQuestion(e.target.value)}
        />
        <label>
          Type
          <select value={type} onChange={(e) => setType(e.target.value)}>
            <option value="">Tous</option>
            {types.map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
        </label>
        <label>
          k
          <input type="number" min={1} max={50} value={topK}
            onChange={(e) => setTopK(Math.max(1, Math.min(50, Number(e.target.value) || 1)))} />
        </label>
        <button type="submit" className="primary" disabled={loading || !question.trim()}>
          {loading ? "Recherche…" : "Chercher"}
        </button>
      </form>

      {error && <p className="bubble error" role="alert">{error}</p>}
      {hits && hits.length === 0 && <p className="muted">Aucun fragment trouvé.</p>}
      <ol className="hit-list">
        {hits?.map((h) => (
          <li key={h.chunk_id} className="hit">
            <div className="hit-head">
              <span className="source-badge">{h.id}</span>
              <strong>{h.reference}</strong>
              <span className="hit-score">score {h.score.toFixed(3)}</span>
            </div>
            <p className="source-section">{h.section} — page {h.page}</p>
            <pre className="hit-text">{h.text}</pre>
            <p className="muted small">{h.chunk_id}</p>
          </li>
        ))}
      </ol>
    </section>
  );
}
