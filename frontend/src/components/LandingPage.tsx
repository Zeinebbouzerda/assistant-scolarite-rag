import { useEffect, useState } from "react";
import type { DocumentInfo, Health } from "../api/types";

interface Props {
  /** État courant de l'API (null = chargement, "down" = hors ligne). */
  health: Health | null | "down";
  /** Documents indexés récupérés depuis GET /api/documents (peut être vide hors ligne). */
  documents: DocumentInfo[];
  /** Ouvre l'application principale (onglet Conversation par défaut, ou Documents). */
  onLaunch: (options?: { tab?: "chat" | "documents" | "search"; question?: string }) => void;
}

interface DemoScenario {
  id: string;
  label: string;
  question: string;
  answerParts: { text: string; cite?: number }[];
  refusal?: boolean;
  source: {
    id: number;
    reference: string;
    section: string;
    page: number;
    date: string;
    score: number;
    badge?: string;
    excerpt: string;
  };
}

/**
 * Trois scénarios réels issus du corpus EIH illustrant les forces du pipeline RAG :
 * résolution de conflit entre versions, citation précise et refus contrôlé hors corpus.
 */
const DEMO_SCENARIOS: DemoScenario[] = [
  {
    id: "pfe",
    label: "Conflit de version",
    question: "Quelle est la durée minimale d'un PFE qui commence en février 2027 ?",
    answerParts: [
      {
        text: "Depuis la note de service du 5 octobre 2026, la durée minimale d'un PFE débutant à compter du 1er janvier 2027 est portée à 18 semaines ",
        cite: 1,
      },
      {
        text: "(elle était précédemment de 16 semaines dans le guide des stages ",
        cite: 2,
      },
      { text: ")." },
    ],
    source: {
      id: 1,
      reference: "EIH-DE-NS-2026-14",
      section: "Article 1 — Modification de la durée minimale du PFE",
      page: 1,
      date: "5 octobre 2026",
      score: 0.89,
      badge: "Modifie EIH-SRE-GUIDE-2026",
      excerpt:
        "Pour tout Projet de Fin d'Études débutant à compter du 1er janvier 2027, la durée minimale obligatoire est portée de 16 à 18 semaines à temps plein.",
    },
  },
  {
    id: "absence",
    label: "Citation exacte",
    question: "Dans quel délai faut-il justifier une absence ?",
    answerParts: [
      {
        text: "Tout justificatif d'absence (certificat médical ou convocation officielle) doit être déposé auprès du service de la scolarité dans un délai maximal de 48 heures ouvrées suivant la reprise ",
        cite: 1,
      },
      { text: "." },
    ],
    source: {
      id: 1,
      reference: "EIH-DE-REG-2026",
      section: "Titre II > Article 6 — Assiduité et absences",
      page: 4,
      date: "10 juillet 2026",
      score: 0.86,
      excerpt:
        "L'étudiant dispose de 48 heures ouvrées à compter de son retour pour transmettre un justificatif recevable au bureau de la scolarité.",
    },
  },
  {
    id: "refusal",
    label: "Refus sans hallucination",
    question: "Quel est le prix d'un repas à la cafétéria du campus ?",
    refusal: true,
    answerParts: [
      {
        text: "Je ne trouve pas cette information dans les documents de l'École.",
      },
    ],
    source: {
      id: 0,
      reference: "Seuil de similarité",
      section: "Meilleur fragment : 0.18 < 0.35",
      page: 0,
      date: "Aucun appel LLM",
      score: 0.18,
      excerpt:
        "Lorsque le score cosinus du meilleur fragment reste sous le seuil configuré, l'API refuse immédiatement la question sans solliciter le modèle de langage.",
    },
  },
];

/** Liste de secours des 7 documents officiels lorsque l'API n'est pas encore démarrée. */
const CORPUS_FALLBACK = [
  { reference: "EIH-DE-REG-2026", title: "Règlement des études 2026-2027", type: "Règlement officiel" },
  { reference: "EIH-SRE-GUIDE-2026", title: "Guide des stages et PFE 2026", type: "Guide pratique" },
  { reference: "EIH-BRI-CHARTE-2026", title: "Charte de mobilité internationale", type: "Charte et procédure" },
  { reference: "EIH-DE-CAL-2026", title: "Calendrier académique 2026-2027", type: "Calendrier officiel" },
  { reference: "EIH-BVE-GUIDE-2026", title: "Guide de la vie étudiante", type: "Guide d'information" },
  { reference: "EIH-SCOL-FAQ-2026", title: "FAQ Scolarité", type: "FAQ (questions-réponses)" },
  { reference: "EIH-DE-NS-2026-14", title: "Note de service 2026-14 (durée PFE)", type: "Texte modificatif" },
];

/**
 * Page d'accueil éditoriale inspirée d'une mise en page studio claire :
 * présentation du projet RAG, aperçu interactif animé dans le hero,
 * architecture du pipeline et accès direct à l'assistant.
 */
export default function LandingPage({ health, documents, onLaunch }: Props) {
  const [scenarioIdx, setScenarioIdx] = useState(0);
  const [paused, setPaused] = useState(false);

  // Rotation douce entre les trois scénarios du hero, mise en pause dès que l'utilisateur interagit.
  useEffect(() => {
    if (paused) return;
    const timer = window.setInterval(() => {
      setScenarioIdx((i) => (i + 1) % DEMO_SCENARIOS.length);
    }, 6500);
    return () => window.clearInterval(timer);
  }, [paused]);

  const scenario = DEMO_SCENARIOS[scenarioIdx];
  const corpusItems =
    documents.length > 0
      ? documents.map((d) => ({
          reference: d.reference,
          title: d.title,
          type: d.type,
          chunks: d.chunks,
          modifies: d.modifies,
        }))
      : CORPUS_FALLBACK.map((d) => ({ ...d, chunks: null as number | null, modifies: [] as string[] }));

  return (
    <div className="landing">
      <header className="landing-nav">
        <div className="landing-nav-inner">
          <div className="brand">
            <span className="brand-mark" aria-hidden>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M12 3v18" />
                <path d="M5 8c2.5 0 4.5 2 7 4 2.5-2 4.5-4 7-4" />
                <path d="M5 16c2.5 0 4.5-2 7-4 2.5 2 4.5 4 7 4" />
              </svg>
            </span>
            <div>
              <span className="brand-title">Assistant scolarité</span>
              <span className="brand-sub">École d'Ingénieurs Hélianthe</span>
            </div>
          </div>

          <nav className="landing-links" aria-label="Navigation principale">
            <a href="#fonctionnement">Fonctionnement</a>
            <a href="#corpus">Corpus officiel</a>
          </nav>

          <div className="landing-nav-actions">
            <span className={`status-pill ${health === "down" ? "status-down" : ""}`} role="status">
              <span className="status-dot" aria-hidden />
              {health === null && "Connexion…"}
              {health === "down" && "API hors ligne"}
              {health && health !== "down" && `${health.chunks} fragments`}
            </span>
            <button type="button" className="btn-primary" onClick={() => onLaunch()}>
              Essayer
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          </div>
        </div>
      </header>

      <main className="landing-main">
        {/* Section Hero : message clair + CTA dominant + aperçu produit interactif */}
        <section className="hero" aria-labelledby="hero-title">
          <div className="hero-copy">
            <h1 id="hero-title">
              Toutes les règles de l'École, sourcées à la page près.
            </h1>
            <p className="hero-lead">
              Posez vos questions sur les stages, absences, examens ou la mobilité. L'assistant
              répond uniquement à partir des 7 documents officiels de l'EIH, cite chaque extrait
              et applique toujours la version la plus récente.
            </p>
            <div className="hero-cta">
              <button type="button" className="btn-primary btn-lg" onClick={() => onLaunch()}>
                Essayer l'assistant
                <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                  <path d="M5 12h14" />
                  <path d="m12 5 7 7-7 7" />
                </svg>
              </button>
              <button
                type="button"
                className="btn-secondary btn-lg"
                onClick={() => onLaunch({ tab: "documents" })}
              >
                Parcourir les documents
              </button>
            </div>
          </div>

          {/* Cadre produit animé : démonstration réelle du pipeline RAG */}
          <div
            className="hero-stage"
            onMouseEnter={() => setPaused(true)}
            onMouseLeave={() => setPaused(false)}
          >
            <div className="stage-bar">
              <div className="stage-tabs" role="tablist" aria-label="Exemples de requêtes">
                {DEMO_SCENARIOS.map((sc, i) => (
                  <button
                    key={sc.id}
                    type="button"
                    role="tab"
                    aria-selected={i === scenarioIdx}
                    className={`stage-tab${i === scenarioIdx ? " is-active" : ""}`}
                    onClick={() => {
                      setScenarioIdx(i);
                      setPaused(true);
                    }}
                  >
                    {sc.label}
                  </button>
                ))}
              </div>
              <button
                type="button"
                className="stage-try-link"
                onClick={() => onLaunch({ tab: "chat", question: scenario.question })}
              >
                Tester cette question
              </button>
            </div>

            <div className="stage-body" key={scenario.id}>
              <div className="stage-conversation">
                <div className="stage-user-msg">{scenario.question}</div>

                <div className={`stage-assistant-msg${scenario.refusal ? " is-refusal" : ""}`}>
                  {scenario.refusal && (
                    <p className="refusal-label">Hors des documents de l'École</p>
                  )}
                  <p className="stage-answer">
                    {scenario.answerParts.map((part, idx) => (
                      <span key={idx}>
                        {part.text}
                        {part.cite !== undefined && (
                          <span className="cite cite-static" aria-hidden>
                            {part.cite}
                          </span>
                        )}
                      </span>
                    ))}
                  </p>
                </div>
              </div>

              <aside className="stage-source" aria-label="Extrait source vérifié">
                <div className="stage-source-head">
                  <span className="source-badge">{scenario.source.id || "—"}</span>
                  <div className="stage-source-titles">
                    <strong>{scenario.source.reference}</strong>
                    <span>{scenario.source.section}</span>
                  </div>
                </div>
                <div className="stage-source-meta">
                  <span>{scenario.source.date}</span>
                  {scenario.source.page > 0 && <span>Page {scenario.source.page}</span>}
                  <span className="tabular">Score {scenario.source.score.toFixed(2)}</span>
                </div>
                {scenario.source.badge && (
                  <p className="stage-source-note">{scenario.source.badge}</p>
                )}
                <blockquote className="stage-excerpt">{scenario.source.excerpt}</blockquote>
              </aside>
            </div>
          </div>
        </section>

        {/* Architecture & garanties : mise en page asymétrique sans grille uniforme de cartes */}
        <section id="fonctionnement" className="landing-section">
          <div className="section-head">
            <h2>Conçu pour des réponses fiables, pas pour improviser</h2>
            <p className="section-sub">
              Chaque question suit un pipeline transparent : recherche vectorielle multilingue,
              contrôle de pertinence, détection des textes modificatifs et vérification formelle des citations.
            </p>
          </div>

          <div className="arch-grid">
            <div className="arch-primary">
              <h3>Pipeline RAG en quatre étapes</h3>
              <ol className="pipeline-steps">
                <li>
                  <span className="step-index tabular">1</span>
                  <div>
                    <strong>Extraction structurelle des PDF</strong>
                    <p>
                      PyMuPDF conserve la hiérarchie des titres, relie chaque ligne de tableau à
                      ses colonnes et lit automatiquement la fiche signalétique en page 1.
                    </p>
                  </div>
                </li>
                <li>
                  <span className="step-index tabular">2</span>
                  <div>
                    <strong>Découpage et indexation ChromaDB</strong>
                    <p>
                      Découpage structurel par article ou question de FAQ (ou fenêtre fixe),
                      encodé avec MiniLM multilingue et remplacé de façon idempotente.
                    </p>
                  </div>
                </li>
                <li>
                  <span className="step-index tabular">3</span>
                  <div>
                    <strong>Extension par documents modificatifs</strong>
                    <p>
                      Lorsqu'un extrait provient d'un document modifié par une note de service plus
                      récente, les passages du texte modificatif sont ajoutés automatiquement au contexte.
                    </p>
                  </div>
                </li>
                <li>
                  <span className="step-index tabular">4</span>
                  <div>
                    <strong>Génération citée et vérifiée</strong>
                    <p>
                      Chaque affirmation renvoie vers ses fragments [1], [2] ; tout numéro hors
                      contexte est détecté côté serveur et signalé dans l'interface.
                    </p>
                  </div>
                </li>
              </ol>
            </div>

            <div className="arch-secondary">
              <h3>Deux garde-fous côté code</h3>
              <dl className="guardrails">
                <div>
                  <dt>Seuil de similarité cosinus</dt>
                  <dd>
                    Si le meilleur fragment passe sous le seuil configuré (0.35 par défaut),
                    l'API refuse immédiatement la question sans même appeler le LLM.
                  </dd>
                </div>
                <div>
                  <dt>Contrôle des citations et précédence</dt>
                  <dd>
                    Les références citées sont vérifiées contre les passages réellement fournis,
                    et les liens modifie / modifié par priment sur l'ancien règlement.
                  </dd>
                </div>
                <div>
                  <dt>Mode débogage intégré</dt>
                  <dd>
                    L'onglet Recherche affiche les scores cosinus bruts sans LLM pour évaluer
                    et calibrer facilement le découpage.
                  </dd>
                </div>
              </dl>
            </div>
          </div>
        </section>

        {/* Aperçu du corpus officiel indexé */}
        <section id="corpus" className="landing-section">
          <div className="section-head">
            <h2>Le corpus officiel de l'EIH</h2>
            <p className="section-sub">
              Sept documents réglementaires et pratiques indexés localement. Aucune connaissance
              extérieure n'est autorisée dans les réponses.
            </p>
          </div>

          <ul className="corpus-list">
            {corpusItems.map((doc) => (
              <li key={doc.reference} className="corpus-row">
                <div className="corpus-row-main">
                  <strong>{doc.title}</strong>
                  <span className="corpus-ref">{doc.reference}</span>
                </div>
                <div className="corpus-row-meta">
                  <span>{doc.type}</span>
                  {doc.chunks !== null && (
                    <span className="tabular">{doc.chunks} fragments</span>
                  )}
                </div>
              </li>
            ))}
          </ul>

          <div className="closing-cta">
            <div>
              <h3>Prêt à tester l'assistant sur vos questions ?</h3>
              <p>Posez une question, inspectez les sources ou comparez les stratégies de découpage.</p>
            </div>
            <button type="button" className="btn-primary btn-lg" onClick={() => onLaunch()}>
              Ouvrir l'assistant
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
                <path d="M5 12h14" />
                <path d="m12 5 7 7-7 7" />
              </svg>
            </button>
          </div>
        </section>
      </main>
    </div>
  );
}
