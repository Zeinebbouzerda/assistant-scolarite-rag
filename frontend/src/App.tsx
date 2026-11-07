import { useEffect, useState } from "react";
import { api } from "./api/client";
import type { Health } from "./api/types";
import ChatView from "./components/ChatView";
import DocumentsView from "./components/DocumentsView";
import SearchDebugView from "./components/SearchDebugView";
import { useDocuments } from "./hooks/useDocuments";

type Tab = "chat" | "documents" | "search";
const TABS: { id: Tab; label: string }[] = [
  { id: "chat", label: "Conversation" },
  { id: "documents", label: "Documents" },
  { id: "search", label: "Recherche" },
];

export default function App() {
  const [tab, setTab] = useState<Tab>("chat");
  const [health, setHealth] = useState<Health | null | "down">(null);
  const docs = useDocuments();

  useEffect(() => {
    api.health().then(setHealth).catch(() => setHealth("down"));
  }, [docs.documents.length]);

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark" aria-hidden />
          <div>
            <h1>Assistant scolarité</h1>
            <p>École d'Ingénieurs Hélianthe</p>
          </div>
        </div>
        <nav aria-label="Sections">
          {TABS.map((t) => (
            <button
              key={t.id} type="button"
              className={`tab${tab === t.id ? " tab-active" : ""}`}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <p className={`status ${health === "down" ? "status-down" : ""}`} role="status">
          {health === null && "Connexion…"}
          {health === "down" && "API injoignable"}
          {health && health !== "down" && `${health.chunks} fragments indexés`}
        </p>
      </header>

      <main>
        {tab === "chat" && <ChatView types={docs.types} />}
        {tab === "documents" && (
          <DocumentsView documents={docs.documents} loading={docs.loading} error={docs.error} onReload={docs.reload} />
        )}
        {tab === "search" && <SearchDebugView types={docs.types} />}
      </main>
    </div>
  );
}
