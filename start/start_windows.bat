@echo off
REM Script de lancement complet (Backend FastAPI + Frontend Vite) pour Windows 10/11.
REM Usage : double-cliquer sur start_windows.bat ou executer start\start_windows.bat

setlocal

REM Resout la racine du projet par rapport a ce script
set "ROOT_DIR=%~dp0.."
cd /d "%ROOT_DIR%"

REM 1. Verification de l'environnement virtuel Python
if not exist "%ROOT_DIR%\.venv\Scripts\uvicorn.exe" (
    echo [ERREUR] Environnement virtuel .venv introuvable ou incomplet.
    echo Executez d'abord dans Command Prompt :
    echo   python -m venv .venv
    echo   .venv\Scripts\activate.bat
    echo   pip install -r backend\requirements.txt
    pause
    exit /b 1
)

REM 2. Verification des fichiers .env
if not exist "%ROOT_DIR%\.env" (
    copy "%ROOT_DIR%\.env.example" "%ROOT_DIR%\.env" >nul
    echo [INFO] Fichier .env cree depuis .env.example.
    echo [ATTENTION] Renseignez GEMINI_API_KEY et GEMINI_MODEL dans .env avant de poser des questions.
)

if not exist "%ROOT_DIR%\frontend\.env" (
    copy "%ROOT_DIR%\frontend\.env.example" "%ROOT_DIR%\frontend\.env" >nul
    echo [INFO] Fichier frontend\.env cree depuis frontend\.env.example.
)

REM 3. Installation des dependances frontend si necessaire
if not exist "%ROOT_DIR%\frontend\node_modules" (
    echo [INFO] Installation des dependances frontend ^(npm install^)...
    pushd "%ROOT_DIR%\frontend"
    call npm install
    if errorlevel 1 (
        echo [ERREUR] Echec de npm install. Verifiez que Node.js est installe.
        popd
        pause
        exit /b 1
    )
    popd
)

REM 4. Indexation initiale du corpus si la base ChromaDB n'existe pas encore
if not exist "%ROOT_DIR%\storage\chroma" (
    echo [INFO] Base vectorielle absente : indexation initiale du corpus...
    "%ROOT_DIR%\.venv\Scripts\python.exe" "%ROOT_DIR%\ingest_corpus.py" --strategy structural
    if errorlevel 1 (
        echo [ERREUR] Echec de l'indexation du corpus.
        pause
        exit /b 1
    )
)

REM 5. Lancement du backend et du frontend dans deux fenetres separees
echo [INFO] Demarrage du backend API sur http://localhost:9500 ...
start "Assistant Scolarite - Backend" cmd /k "cd /d "%ROOT_DIR%" && call .venv\Scripts\activate.bat && uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 9500"

echo [INFO] Demarrage du frontend sur http://localhost:5173 ...
start "Assistant Scolarite - Frontend" cmd /k "cd /d "%ROOT_DIR%\frontend" && npm run dev"

REM Ouvre l'interface dans le navigateur apres une courte attente
timeout /t 3 /nobreak >nul
start "" "http://localhost:5173"

echo [INFO] Les deux serveurs sont lances. Fermez leurs fenetres pour les arreter.
endlocal
