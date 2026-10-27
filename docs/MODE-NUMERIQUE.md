# Recevoir le journal par e-mail, sans le PC

Le journal est généré chaque matin dans le cloud GitHub (GitHub Actions), puis
envoyé par e-mail : version lisible sur téléphone dans le corps du message
(articles, brèves, mots du jour ; ni météo ni jeux), avec la même page HTML en
pièce jointe. Le PC peut rester éteint.

Les mots du jour du voyage (28/10 → 11/11/2026) sont choisis à l'avance dans
`mots_planifies.json`, sur la branche `journal-etat` ; ensuite, le tirage
habituel dans la base reprend.

| Étape | Heure de Paris | Heure grecque |
|---|---|---|
| Lancement (lundi-vendredi) | 4 h 07 | 5 h 07 |
| Bascule en appels directs si le traitement de nuit traîne | 5 h 20 | 6 h 20 |
| E-mail reçu au plus tard | ≈ 5 h 45 | ≈ 6 h 45 |

GitHub peut retarder une tâche planifiée de quelques minutes à une demi-heure.

## 1. Choisir le compte qui envoie

L'adresse qui **reçoit** peut être n'importe laquelle (Proton compris).
L'adresse qui **envoie** doit accepter l'envoi SMTP :

- **Gmail** (recommandé) : activer la validation en deux étapes, puis créer un
  « mot de passe d'application » (myaccount.google.com → Sécurité → Mots de passe
  des applications). Serveur `smtp.gmail.com`, port `465`.
- **Proton Mail** : SMTP réservé aux offres payantes **et** à une adresse sur
  domaine personnalisé ; une adresse @proton.me ne peut pas envoyer par SMTP.
  Serveur `smtp.protonmail.ch`, port `587`.

## 2. Créer les secrets (depuis le téléphone ou un navigateur)

github.com/CesarHolm/signal-matin → **Settings → Secrets and variables → Actions
→ New repository secret**. Les valeurs ne sont jamais visibles ensuite, ni dans
les journaux d'exécution.

| Nom | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | la clé API (la même que dans `.env`) |
| `SMTP_SERVEUR` | ex. `smtp.gmail.com` |
| `SMTP_PORT` | `465` (Gmail) ou `587` (Proton) |
| `SMTP_UTILISATEUR` | l'adresse du compte d'envoi |
| `SMTP_MOT_DE_PASSE` | le mot de passe d'application |
| `MAIL_DESTINATAIRE` | l'adresse qui reçoit le journal |

## 3. Activer GitHub Actions sur le fork

Onglet **Actions** du dépôt → « I understand my workflows, go ahead and enable
them ». Les forks ont les tâches planifiées désactivées par défaut.

## 4. Premier essai

Actions → **journal quotidien** → **Run workflow** (cases « Essai » et « Direct »
cochées) → l'e-mail arrive en quelques minutes, marqué « [Essai] », sans rien
mémoriser.

## 5. Pendant le voyage

- Désactiver les tâches du PC pour éviter une double édition (et une double
  facture) s'il reste branché :
  `powershell -ExecutionPolicy Bypass -File scripts\installer_taches_journal.ps1 -Desinstaller`
- En cas d'échec, GitHub envoie une alerte à l'adresse du compte GitHub ; le
  détail est dans l'onglet Actions.
- Pour suspendre l'envoi : Actions → journal quotidien → « … » → Disable workflow.

## 6. Au retour

La mémoire (mots appris, solutions, articles déjà publiés) est sur la branche
`journal-etat`. Pour que le PC reprenne là où le cloud s'est arrêté, recopier
son contenu dans le dossier `data\` du PC avant de réactiver les tâches.
