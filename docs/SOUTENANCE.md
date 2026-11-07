# Préparer la soutenance (15 min, démonstration en direct)

## Déroulé conseillé
| Min | Contenu |
|---:|---|
| 0-2 | Problème et schéma d'architecture |
| 2-6 | Ingestion : extraction (titres, tableaux, métadonnées), les deux découpages |
| 6-9 | Génération : prompt, seuil, citations, documents modificatifs |
| 9-12 | **Démo en direct** (script ci-dessous) |
| 12-14 | Résultats d'évaluation et limites |
| 14-15 | Conclusion |

## Script de démonstration (testez-le la veille, API déjà indexée)
1. « Combien de jours avant le début d'un stage la convention doit-elle être déposée ? » : une réponse simple, cliquez sur `[1]`, montrez la page et le score.
2. « Quelle est la durée minimale d'un PFE qui commence en février 2027 ? » : la réponse doit signaler que la note de service a remplacé le guide ; montrez les deux sources.
3. « Le stage d'initiation est-il rémunéré ? » : refus avec son style distinct.
4. Onglet **Recherche** : même question qu'en 2, montrez les fragments bruts et leurs scores sans LLM.
5. Coupez l'API : montrez le message d'erreur clair. Ouvrez sur mobile.
Prévoyez un plan B : captures d'écran et réponse enregistrée si le quota Gemini est atteint.

## Ce que chacun doit savoir expliquer sans notes
- **Extraction** : pourquoi la taille/gras de la police donne les titres ; comment on repère un en-tête répété ; pourquoi `find_tables().extract()` est évité.
- **Découpage** : la fonction `window_spans` (fenêtre, chevauchement, coupure propre), la différence fixe/structurel, pourquoi une ligne de tableau n'est jamais coupée.
- **Embeddings et score** : cosinus ; score = 1 − distance Chroma ; pourquoi 384 tokens ; pourquoi le seuil dépend du modèle.
- **Prompt** : le rôle de chacune des 6 règles ; protection contre l'injection (le contenu des PDF est une donnée).
- **Versions** : comment le lien « note → guide » est trouvé sans écrire de référence en dur ; pourquoi on ajoute les fragments du document modificatif au contexte.
- **Contrôles** : seuil (refus sans LLM) ; citations (numéro valide ≠ citation juste).
- **Évaluation** : Hit@k, MRR, couverture, exactitude 0-2, taux de refus correct / à tort, et pourquoi le jeu de test est annoté par « gold » plutôt que par identifiants de fragments.

## Questions probables du jury
- *Pourquoi ne pas simplement envoyer les 7 documents au LLM ?* Coût et limites de contexte, mais surtout traçabilité et passage à l'échelle d'un vrai corpus.
- *Que se passe-t-il si le LLM cite un numéro inexistant ?* Il est listé dans `invalid_citations` et l'interface le barre.
- *Comment gérez-vous la règle modifiée ?* Lien détecté dans le statut, fragments modificatifs ajoutés, dates et liens présentés au modèle, règle de précédence dans le prompt. Limite : le LLM peut encore mal appliquer la règle ; mesurez-le dans l'évaluation.
- *Votre seuil est-il fiable ?* Réponse honnête : c'est un garde-fou grossier, calibré sur un petit jeu ; les cas ambigus reposent sur le refus du LLM.
- *Qu'avez-vous fait vous-mêmes, et avec quelle aide d'IA ?* Voir la déclaration : soyez précis et sincères.
