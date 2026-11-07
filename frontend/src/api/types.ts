// Types alignés sur les modèles Pydantic du backend (backend/app/models.py).

export interface Filters {
  type?: string | null;
  reference?: string | null;
}

export interface Source {
  id: number; // numéro de citation : [1], [2]...
  chunk_id: string;
  file: string;
  reference: string;
  date: string | null;
  page: number;
  section: string;
  excerpt: string;
  score: number;
}

export interface AskResponse {
  answer: string;
  found: boolean;
  sources: Source[];
  invalid_citations: number[];
  latency_ms: number;
}

export interface SearchHit {
  id: number;
  chunk_id: string;
  file: string;
  reference: string;
  type: string;
  date: string | null;
  page: number;
  section: string;
  text: string;
  score: number;
}

export interface SearchResponse {
  question: string;
  results: SearchHit[];
}

export interface DocumentInfo {
  file: string;
  reference: string;
  title: string;
  type: string;
  date: string | null;
  version: string;
  status: string;
  pages: number;
  chunks: number;
  modifies: string[];
  modified_by: string[];
}

export interface Health {
  status: string;
  chunks: number;
  embedding_model: string;
  llm_provider: string;
  similarity_threshold: number;
}

export interface IngestParams {
  strategy: "fixed" | "structural";
  chunk_size?: number;
  chunk_overlap?: number;
}

export interface IngestResult {
  documents: number;
  chunks: number;
  strategy: string;
  chunk_size: number;
  chunk_overlap: number;
  duration_ms: number;
}
