# Signal Matin — éditions fabriquées par l'agent

Branche alimentée chaque matin par la tâche planifiée Claude (compétence `gazette`,
sur `cesar/personnalisation`). Un dossier par édition :

| Fichier | Contenu |
|---|---|
| `cache.json` | candidats du jour et textes récupérés |
| `a_faire/<id>.json` | demandes à l'IA : consigne, contenu, format attendu |
| `faits/<id>.json` | réponses rédigées par l'agent |
| `resultat.json` | édition prête, publiée par le workflow `publier` |

Un dossier `…-essai-HHMM` est une édition d'essai : e-mail marqué « essai », rien n'est mémorisé.
Republier une édition : demander à Claude (déclenchement manuel du workflow `publier` avec le dossier).
