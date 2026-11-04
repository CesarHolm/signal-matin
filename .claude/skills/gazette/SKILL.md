---
name: gazette
description: Fabrique l'édition numérique quotidienne de Signal Matin (collecte, tri, rédaction) et la pousse sur la branche claude/editions, où GitHub la met en page et l'envoie par e-mail. Utilisée par la tâche planifiée du matin ; « essai » dans la demande produit une édition d'essai.
---

# Gazette Signal Matin

Tu fabriques l'édition numérique du jour. Le programme Python fait tout ce qui ne
demande pas d'IA (collecte des flux, textes complets, PDF, mise en page, e-mail) ;
toi, tu fais rédiger les réponses demandées, **à l'aide de sous-agents**, sans
rien inventer. Les consignes de rédaction sont dans les fichiers de demande : tu
ne les modifies pas, tu ne les résumes pas.

Règles absolues :
- Aucune information extérieure aux textes fournis. Aucune recherche web.
- Ne jamais afficher ni demander de clé ou de secret.
- Ne jamais modifier le code, la configuration ni les branches autres que `claude/editions`.

## 1. Préparation

Depuis la racine du dépôt :

```bash
git fetch -q origin cesar/personnalisation journal-etat
git checkout -q cesar/personnalisation
git worktree add -f data origin/journal-etat          # mémoire du journal (lecture seule ici)
if git fetch -q origin claude/editions; then
  git worktree add -f livraison origin/claude/editions
else
  git worktree add -f --orphan -b claude/editions livraison
fi
pip install -q -e . 2>&1 | tail -1
cp config.cesar.example.yaml config.yaml
```

Dossier de l'édition :
- édition normale : `D=livraison/editions/$(TZ=Europe/Paris date +%F)` ;
- si la demande contient « essai » : `D=livraison/editions/$(TZ=Europe/Paris date +%F)-essai-$(TZ=Europe/Paris date +%H%M)`
  et ajoute `--essai` à la première commande `avancer`.

Si `$D/resultat.json` existe déjà pour une édition normale, l'édition du jour est
déjà faite : arrête-toi et réponds « Édition du jour déjà produite ».

## 2. Boucle de fabrication (4 tours au plus)

```bash
python main.py journal-agent avancer "$D"        # + --essai au premier appel d'un essai
```

- **Code 0** : l'édition est prête (`$D/resultat.json`). Passe à l'étape 3.
- **Code 3** : la dernière ligne commence par `A_FAIRE` et liste les demandes en
  attente (`a_faire/<id>.json`). Fais-les traiter (ci-dessous), lance
  `python main.py journal-agent verifier "$D"`, fais refaire **une fois** les
  réponses signalées (en donnant le problème au sous-agent), puis relance `avancer`.
- **Autre code** : erreur du programme. Note les dernières lignes et passe à l'étape 4 (échec).

Ordre normal : tour 1 = tri des sections (et mots si demandés), tour 2 = brèves
complémentaires et articles, tour 3 = édition prête.

Après 4 tours, ou si une demande reste sans réponse valable après la seconde
tentative, termine avec `python main.py journal-agent avancer "$D" --final` :
l'édition sort avec les sections manquantes signalées en tête de l'e-mail.

### Faire traiter les demandes

Chaque fichier `a_faire/<id>.json` contient : `modele` (haiku ou sonnet),
`systeme` (la consigne), `contenu` (le message à traiter), `schema` (format JSON
attendu), `sortie` (fichier à écrire) et parfois `limite_caracteres`.

Regroupe les demandes pour limiter le nombre de sous-agents :
- toutes les demandes `haiku` (tri-*, mots, breves) : **un seul** sous-agent, modèle `haiku` ;
- les demandes `sonnet` (syn-*) : des sous-agents de modèle `sonnet`, **4 demandes au plus** chacun.

Lance tous les sous-agents d'un même tour **en parallèle** (outil Agent, type
`general-purpose`, paramètre `model` = `haiku` ou `sonnet`), avec ce message, en
remplaçant la liste :

> Pour chacun de ces fichiers, l'un après l'autre : <D>/a_faire/<id>.json, …
> Lis le fichier. Le champ « systeme » est ta consigne, le champ « contenu » le message à traiter.
> Applique la consigne au contenu à la lettre, en français, sans aucune information extérieure
> au contenu, sans recherche web et sans ouvrir d'autre fichier. Écris uniquement l'objet JSON de
> ta réponse, conforme au champ « schema », dans le fichier <D>/<sortie> (UTF-8, rien autour).
> Si « limite_caracteres » est indiqué, le total chapô + intertitres + textes des sections +
> synthèse doit faire 90 à 100 % de cette limite : compte-le avec Python avant d'écrire et ajuste.
> Termine par une ligne par fichier : « <id> OK » ou « <id> PROBLÈME : … ».

Tu ne rédiges pas toi-même et tu ne lis pas les textes des articles : tu
coordonnes. Si un sous-agent échoue, relance-le une fois pour les fichiers concernés.

## 3. Livraison

```bash
cd livraison
git add -A editions
git -c user.name="Signal Matin (agent)" -c user.email="noreply@anthropic.com" \
    commit -qm "Édition $(basename "$D")"
git push -q origin HEAD:claude/editions
```

Le push déclenche le workflow « publier » de la branche `claude/editions` : mise
en page, mémoire du journal et e-mail. Un seul commit par édition.

## 4. Compte rendu

Termine par **une seule ligne** :
- succès : « Édition <date> livrée : N articles, M brèves » (+ « incomplète : … » si des sections manquent) ;
- échec : « ÉCHEC gazette <date> : <raison en une phrase> ». Rien n'est poussé
  si l'édition n'a pas pu être produite ; Cesar relancera l'édition à la main.
