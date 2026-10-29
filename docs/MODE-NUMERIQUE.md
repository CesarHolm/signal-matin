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

## 1. Envoi par Resend (retenu le 29/10/2026)

Gmail refuse les connexions SMTP venant des serveurs GitHub (connexion coupée
avant toute identification, constaté le 29/10/2026 sur les ports 465 et 587).
L'envoi passe donc par **Resend**, un service d'envoi qui fonctionne en HTTPS.

1. Compte sur resend.com créé avec **l'adresse Proton** qui reçoit le journal
   (mot de passe propre à Resend). Sans domaine vérifié, Resend n'envoie qu'à
   l'adresse du compte, depuis `onboarding@resend.dev`.
2. Resend → **API Keys → Create API Key** (« Sending access »).
3. Resend ne voit que le journal qu'il envoie : aucun accès à la boîte Proton.

Le code choisit Resend dès que le secret `RESEND_API_KEY` existe ; sinon il
retombe sur le SMTP (secrets `SMTP_…`, bascule automatique 465 ↔ 587).

## 2. Créer les secrets (depuis le téléphone ou un navigateur)

github.com/CesarHolm/signal-matin → **Settings → Secrets and variables → Actions
→ New repository secret**. Les valeurs ne sont jamais visibles ensuite, ni dans
les journaux d'exécution.

| Nom | Valeur |
|---|---|
| `ANTHROPIC_API_KEY` | la clé API Anthropic (la même que dans `.env`) |
| `RESEND_API_KEY` | la clé Resend (`re_…`) |
| `MAIL_DESTINATAIRE` | l'adresse Proton du compte Resend |

Taper les valeurs à la main plutôt que les coller : le copier-coller sur
téléphone ajoute parfois des espaces (le code les retire, par précaution).

## 3. Activer GitHub Actions sur le fork

Onglet **Actions** du dépôt → « I understand my workflows, go ahead and enable
them ». Les forks ont les tâches planifiées désactivées par défaut.

## 4. Premier essai

Actions → **journal quotidien** → **Run workflow** (cases « Essai » et « Direct »
cochées) → l'e-mail arrive en quelques minutes, marqué « [Essai] », sans rien
mémoriser.

Option « Tester seulement la connexion e-mail » : vérifie les secrets d'envoi
en 30 secondes, sans génération ni appel IA ; le résultat s'affiche dans les
annotations du run.

## 4 bis. Contenu de la version numérique (validé le 29/10/2026)

Sans contrainte de page, la version téléphone est plus complète que le journal
imprimé, qui reste inchangé :

- **Au sommaire**, sous les mots du jour : par catégorie, le titre de chaque
  article avec un lien direct, puis les brèves.
- Par catégorie : jusqu'à **6 articles développés**, dont **4 longs** (jusqu'à
  4 500 caractères, 4 à 6 sections) ; les autres en format court enrichi
  (jusqu'à 1 800 caractères, 2 ou 3 sections).
- **Brèves** plus complètes (2 à 3 phrases, environ 450 caractères), jusqu'à 6
  par catégorie.
- Pas de PDF A4 généré ; pas de météo, de jeux ni de quiz.
- Coût API estimé : environ 2 à 3 fois l'édition imprimée (plus de synthèses
  Sonnet), soit de l'ordre de 4 à 6 $ par mois, sous le plafond conseillé de 15 $.

Réglages : `src/signal_matin/journal/mise_en_page.py` (constantes `NUM_…`).

GitHub peut retarder une tâche planifiée de plusieurs heures (constaté le 28 et
le 29/10/2026 : lancement vers 10 h 30 au lieu de 4 h 07, heure de Paris).

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
