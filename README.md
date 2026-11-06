# Signal Matin — éditions fabriquées par l'agent

Branche d'échange entre la tâche planifiée Claude (rédaction) et le workflow GitHub `fabrication` (collecte, mise en page, e-mail) — mode hybride. Alimentée chaque matin par la tâche planifiée Claude (compétence `gazette`,
sur `cesar/personnalisation`). Un dossier par édition :

| Fichier | Contenu |
|---|---|
| `cache.json` | candidats du jour et textes récupérés |
| `a_faire/<id>.json` | demandes à l'IA : consigne, contenu, format attendu |
| `faits/<id>.json` | réponses rédigées par l'agent |
| `tour.json` | demande de l'agent : numéro du tour, essai, final |
| `etat.json` | réponse de GitHub : demandes en attente, édition terminée ou non, journal |
| `resultat.json` | édition prête, publiée par le workflow `fabrication` |

Un dossier `…-essai-HHMM` est une édition d'essai : e-mail marqué « essai », rien n'est mémorisé.
Republier une édition : demander à Claude (déclenchement manuel du workflow `fabrication` avec le dossier).
