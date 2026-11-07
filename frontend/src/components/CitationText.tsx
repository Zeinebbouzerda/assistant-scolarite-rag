import type { ReactNode } from "react";

interface Props {
  text: string;
  validIds: Set<number>;
  activeId: number | null;
  onCite: (id: number) => void;
}

/** Affiche la réponse en transformant chaque [n] en pastille cliquable.
 *  Un numéro qui ne correspond à aucun fragment fourni reste visible mais barré. */
export default function CitationText({ text, validIds, activeId, onCite }: Props) {
  const parts: ReactNode[] = [];
  const re = /\[([\d\s,;]+)\]/g;
  let last = 0;
  let m: RegExpExecArray | null;
  while ((m = re.exec(text)) !== null) {
    if (m.index > last) parts.push(text.slice(last, m.index));
    for (const raw of m[1].match(/\d+/g) ?? []) {
      const id = Number(raw);
      const ok = validIds.has(id);
      parts.push(
        <button
          key={`${m.index}-${raw}`}
          type="button"
          className={`cite${ok ? "" : " cite-invalid"}${activeId === id ? " cite-active" : ""}`}
          disabled={!ok}
          aria-label={ok ? `Voir la source ${id}` : `Citation ${id} invalide`}
          onClick={() => onCite(id)}
        >
          {id}
        </button>,
      );
    }
    last = m.index + m[0].length;
  }
  if (last < text.length) parts.push(text.slice(last));
  return <p className="answer-text">{parts}</p>;
}
