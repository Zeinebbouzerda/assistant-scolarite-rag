import { useEffect, useRef } from "react";
import type { Source } from "../api/types";

interface Props {
  sources: Source[];
  activeId: number | null;
  onSelect: (id: number) => void;
  open: boolean; // tiroir sur mobile
  onClose: () => void;
}

function formatDate(iso: string | null) {
  if (!iso) return "date inconnue";
  return new Date(iso + "T00:00:00").toLocaleDateString("fr-FR", {
    day: "numeric", month: "long", year: "numeric",
  });
}

export default function SourcesPanel({ sources, activeId, onSelect, open, onClose }: Props) {
  const refs = useRef<Record<number, HTMLLIElement | null>>({});

  useEffect(() => {
    if (activeId !== null) {
      refs.current[activeId]?.scrollIntoView({ block: "nearest", behavior: "smooth" });
    }
  }, [activeId]);

  return (
    <aside className={`sources${open ? " sources-open" : ""}`} aria-label="Sources de la réponse">
      <div className="sources-head">
        <h2>Sources</h2>
        <button type="button" className="ghost sources-close" onClick={onClose}>
          Fermer
        </button>
      </div>
      {sources.length === 0 ? (
        <p className="muted">
          Les documents utilisés pour une réponse apparaissent ici. Cliquez sur une pastille
          jaune dans la réponse pour afficher la source correspondante.
        </p>
      ) : (
        <ul className="source-list">
          {sources.map((s) => (
            <li
              key={s.chunk_id}
              ref={(el) => { refs.current[s.id] = el; }}
              className={`source${activeId === s.id ? " source-active" : ""}`}
            >
              <button type="button" className="source-main" onClick={() => onSelect(s.id)}>
                <span className="source-badge">{s.id}</span>
                <span className="source-title">
                  <strong>{s.reference}</strong>
                  <span className="source-section">{s.section}</span>
                </span>
              </button>
              <dl className="source-meta">
                <div><dt>Document</dt><dd>{s.file}</dd></div>
                <div><dt>Page</dt><dd>{s.page}</dd></div>
                <div><dt>Publié le</dt><dd>{formatDate(s.date)}</dd></div>
                <div>
                  <dt>Pertinence</dt>
                  <dd>
                    <span className="score-bar" aria-hidden>
                      <span style={{ width: `${Math.max(0, Math.min(1, s.score)) * 100}%` }} />
                    </span>
                    {s.score.toFixed(2)}
                  </dd>
                </div>
              </dl>
              <blockquote className="excerpt">{s.excerpt}</blockquote>
            </li>
          ))}
        </ul>
      )}
    </aside>
  );
}
