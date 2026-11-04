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
| Lancement (lundi-samedi) | 4 h 07 | 5 h 07 |
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

## 4 bis. Contenu de la version numérique (validé le 29/10, structure du 02/11/2026)

Sans contrainte de page, la version téléphone est plus complète que le journal
imprimé, qui reste inchangé (8 pages, blocs d'origine).

**Six catégories**, dans cet ordre (sources : `blocs_numerique` dans `config.cesar.example.yaml`) :

| Catégorie | Contenu |
|---|---|
| IA | Uniquement l'IA (arXiv retiré le 04/11/2026 : aucun papier retenu) |
| Actualité France | Surtout des faits, un peu d'analyse ; pas d'international sauf si la France est concernée |
| Actualité Monde | Surtout des faits, un peu d'analyse |
| Recherche & travaux d'experts | Papiers de recherche et analyses de chercheurs : économie, finance, social, droit, santé publique, climat, astronomie, mathématiques |
| Veille réglementaire | RGPD, AI Act, NIS 2, anti-corruption, CSRD/CSDDD, sanctions et contrôle des exportations ; LCB-FT et DORA en second rang. Évolutions, sanctions et leurs motifs, mise en conformité. Priorité à l'Europe |
| Curiosités | Tout le reste : science, climat, espace, sport, idées |

Règles :

- **Au sommaire**, sous les mots du jour : par catégorie, le titre de chaque
  article avec un lien direct, puis les brèves ; « Rien de notable aujourd'hui »
  si une catégorie est vide.
- **Deux formats** (04/11/2026) : article long et brève (~450 caractères). La
  longueur du long suit la matière de la source : la moitié du texte, 4 500
  caractères au plus ; une source mince donne un long plus court.
- **Plafonds par catégorie** (04/11/2026), sans minimum : IA 4 longs + 4 brèves ;
  France 3 + 3 ; Monde 3 + 3 ; Recherche 2 + 4 (brèves : conclusions seulement) ;
  Veille réglementaire 2 + 2 ; Curiosités 2 + 4 (`max_longs`, `max_breves` dans
  `blocs_numerique`). Au plus 3 articles et 3 brèves d'une même source.
- **Tri** : (1) le sujet relève de la catégorie (France et Monde : toute l'actualité) ;
  (2) importance, nouveauté, diversité. Long = important ou fondamental ; brève =
  intéressant à savoir.
- **Papiers de recherche** : lecture du PDF si la page ne donne qu'un résumé ;
  trame « La question · Les conclusions · La méthode · Ce que ça implique · Les
  limites » (limites seulement si les auteurs en citent), avec la référence
  (auteurs, institution, date, nature du document).
- **Texte trop court** (article payant, page fermée) : pour tout article retenu en
  long, le programme cherche le même sujet dans les autres sources du jour, puis sur
  Google Actualités, et rédige à partir de ces textes en citant chaque source ; avec
  l'agent, chaque source complémentaire est d'abord vérifiée (même fait). Sans
  matière suffisante, l'article devient une brève.
- **Google Actualités** couvre les thèmes de veille sans flux exploitable (NIS 2,
  anti-corruption, sanctions UE, OFAC, contrôle des exportations, LCB-FT,
  CSRD/CSDDD) ; les liens sont résolus vers l'article d'origine, les médias en
  écriture non latine sont écartés.
- Écartés le 02/11/2026 : VoxEU et The Conversation (catégorie Recherche),
  medRxiv (prépublications non relues), recherche en géopolitique.
- Pas de PDF A4 généré ; pas de météo, de jeux ni de quiz.
- **Parution du lundi au samedi** (validé le 31/10/2026) : chaque édition couvre les
  24 h précédentes ; le samedi = les infos du vendredi ; le lundi = 48 h (samedi et
  dimanche). Les samedis n'ont pas de mots planifiés : tirage habituel dans la base.

Vérifier une source avant de l'ajouter : lister les flux dans
`scripts/verif/candidats.txt`, lancer le workflow « verification des sources »,
lire le résultat dans `verif-sources.txt` (branche `diagnostic`).
Chaque essai manuel copie aussi son journal d'exécution et sa page sur la branche
`diagnostic` (dossier `essai/`).

Réglages : `src/signal_matin/journal/mise_en_page.py` (constantes `NUM_…`).

GitHub peut retarder une tâche planifiée de plusieurs heures (constaté le 28 et
le 29/10/2026 : lancement vers 10 h 30 au lieu de 4 h 07, heure de Paris).

## 4 ter. Lancement à l'heure : cron-job.org (mis en place le 29/10/2026)

Depuis fin août 2026, la planification GitHub part avec 3 à 10 h de retard.
Le lancement est donc confié à **cron-job.org**, qui appelle chaque matin
(lundi-samedi, 4 h 07, Europe/Paris) l'API GitHub, comme le bouton « Run workflow » :

- URL : `POST https://api.github.com/repos/CesarHolm/signal-matin/actions/workflows/journal-quotidien.yml/dispatches`
- En-têtes : `Authorization: Bearer <jeton>`, `Accept: application/vnd.github+json`,
  `X-GitHub-Api-Version: 2022-11-28`, `Content-Type: application/json`
- Corps : `{"ref":"main","inputs":{"essai":"false","direct":"false"}}`
- Réponse attendue : 204
- Jeton : jeton GitHub « fine-grained » limité au dépôt `signal-matin`, permission
  **Actions : Read and write** uniquement.

La planification GitHub reste en secours : chaque lancement réel vérifie d'abord
si l'édition du jour est déjà enregistrée sur `journal-etat` et s'arrête si oui.
Un seul e-mail, une seule facture par jour.

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

## 7. Fabrication par l'agent Claude (abonnement, en préparation)

Plan : `claude/plan-bascule-abonnement.md` (projet claude.ai). Les appels à l'API
sont remplacés par une tâche planifiée Claude qui suit la compétence
`.claude/skills/gazette/SKILL.md` :

1. `python main.py journal-agent avancer <dossier>` : collecte, textes complets,
   puis dépôt des demandes à l'IA dans `<dossier>/a_faire/` (mêmes consignes que l'API) ;
   code 3 tant qu'il manque des réponses, code 0 quand l'édition est prête.
2. Des sous-agents (Haiku pour le tri et les brèves, Sonnet pour les articles)
   écrivent les réponses dans `<dossier>/faits/` ; `journal-agent verifier` les contrôle.
3. Le dossier est poussé sur la branche `claude/editions` ; le workflow `publier`
   de cette branche lance `journal-agent publier <dossier> --envoyer` (mise en page,
   mémoire sur `journal-etat`, e-mail Resend).

Une réponse manquante ne bloque pas l'édition : la section ou l'article absent est
signalé en tête de l'e-mail (« Édition incomplète »). En cas d'échec complet, relance
à la main de l'édition par l'API (§ 4).
