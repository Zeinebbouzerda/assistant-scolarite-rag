import { useCallback, useEffect, useState } from "react";
import { api } from "./api/client";
import type { Health } from "./api/types";
import ChatView from "./components/ChatView";
import DocumentsView from "./components/DocumentsView";
import LandingPage from "./components/LandingPage";
import SearchDebugView from "./components/SearchDebugView";
import { useDocuments } from "./hooks/useDocuments";

type Tab = "chat" | "documents" | "search";
const TABS: { id: Tab; label: string }[] = [
  { id: "chat", label: "Conversation" },
  { id: "documents", label: "Documents" },
  { id: "search", label: "Recherche" },
];

/**
 * Composant racine de l'application Assistant Scolarité.
 * Affiche d'abord la page d'accueil de présentation puis bascule vers
 * l'espace de travail (Conversation, Documents, Recherche) au clic sur "Essayer".
 */
export default function App() {
  const [view, setView] = useState<"landing" | "app">("landing");
  const [tab, setTab] = useState<Tab>("chat");
  const [initialQuestion, setInitialQuestion] = useState<string | null>(null);
  const [health, setHealth] = useState<Health | null | "down">(null);
  const docs = useDocuments();

  const refreshHealth = useCallback(() => {
    api.health().then(setHealth).catch(() => setHealth("down"));
  }, []);

  useEffect(() => {
    refreshHealth();
  }, [refreshHealth]);

  const handleReloadDocuments = useCallback(() => {
    void docs.reload();
    refreshHealth();
  }, [docs.reload, refreshHealth]);

  const handleLaunch = useCallback(
    (options?: { tab?: Tab; question?: string }) => {
      setTab(options?.tab ?? "chat");
      setInitialQuestion(options?.question ?? null);
      setView("app");
      window.scrollTo({ top: 0, behavior: "instant" });
    },
    [],
  );

  if (view === "landing") {
    return (
      <LandingPage
        health={health}
        documents={docs.documents}
        onLaunch={handleLaunch}
      />
    );
  }

  return (
    <div className="app">
      <header className="topbar">
        <button
          type="button"
          className="brand brand-btn"
          onClick={() => setView("landing")}
          aria-label="Retour à la page d'accueil"
        >
          <img
            src="/mundiapolis-logo.png"
            alt="Université Mundiapolis"
            className="uni-logo uni-logo-sm"
            width={118}
            height={38}
          />
          <span className="brand-divider" aria-hidden />
          <div>
            <h1>Assistant scolarité</h1>
            <p>3ACINFO · Corpus EIH</p>
          </div>
        </button>
        <nav aria-label="Sections">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              className={`tab${tab === t.id ? " tab-active" : ""}`}
              aria-current={tab === t.id ? "page" : undefined}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <p className={`status-pill ${health === "down" ? "status-down" : ""}`} role="status">
          <span className="status-dot" aria-hidden />
          {health === null && "Connexion…"}
          {health === "down" && "API injoignable"}
          {health && health !== "down" && `${health.chunks} fragments indexés`}
        </p>
      </header>

      <main>
        {tab === "chat" && (
          <ChatView
            types={docs.types}
            initialQuestion={initialQuestion}
            onConsumeInitialQuestion={() => setInitialQuestion(null)}
          />
        )}
        {tab === "documents" && (
          <DocumentsView
            documents={docs.documents}
            loading={docs.loading}
            error={docs.error}
            onReload={handleReloadDocuments}
          />
        )}
        {tab === "search" && <SearchDebugView types={docs.types} />}
      </main>
    </div>
  );
}
