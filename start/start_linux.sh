#!/usr/bin/env bash
# Script de lancement complet (Backend FastAPI + Frontend Vite) pour Linux / macOS.
# Usage : ./start/start_linux.sh

set -euo pipefail

# Résout la racine du projet quel que soit le répertoire courant
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$ROOT_DIR"

# 1. Vérification de l'environnement virtuel Python
if [ ! -x "$ROOT_DIR/.venv/bin/uvicorn" ]; then
  echo "[ERREUR] Environnement virtuel .venv introuvable ou incomplet."
  echo "Exécutez d'abord :"
  echo "  python3 -m venv .venv"
  echo "  source .venv/bin/activate"
  echo "  pip install -r backend/requirements.txt"
  exit 1
fi

# 2. Vérification des fichiers .env
if [ ! -f "$ROOT_DIR/.env" ]; then
  cp "$ROOT_DIR/.env.example" "$ROOT_DIR/.env"
  echo "[INFO] Fichier .env créé depuis .env.example."
  echo "[ATTENTION] Renseignez GEMINI_API_KEY (et GEMINI_MODEL) dans .env avant de poser des questions."
fi

if [ ! -f "$ROOT_DIR/frontend/.env" ]; then
  cp "$ROOT_DIR/frontend/.env.example" "$ROOT_DIR/frontend/.env"
  echo "[INFO] Fichier frontend/.env créé depuis frontend/.env.example."
fi

# 3. Installation des dépendances frontend si nécessaire
if [ ! -d "$ROOT_DIR/frontend/node_modules" ]; then
  echo "[INFO] Installation des dépendances frontend (npm install)..."
  (cd "$ROOT_DIR/frontend" && npm install)
fi

# 4. Indexation initiale du corpus si la base ChromaDB n'existe pas encore
if [ ! -d "$ROOT_DIR/storage/chroma" ]; then
  echo "[INFO] Base vectorielle absente : indexation initiale du corpus..."
  "$ROOT_DIR/.venv/bin/python" "$ROOT_DIR/ingest_corpus.py" --strategy structural
fi

# 5. Lancement du backend en arrière-plan avec arrêt propre sur Ctrl+C
BACKEND_PID=""
cleanup() {
  if [ -n "$BACKEND_PID" ] && kill -0 "$BACKEND_PID" 2>/dev/null; then
    echo ""
    echo "[INFO] Arrêt du backend (PID $BACKEND_PID)..."
    kill "$BACKEND_PID" 2>/dev/null || true
    wait "$BACKEND_PID" 2>/dev/null || true
  fi
}
trap cleanup INT TERM EXIT

echo "[INFO] Démarrage du backend API sur http://localhost:8000 ..."
"$ROOT_DIR/.venv/bin/uvicorn" backend.app.main:app --reload --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

echo "[INFO] Démarrage du frontend sur http://localhost:5173 ..."
echo "[INFO] Appuyez sur Ctrl+C pour arrêter les deux services."
cd "$ROOT_DIR/frontend"
npm run dev
