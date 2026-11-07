# Plan de travail : ce qu'il vous reste à faire

Le code des 5 séances est écrit et testé **avec un modèle d'embeddings et un LLM de substitution** (pas de réseau là où il a été construit).
Ce qui n'a donc jamais tourné : le vrai MiniLM et le vrai Gemini. Les étapes ci-dessous sont celles où vous découvrirez les vrais résultats.
**Aucun chiffre de qualité n'est fourni ici : vous les produisez et vous les expliquez.**

## Étape 0 : installer et nettoyer (30 min)
1. Dézippez par-dessus votre dossier, puis suivez `docs/CHANGEMENTS.md` (nettoyage git).
2. `pip install -r backend/requirements.txt`, vérifiez votre `.env`.
3. **Régénérez votre clé Gemini** : elle figurait dans l'archive que vous m'avez envoyée.
4. `pytest` : 21 tests doivent passer.

## Étape 1 : premier vrai test (séances 2-3)
1. `python ingest_corpus.py --strategy structural` (télécharge MiniLM la première fois).
2. `uvicorn backend.app.main:app --reload`, puis dans `/docs` : `GET /api/health` (91 fragments attendus), `POST /api/search`, `POST /api/ask`.
3. Posez les 6 questions de l'énoncé. Pour chacune, regardez les fragments dans `/api/search` **avant** de juger la réponse : c'est le réflexe qui sépare un bug de recherche d'un bug de génération.
4. Cas à surveiller : « durée minimale du PFE en février 2027 » doit répondre 18 semaines et signaler le changement ; « stage d'initiation rémunéré ? » doit refuser.

## Étape 2 : calibrer le seuil
```powershell
python eval/run_eval.py --configs structural:1000:100:5 --sweep
```
Lisez le tableau : il donne, pour chaque seuil, le pourcentage de questions *dans* le corpus refusées à tort et de questions *hors* corpus refusées à raison.
Reportez la valeur retenue dans `.env` (`SIMILARITY_THRESHOLD`) et **justifiez-la dans le rapport**. Le seuil ne sépare jamais parfaitement : « stage d'initiation rémunéré » parle d'un sujet présent dans le corpus, donc seul le prompt peut le refuser.

## Étape 3 : évaluation (séance 5)
```powershell
# recherche seule : rapide, sans quota
python eval/run_eval.py --configs fixed:500:100:3 fixed:500:100:8 structural:1000:100:3 structural:1000:100:8
# génération : ~21 appels Gemini par configuration, 4 s de pause entre appels (quota gratuit)
python eval/run_eval.py --configs fixed:500:100:5 structural:1000:100:5 --generate
```
Résultats dans `eval/results/<date>/` : `report.md` (tableaux), `details.jsonl` (réponse et sources de chaque question), `manual_grading.csv`.

- **Hit@k** : au moins un fragment pertinent dans les k premiers. **MRR** : moyenne de 1/rang du premier fragment pertinent. **Couverture@k** : part des faits attendus retrouvés (utile pour les questions de synthèse).
- Un fragment est « pertinent » s'il vient d'un des documents attendus et contient la phrase indiquée dans `gold` (`eval/questions.jsonl`).
- Exactitude 0-2 *automatique* : 2 = tous les faits attendus présents dans la réponse, 1 = au moins la moitié, 0 sinon. **Corrigez-la à la main** dans `manual_grading.csv` (une réponse peut contenir « 18 semaines » et être fausse) et notez aussi la **fidélité** (chaque affirmation est-elle bien soutenue par le fragment cité ?).
- Le rapport doit **expliquer les écarts avec des exemples** : ouvrez `details.jsonl` et la section « Échecs de recherche » du `report.md`.

Hypothèses à *tester* (ne les écrivez dans le rapport que si vos chiffres les confirment) : le découpage fixe coupe-t-il des lignes de tableau ou des articles ? k = 3 suffit-il aux questions de synthèse ? Le document modificatif est-il toujours dans le contexte ?

## Étape 4 : compléter le jeu de test
Le jeu fourni (21 questions : 8 simples, 5 synthèses, 3 versions, 5 hors corpus) respecte l'énoncé. **Ajoutez au moins 3 questions pièges de votre invention** (par exemple une question qui mélange deux règles, une reformulation éloignée du texte, une question hors corpus proche d'un sujet du corpus), avec réponse attendue et passage `gold`. Vérifiez avec `python eval/run_eval.py --check-gold`.

## Étape 5 : livrables
| Livrable | État |
|---|---|
| Dépôt Git partagé avec l'enseignant, commits réguliers | à faire : un commit par étape ci-dessus |
| README (installation, variables, lancement, choix techniques) | fourni, à relire et personnaliser |
| ≥ 5 tests pytest dont découpage et refus hors corpus | 21 fournis |
| Rapport ≤ 6 pages | trame dans `docs/RAPPORT_PLAN.md` |
| Annexe déclaration d'IA générative | modèle dans `docs/DECLARATION_IA.md` |
| Soutenance 15 min avec démo en direct | préparation dans `docs/SOUTENANCE.md` |

## Répartition suggérée à deux
| | Personne A | Personne B |
|---|---|---|
| Étapes 0-1 | installation, ingestion, tests API dans `/docs` | frontend : lancer, tester sur mobile, tous les codes d'erreur |
| Étape 2-3 | calibrage du seuil, évaluation recherche | évaluation génération, notation manuelle |
| Étape 4 | questions pièges (version, synthèse) | questions pièges (hors corpus, reformulations) |
| Rapport | architecture, choix, limites | résultats, comparaison, exemples |

Chacun doit pouvoir expliquer **tout** le projet : croisez les relectures.
