# Script de Démonstration — Sensai (Hogwarts Edition ⚡)

> **Objectif** : Démonstration live fluide, scénarisée et 100 % rejouable devant le jury.  
> **Scénario** : Un élève de 1ère année à Poudlard (Maison Gryffondor) utilise Sensai comme tuteur personnel pour réviser ses cours de Potions et de Métamorphose.  
> **Durée estimée** : 5 à 7 minutes.

---

## 0. Pré-requis avant de monter sur scène

1. Vérifier qu'Ollama est lancé :
   ```bash
   ollama list
   # Doit afficher llama3.2:latest
   ```
2. Nettoyer ou initialiser une base propre pour la démo :
   ```bash
   rm -f demo.db
   ```

---

## Étape 1 : Profil de l'élève & Démarrage avec le Professeur Rogue [B1, A5, M1]

**Commande à lancer dans le terminal :**
```bash
python -m sensai --db demo.db --persona snape --set-profile name=Harry --set-profile house=Gryffindor
```

**Comportement attendu :**
- L'assistant démarre avec l'identité de **Severus Rogue** (ton sévère, froid et exigeant).
- Le profil de l'élève (`name=Harry`, `house=Gryffindor`) est persisté dans SQLite (`profile`).

**Prompt 1 à copier-coller :**
```text
Bonjour professeur, je souhaite apprendre à préparer la potion d'Aiguise-Mémoire.
```
*Observer : Réponse de Rogue, streaming token par token, ton cassant caractéristique.*

---

## Étape 2 : Mémoire Structurée — Mémorisation d'un fait durable [M3]

**Prompt 2 à copier-coller :**
```text
Attention professeur, j'ai une allergie sévère aux branchies de grenouille. Notez-le bien.
```

**Ce qui se passe sous le capot :**
- Le modèle détecte un fait durable et déclenche l'outil `remember_fact(key="allergy", value="branchies de grenouille")`.
- L'information est stockée dans la table SQLite `facts`.
- Rogue confirme qu'il en prend note avec mépris.

---

## Étape 3 : Changement de Professeur en direct & Conservation du contexte [A5]

**Commande interactive dans le chat :**
```text
/persona dumbledore
```

**Comportement attendu :**
- L'assistant bascule instantanément sur **Albus Dumbledore**.
- Le terminal affiche la confirmation du changement d'identité.
- **L'historique complet est conservé** (Dumbledore sait ce qui a été dit avec Rogue).

**Prompt 3 à copier-coller :**
```text
Professeur Dumbledore, pouvez-vous me donner les ingrédients pour cette potion ?
```

**Ce qui se passe sous le capot :**
- Dumbledore répond avec son ton sage, bienveillant et posé.
- Il invoque `recall_fact(key="allergy")` et **met explicitement en garde l'élève** sur son allergie aux branchies de grenouille !
- *(Prouve au jury la synergie M3 + A5 : la mémoire externe survit au changement de persona).*

---

## Étape 4 : Export de la séance de révision [X3]

**Commande interactive dans le chat :**
```text
/export markdown export/revision_potions.md
```

**Comportement attendu :**
- Confirmation : `Exported session to export/revision_potions.md`.
- Quitter le chat :
```text
exit
```

---

## Étape 5 : Reprise de session et Persistance [M1]

**Commande à lancer dans le terminal :**
```bash
python -m sensai --db demo.db --resume
```

**Comportement attendu :**
- Le chatbot recharge la session précédente et affiche le nombre de messages rechargés.
- L'élève peut continuer la conversation exactement là où il s'était arrêté.
- Quitter avec `exit`.

---

## Étape 6 : Génération Structurée JSON [T5]

**Commande à lancer dans le terminal :**
```bash
python -m sensai --db demo.db --persona snape --schema schemas/potion.json
```

**Prompt 4 à copier-coller :**
```text
Génère la fiche officielle de la potion de Polynectar avec ses ingrédients et son niveau de danger.
```

**Comportement attendu :**
- Le modèle renvoie **strictement un objet JSON** validé côté client par rapport à `schemas/potion.json`.
- Pas de texte d'enrobage superflu : une structure exploitable directement par une application.
- Quitter avec `exit`.

---

## Étape 7 : Garde-fous de Sécurité [EV2]

**Commande à lancer :**
```bash
python -m sensai --db demo.db
```

**Prompt 5 (Test de blocage) :**
```text
Voici le mot de passe secret de la salle commune : Alohomora123!
```

**Comportement attendu :**
- Le message est **immédiatement intercepté et bloqué** :  
  `[guardrail] Blocked by guardrails: please avoid sharing or requesting sensitive data related to 'password'.`
- Le message n'est pas envoyé au LLM et n'est pas enregistré dans l'historique.
- Quitter avec `exit`.

---

## Étape 8 : Démonstration de l'Interface Web [X1] (Clap de fin)

**Commande à lancer :**
```bash
python -m sensai.features.web_ui --db demo.db
```

**Dans le navigateur (`http://127.0.0.1:8000`) :**
1. Montrer l'historique de la session précédente dans la barre latérale.
2. Montrer le changement de professeur en direct via le menu déroulant (Rogue -> McGonagall -> Dumbledore).
3. Montrer les compteurs de tokens en temps réel sous chaque réponse.
4. Télécharger l'export Markdown en 1 clic via le bouton d'export.

---

## Tableau récapitulatif pour la soutenance

| Étape | Fonctionnalité montrée | Preuve pour le jury |
| :--- | :--- | :--- |
| **Étape 1** | [B1] CLI + [A5] Rogue + [M1] Profil | Streaming immédiat, ton Rogue, Gryffindor injecté |
| **Étape 2** | [M3] Mémoire structurée SQLite | Tool call `remember_fact` pour l'allergie |
| **Étape 3** | [A5] Switch Persona + [M3] Recall | Changement de ton (Dumbledore), alerte allergie active |
| **Étape 4** | [X3] Export Markdown | Fichier `revision_potions.md` généré proprement |
| **Étape 5** | [M1] Reprise `--resume` | Rechargement instantané de l'historique |
| **Étape 6** | [T5] Output JSON Schema | Sortie JSON stricte conforme à `potion.json` |
| **Étape 7** | [EV2] Guardrails | Interception locale du mot de passe |
| **Étape 8** | [X1] Web UI | Navigation graphique fluide, tokens, export |
