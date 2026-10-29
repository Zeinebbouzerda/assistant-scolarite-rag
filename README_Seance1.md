# Séance 1 — Extraction et découpage : fragments et métadonnées dans un fichier JSON

## 1. Objectif de la séance

L'objectif de cette séance est de préparer le corpus documentaire utilisé par notre assistant de scolarité basé sur le principe du RAG (*Retrieval-Augmented Generation*).

Cette préparation consiste à extraire le texte des documents PDF, à découper ce texte en fragments (*chunks*), à associer des métadonnées à chaque fragment et à exporter les résultats au format JSON.

## 2. Présentation du corpus documentaire

Le corpus est constitué de sept documents PDF fictifs portant sur la scolarité d'une école d'ingénieurs, l'École d'Ingénieurs Hélianthe (EIH).

Les documents traitent notamment des sujets suivants :

- Règlement des études 2026-2027 ;
- Guide des stages et du PFE ;
- Charte de mobilité internationale ;
- Calendrier académique 2026-2027 ;
- Guide de la vie étudiante ;
- FAQ Scolarité ;
- Note de service 2026-14.

Les documents sources sont stockés dans le dossier `data/corpus/`.

**Remarque :** les documents sont fictifs et sont utilisés à des fins pédagogiques.

## 3. Extraction du texte

L'extraction du texte est réalisée en Python à l'aide de la bibliothèque PyMuPDF.

Le traitement parcourt les fichiers PDF et extrait leur contenu page par page. Cette approche permet de conserver le lien entre chaque fragment et sa page d'origine.

Les informations extraites sont ensuite utilisées pour préparer les fragments et leurs métadonnées.

## 4. Stratégies de découpage

Deux stratégies de découpage ont été implémentées et comparées.

### 4.1. Découpage de taille fixe

La première stratégie consiste à diviser le texte en fragments de taille limitée.

Paramètres utilisés :

- Taille maximale visée : 800 caractères.
- Chevauchement : 150 caractères.

Le chevauchement permet de conserver une partie du contexte entre deux fragments consécutifs et de limiter la perte d'informations aux frontières des fragments.

**Résultat obtenu : 72 fragments.**

### 4.2. Découpage structurel

La deuxième stratégie consiste à regrouper les paragraphes en respectant autant que possible leur cohérence et leur ordre dans le document.

La taille maximale visée est de 1 200 caractères. Lorsqu'un paragraphe dépasse cette limite, il est découpé en parties plus petites.

Cette stratégie vise à conserver des unités de texte cohérentes, ce qui peut améliorer la pertinence des résultats lors de la recherche documentaire.

**Résultat obtenu : 46 fragments.**

## 5. Métadonnées des fragments

Chaque fragment contient les informations suivantes :

| Champ | Description |
|---|---|
| `chunk_id` | Identifiant unique du fragment |
| `text` | Contenu textuel du fragment |
| `metadata` | Métadonnées du document source |
| `strategy` | Stratégie de découpage utilisée |
| `start` | Position de début du fragment, pour le découpage fixe |
| `end` | Position de fin du fragment, pour le découpage fixe |

Les métadonnées du document comprennent notamment :

- `source` : nom du fichier PDF ;
- `document_id` : identifiant du document ;
- `page` : numéro de la page d'origine ;
- `title` : titre du document ;
- `type` : catégorie du document ;
- `version` : version du document, lorsqu'elle est disponible ;
- `status` : statut du document, lorsqu'il est renseigné.

Ces métadonnées permettent d'assurer la traçabilité des informations et de retrouver les sources des passages utilisés par l'assistant.

## 6. Export des résultats au format JSON

Les fragments sont exportés automatiquement au format JSON à l'aide du script `export_chunks_json.py`.

Les fichiers générés sont enregistrés dans `data/processed/` :

- `chunks_fixed.json` : fragments issus du découpage de taille fixe ;
- `chunks_structural.json` : fragments issus du découpage structurel.

Chaque fichier contient une liste de fragments avec leur texte et leurs métadonnées.

### Exemple de structure JSON

```json
{
  "chunk_id": "document_p1_0",
  "text": "Exemple de texte extrait du document...",
  "metadata": {
    "source": "01_Reglement_des_etudes_2026-2027.pdf",
    "document_id": "identifiant_document",
    "page": 1,
    "title": "Règlement des études",
    "type": "reglement",
    "version": null,
    "status": "active"
  },
  "start": 0,
  "end": 800,
  "strategy": "fixed_size"
}
```

Cet exemple illustre la structure d'un fragment issu du découpage fixe. Les valeurs sont données à titre indicatif.

## 7. Organisation des fichiers

```text
assistant-scolarite-rag/
├── data/
│   ├── corpus/
│   │   └── documents PDF
│   └── processed/
│       ├── chunks_fixed.json
│       └── chunks_structural.json
├── backend/
│   └── app/
│       └── services/
│           ├── extraction.py
│           └── chunking.py
├── export_chunks_json.py
├── verify_json.py
└── README_Seance1.md
```

## 8. Exécution du traitement

Depuis la racine du projet, avec l'environnement virtuel activé, exécuter :

```bash
python export_chunks_json.py
```

Cette commande extrait le texte des documents PDF, applique les deux stratégies de découpage et génère les fichiers JSON.

Pour vérifier les fichiers générés, exécuter :

```bash
python verify_json.py
```

Le script de vérification contrôle la présence des champs essentiels et des métadonnées de source et de page.

## 9. Résultats et validation

Les vérifications réalisées ont donné les résultats suivants :

| Indicateur | Découpage fixe | Découpage structurel |
|---|---:|---:|
| Nombre de fragments | 72 | 46 |
| Clés obligatoires manquantes | 0 | 0 |
| Fragments sans source ou page | 0 | 0 |
| Format JSON | Valide | Valide |

Ces résultats confirment que les deux fichiers JSON ont été générés et que les contrôles structurels effectués sont satisfaisants.

## 10. Conclusion

Cette séance a permis de mettre en place une première chaîne de préparation documentaire : extraction du texte, découpage selon deux stratégies, enrichissement par des métadonnées et export au format JSON.

Les fragments obtenus constituent la base documentaire nécessaire aux étapes suivantes du projet, notamment la génération des embeddings, l'indexation dans une base vectorielle et la recherche sémantique dans le système RAG.
