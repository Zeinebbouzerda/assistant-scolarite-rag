import type {
  AskResponse, DocumentInfo, Filters, Health, IngestParams, IngestResult, SearchResponse,
} from "./types";

// L'URL de l'API vient d'une variable d'environnement (frontend/.env).
const BASE = (import.meta.env.VITE_API_URL ?? "http://localhost:8000").replace(/\/$/, "");

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${BASE}/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...init,
    });
  } catch {
    throw new ApiError(0, "network"); // API éteinte, CORS, hors ligne...
  }
  if (!res.ok) {
    let detail = "";
    try {
      const body = await res.json();
      detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* corps non JSON */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

const post = <T,>(path: string, body: unknown) =>
  request<T>(path, { method: "POST", body: JSON.stringify(body) });

export const api = {
  health: () => request<Health>("/health"),
  documents: () => request<DocumentInfo[]>("/documents"),
  search: (question: string, top_k: number, filters: Filters) =>
    post<SearchResponse>("/search", { question, top_k, filters }),
  ask: (question: string, top_k: number, filters: Filters) =>
    post<AskResponse>("/ask", { question, top_k, filters }),
  ingest: (params: IngestParams) => post<IngestResult>("/ingest", params),
};

/** Message clair et actionnable pour chaque code d'erreur géré par l'énoncé. */
export function describeError(e: unknown): string {
  if (!(e instanceof ApiError)) return "Une erreur inattendue s'est produite.";
  switch (e.status) {
    case 0:
      return `Impossible de joindre l'API (${BASE}). Vérifiez que le serveur est démarré.`;
    case 422:
      return "La demande est invalide : saisissez une question non vide et des réglages valides.";
    case 502:
      return "Le modèle de langage ne répond pas. Réessayez dans un instant ; si cela persiste, vérifiez la clé et le quota du fournisseur.";
    case 503:
      return "La base de documents est indisponible. Vérifiez que le service est démarré et que le corpus est indexé.";
    default:
      return `Erreur ${e.status}${e.message ? ` : ${e.message}` : "."}`;
  }
}
