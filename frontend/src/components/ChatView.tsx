import { FormEvent, useEffect, useRef, useState } from "react";
import { api, describeError } from "../api/client";
import type { AskResponse, Source } from "../api/types";
import CitationText from "./CitationText";
import SourcesPanel from "./SourcesPanel";

type Message =
  | { id: number; role: "user"; text: string }
  | { id: number; role: "assistant"; response: AskResponse }
  | { id: number; role: "error"; text: string };

const SUGGESTIONS = [
  "Quelle est la durée minimale d'un PFE qui commence en février 2027 ?",
  "Que doit faire un groupe d'étudiants pour créer un club ?",
  "Dans quel délai faut-il justifier une absence ?",
];

interface Props {
  types: string[];
}

export default function ChatView({ types }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [topK, setTopK] = useState(5);
  const [type, setType] = useState("");
  const [selected, setSelected] = useState<number | null>(null); // message dont on affiche les sources
  const [activeSource, setActiveSource] = useState<number | null>(null);
  const [drawer, setDrawer] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);
  const nextId = useRef(1);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading]);

  const selectedMsg = messages.find((m) => m.id === selected);
  const sources: Source[] =
    selectedMsg && selectedMsg.role === "assistant" ? selectedMsg.response.sources : [];

  async function send(question: string) {
    const q = question.trim();
    if (!q || loading) return;
    setInput("");
    setLoading(true);
    const uid = nextId.current++;
    setMessages((m) => [...m, { id: uid, role: "user", text: q }]);
    try {
      const response = await api.ask(q, topK, { type: type || null });
      const id = nextId.current++;
      setMessages((m) => [...m, { id, role: "assistant", response }]);
      setSelected(id);
      setActiveSource(null);
    } catch (e) {
      setMessages((m) => [...m, { id: nextId.current++, role: "error", text: describeError(e) }]);
    } finally {
      setLoading(false);
    }
  }

  function onSubmit(e: FormEvent) {
    e.preventDefault();
    void send(input);
  }

  function openSource(msgId: number, sourceId: number) {
    setSelected(msgId);
    setActiveSource(sourceId);
    setDrawer(true);
  }

  return (
    <div className="chat-layout">
      <section className="chat" aria-label="Conversation">
        <div className="messages" role="log" aria-live="polite">
          {messages.length === 0 && (
            <div className="empty">
              <h2>Posez votre question sur la scolarité</h2>
              <p>
                Les réponses s'appuient uniquement sur les documents officiels de l'École et
                indiquent leurs sources.
              </p>
              <div className="suggestions">
                {SUGGESTIONS.map((s) => (
                  <button key={s} type="button" className="chip" disabled={loading} onClick={() => void send(s)}>
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m) => {
            if (m.role === "user") {
              return <div key={m.id} className="bubble user">{m.text}</div>;
            }
            if (m.role === "error") {
              return <div key={m.id} className="bubble error" role="alert">{m.text}</div>;
            }
            const r = m.response;
            const ids = new Set(r.sources.map((s) => s.id));
            return (
              <div
                key={m.id}
                className={`bubble assistant${r.found ? "" : " refusal"}${selected === m.id ? " is-selected" : ""}`}
              >
                {!r.found && <p className="refusal-label">Hors des documents de l'École</p>}
                <CitationText
                  text={r.answer}
                  validIds={ids}
                  activeId={selected === m.id ? activeSource : null}
                  onCite={(id) => openSource(m.id, id)}
                />
                {r.invalid_citations.length > 0 && (
                  <p className="warn">
                    Attention : la réponse cite {r.invalid_citations.map((n) => `[${n}]`).join(", ")},
                    qui ne correspond à aucune source fournie. Vérifiez cette information.
                  </p>
                )}
                {r.found && (
                  <div className="bubble-foot">
                    <button type="button" className="ghost" onClick={() => { setSelected(m.id); setActiveSource(null); setDrawer(true); }}>
                      {r.sources.length} sources
                    </button>
                    <span className="muted">{(r.latency_ms / 1000).toFixed(1)} s</span>
                  </div>
                )}
              </div>
            );
          })}

          {loading && (
            <div className="bubble assistant pending" aria-busy="true">
              <span className="spinner" aria-hidden /> Recherche dans les documents…
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form className="composer" onSubmit={onSubmit}>
          <div className="settings">
            <label>
              Type de document
              <select value={type} onChange={(e) => setType(e.target.value)} disabled={loading}>
                <option value="">Tous</option>
                {types.map((t) => <option key={t} value={t}>{t}</option>)}
              </select>
            </label>
            <label>
              Fragments (k)
              <input
                type="number" min={1} max={20} value={topK} disabled={loading}
                onChange={(e) => setTopK(Math.max(1, Math.min(20, Number(e.target.value) || 1)))}
              />
            </label>
          </div>
          <div className="composer-row">
            <textarea
              value={input}
              rows={2}
              placeholder="Ex. : Combien de jours avant un stage faut-il déposer la convention ?"
              aria-label="Votre question"
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); void send(input); }
              }}
            />
            <button type="submit" className="primary" disabled={loading || !input.trim()}>
              {loading ? "Envoi…" : "Envoyer"}
            </button>
          </div>
        </form>
      </section>

      <SourcesPanel
        sources={sources}
        activeId={activeSource}
        onSelect={setActiveSource}
        open={drawer}
        onClose={() => setDrawer(false)}
      />
    </div>
  );
}
