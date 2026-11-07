# Trame du rapport (6 pages maximum)

Écrivez-le avec vos mots et vos chiffres. Page budget indicatif.

**1. Introduction (0,5 p.)** Problème (étudiants, documents hétérogènes, versions), objectif, résumé de la solution.

**2. Architecture (1 p.)** Reprenez le schéma du README (ingestion / question). Justifiez chaque brique : PyMuPDF, MiniLM multilingue, Chroma, Gemini, FastAPI, React. Indiquez le contrat d'API.

**3. Ingestion et découpage (1,5 p.)**
- Extraction : métadonnées lues dans la fiche, titres détectés par la police, en-têtes/pieds supprimés, lignes de tableau reliées à leurs en-têtes (donnez l'exemple du 12 février 2027).
- Les deux stratégies et leurs paramètres. Pourquoi un en-tête contextuel (titre + section) devant le texte encodé ?
- Piège PyMuPDF : cellules sans espaces, parade par `get_text(clip=…)`.

**4. Génération et gestion des versions (1,25 p.)**
- Le prompt, règle par règle (voir `app/services/prompts.py`) : pourquoi chacune ?
- Documents modificatifs : détection générique dans le champ *Statut*, ajout au contexte, présentation « modifie / modifié par » + date.
- Garde-fous côté code : seuil, vérification des citations. Que ne vérifient-ils *pas* ?

**5. Évaluation (1,75 p.)** Jeu de test (composition), métriques (définitions), **tableau comparatif de vos configurations**, calibrage du seuil, puis *au moins 3 exemples* d'écart expliqués : question, fragments retournés, pourquoi la configuration A réussit et B échoue.

**6. Limites et perspectives (0,5 p.)** Par exemple : pas de mémoire de conversation ; seuil dépendant du modèle ; citations vérifiées formellement et non sémantiquement ; dépendance à la qualité du LLM pour la précédence des règles ; recherche hybride (BM25) et reranking comme pistes.

**Annexe (hors 6 pages)** : déclaration d'utilisation des outils d'IA générative.
