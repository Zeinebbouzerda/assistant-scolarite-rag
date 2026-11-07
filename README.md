# Assistant Scolarité — RAG pour l'École d'Ingénieurs Hélianthe (EIH)

Application web qui répond aux questions des étudiants **uniquement à partir des 7 documents officiels de l'École**, cite ses sources `[1]`, `[2]` et répond
« *Je ne trouve pas cette information dans les documents de l'École.* » quand la réponse n'est pas dans le corpus.
Quand deux documents se contredisent, le plus récent qui **se déclare modificatif** l'emporte, et la réponse le signale.

Projet du module RAG (3ACINFO, Université Mundiapolis) — binôme : *[vos deux noms]*.

## Architecture

```
INGESTION (une fois)   PDF ─► extraction ─► découpage ─► embeddings ─► ChromaDB (disque)
                            PyMuPDF        fixe | structurel  MiniLM multilingue

QUESTION (à chaque requête)
 React ─► POST /api/ask ─► recherche top-k ─► seuil de score ─► + documents modificatifs
                                  │                │ sous le seuil : refus SANS appeler le LLM
                                  ▼                ▼
                        prompt (fragments numérotés + référence + date + statut) ─► Gemini
                                  ▼
                 vérification des citations ─► { answer, found, sources, invalid_citations }
```

```
assistant-scolarite-rag/
├── backend/app/
│   ├── main.py, api.py, models.py, config.py, errors.py     # FastAPI, routes, schémas Pydantic
│   └── services/
│       ├── extraction.py   # PDF -> blocs (métadonnées, titres, tableaux, en-têtes/pieds supprimés)
│       ├── chunking.py     # stratégies "fixed" et "structural"
│       ├── embeddings.py   # sentence-transformers (+ variante "hash" pour les tests)
│       ├── vector_store.py # ChromaDB, cosinus, remplacement par fichier (idempotent)
│       ├── retrieval.py    # top-k + ajout des documents modificatifs
│       ├── prompts.py      # prompt système et mise en forme du contexte
│       ├── generation.py   # pipeline RAG, seuil, vérification des citations
│       ├── llm.py          # Gemini / Ollama / faux LLM de test
│       └── ingestion.py    # chaîne d'ingestion
├── backend/tests/          # 21 tests pytest (sans réseau ni clé API)
├── frontend/               # React + TypeScript + Vite
├── eval/                   # questions.jsonl (21 questions) + run_eval.py
├── data/corpus/            # les 7 PDF (non modifiés)
├── data/processed/         # JSON de la séance 1
├── scripts/                # utilitaires de diagnostic
├── docs/                   # changements, plan de travail, trame du rapport, soutenance, déclaration IA
├── ingest_corpus.py, export_chunks_json.py
└── .env.example
```

## Installation (Windows PowerShell ; sous Linux/macOS remplacez l'activation par `source .venv/bin/activate`)

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
copy .env.example .env          # puis renseignez GEMINI_API_KEY dans .env
```

Python 3.11 ou plus. Le fichier `.env` n'est **jamais** versionné (voir `.gitignore`) ; le navigateur ne voit jamais la clé.

### Variables d'environnement (backend, fichier `.env` à la racine)

| Variable | Rôle | Défaut |
|---|---|---|
| `LLM_PROVIDER` | `gemini`, `ollama` ou `fake` (tests) | `gemini` |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | accès Gemini | — / `gemini-2.5-flash` |
| `OLLAMA_URL`, `OLLAMA_MODEL` | alternative locale | `http://localhost:11434` / `mistral` |
| `SIMILARITY_THRESHOLD` | score minimal du meilleur fragment, sinon refus sans LLM | `0.35` (**à calibrer**) |
| `EMBEDDING_MODEL` | modèle d'embeddings multilingue | `paraphrase-multilingual-MiniLM-L12-v2` |
| `EMBEDDING_MAX_SEQ_LENGTH` | tokens encodés par fragment | `384` |
| `CORS_ORIGINS` | origines autorisées | `http://localhost:5173` |

Frontend : `frontend/.env` contient `VITE_API_URL=http://localhost:8000` (copiez `frontend/.env.example`).

## Lancement

```powershell
# 1. Indexer le corpus (télécharge le modèle d'embeddings la première fois, ~470 Mo)
python ingest_corpus.py --strategy structural        # ou via POST /api/ingest dans http://localhost:8000/docs

# 2. API  ->  http://localhost:8000/docs
uvicorn backend.app.main:app --reload

# 3. Interface  ->  http://localhost:5173
cd frontend
copy .env.example .env
npm install
npm run dev
```

## API (préfixe `/api`, documentation interactive sur `/docs`)

| Route | Rôle | Erreurs |
|---|---|---|
| `GET /api/health` | état et nombre de fragments | 503 si la base est indisponible |
| `POST /api/ingest` | (ré)indexation : `strategy`, `chunk_size`, `chunk_overlap` | 422 si invalides |
| `GET /api/documents` | documents indexés + métadonnées + liens de modification | |
| `POST /api/search` | recherche seule, fragments et scores | 422 si question vide |
| `POST /api/ask` | recherche puis génération | 422 ; 502 si le LLM ne répond pas |

## Tests et évaluation

```powershell
pytest                                                # 21 tests, ~1 min, sans réseau
python eval/run_eval.py --check-gold                  # vérifie le jeu de test contre le corpus
python eval/run_eval.py --configs fixed:500:100:3 fixed:500:100:8 structural:1000:100:3 structural:1000:100:8 --sweep
python eval/run_eval.py --configs fixed:500:100:5 structural:1000:100:5 --generate
```

Détails des métriques et de la lecture des résultats : `docs/PLAN_TRAVAIL.md`.

## Choix techniques (et pourquoi)

- **PyMuPDF** : donne la police et la taille de chaque ligne, donc des titres détectés *sans règle propre à ce corpus*. Ses tableaux perdent les espaces dans les cellules ; on n'utilise que leur géométrie et on relit chaque cellule avec `get_text(clip=…)`.
- **Découpage structurel** : un fragment par article / section / paire Q-R, avec le chemin hiérarchique (« Titre III > Article 6 ») ; une ligne de tableau n'est jamais coupée et garde ses en-têtes.
- **Versions** : le champ *Statut* de la fiche d'un document est lu ; s'il parle de modification et cite une autre référence, le lien `modifie / modifié par` est créé automatiquement. Les fragments du document modificatif sont ajoutés au contexte, et chaque fragment est présenté au LLM avec sa référence, sa date et ces liens.
- **Ingestion idempotente** : les fragments de chaque fichier sont *remplacés*, jamais ajoutés ; changer de stratégie ne laisse pas de doublons.
- **Deux garde-fous côté code** : seuil de score (refus sans appel LLM) et vérification que chaque `[n]` cité correspond à un fragment fourni.

## Limites connues

Pas de mémoire de conversation (chaque question est indépendante) ; le seuil de score dépend du modèle d'embeddings ; le LLM peut mal appliquer une règle de précédence malgré le prompt ; les citations sont vérifiées *formellement* (le numéro existe), pas *sémantiquement*.
