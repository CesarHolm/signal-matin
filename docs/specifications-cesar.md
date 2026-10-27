# Signal Matin — spécifications

*Dernière mise à jour : 19 octobre 2026 · maquette de référence : `signal-matin-demo.html`*

## 1. Structure du journal (8 pages A4 par défaut, recto verso)

| Bloc | Contenu | Volume | Statut |
|---|---|---|---|
| 0. Une | Titre + météo + mots du jour | ~1/2 page (115 mm) | ✅ Validé |
| 1. IA & recherche | au moins 2 articles + 3 brèves | variable | ✅ Validé |
| 2. Actualité | France, États-Unis, Chine, Monde, géopolitique & défense | ~1,5 page | Sources à définir |
| 3. Veille | Réglementation & conformité, climat | ~1,5 page | Sources à définir |
| 4. Curiosités | Science grand public, sport | ~1,5 page | Sources à définir |
| 5. Jeux | Dernière page | 1 page | ✅ Validé |

Rubriques retirées : agenda, priorités, à ne pas oublier.

## 2. Une

### Météo
- Source : Meteociel, Issy-les-Moulineaux (92130) — https://www.meteociel.fr/previsions/33205/issy_les_moulineaux.htm (pas de 3 h, modèle GFS)
- Affichage : températures min / max, résumé du jour en une phrase, tableau par plage **8h-12h · 12h-14h · 14h-18h · 18h-22h** (ciel, température, vent moyen et rafales en km/h, pluie en mm)

### Mots du jour
- **5 nouveaux mots** : 2 faciles, 1 intermédiaire, 2 difficiles. Affichage : mot, nature grammaticale, définition, exemple. **Aucune mention du niveau.**
- **5 mots à réviser**, tirés au hasard parmi les mots déjà appris : le mot seul, avec de l'espace pour écrire la définition au stylo
- Zone « À réviser » à agrandir légèrement (plus de place pour écrire)
- **Réponses des révisions de la veille** en petit caractères, sous la liste
- Domaines : environ 80 % français soutenu / littéraire, 20 % vocabulaire professionnel (économie, droit, tech)
- Base de mots : approche hybride (base initiale générée une fois + agent qui réalimente sans doublons)

## 3. Bloc IA & recherche — sources

| Source | Langue | Flux |
|---|---|---|
| MIT Technology Review – IA | EN | https://www.technologyreview.com/topic/artificial-intelligence/feed |
| ActuIA | FR | https://www.actuia.com/feed/ |
| TechCrunch – IA | EN | https://techcrunch.com/category/artificial-intelligence/feed/ |
| OpenAI (officiel) | EN | https://openai.com/news/rss.xml |
| Quanta Magazine | EN | https://www.quantamagazine.org/feed/ |
| The Conversation France | FR | https://theconversation.com/fr/articles.atom |
| CNRS Le journal | FR | https://lejournal.cnrs.fr/rss |
| VoxEU (CEPR) | EN | https://cepr.org/rss/vox-content |
| Aeon | EN | https://aeon.co/feed.rss |
| Our World in Data | EN | https://ourworldindata.org/atom.xml |

## 3 bis. Blocs 2 à 4 — sources retenues

✅ vérifié · ⏳ non vérifiable par l'outil de Claude, à confirmer au premier test · ⚠️ problème à corriger

| Bloc | Rubrique | Source | Langue | Statut |
|---|---|---|---|---|
| Actualité | France | Le Monde — https://www.lemonde.fr/rss/une.xml | FR | ✅ |
| Actualité | France | franceinfo — https://www.francetvinfo.fr/titres.rss | FR | ✅ |
| Actualité | France | Public Sénat — https://www.publicsenat.fr/feed | FR | ✅ |
| Actualité | États-Unis | NPR — https://feeds.npr.org/1001/rss.xml | EN | ✅ |
| Actualité | États-Unis | Politico — https://rss.politico.com/politics-news.xml | EN | ✅ |
| Actualité | Chine | South China Morning Post — https://www.scmp.com/rss/4/feed | EN | ✅ |
| Actualité | Chine | The Diplomat — https://thediplomat.com/feed/ | EN | ✅ |
| Actualité | Monde | Al Jazeera — https://www.aljazeera.com/xml/rss/all.xml | EN | ✅ |
| Actualité | Géopolitique | Le Grand Continent — https://legrandcontinent.eu/fr/feed/ | FR | ✅ |
| Actualité | Géopolitique | Diploweb — https://www.diploweb.com/spip.php?page=backend | FR | ✅ |
| Veille | Conformité | CNIL — https://www.cnil.fr/fr/rss.xml | FR | ✅ |
| Veille | Conformité | EDPB — https://www.edpb.europa.eu/feed/news_en | EN | ✅ |
| Veille | Conformité | AMF — https://www.amf-france.org/fr/flux-rss/display/21 | FR | ✅ |
| Veille | Conformité | ESMA — https://www.esma.europa.eu/rss.xml | EN | ✅ |
| Veille | Conformité | EBA — https://www.eba.europa.eu/rss.xml | EN | ✅ |
| Veille | Climat | Carbon Brief — https://www.carbonbrief.org/feed/ | EN | ✅ |
| Veille | Climat | Inside Climate News — https://insideclimatenews.org/feed/ | EN | ✅ |
| Curiosités | Science | NASA — https://www.nasa.gov/feed/ | EN | ✅ |
| Curiosités | Science | Sciences et Avenir — https://www.sciencesetavenir.fr/rss.xml | FR | ✅ |
| Veille | Conformité | ACPR | FR | ⏳ site inaccessible depuis le cloud, à tester depuis le PC |
| Curiosités | Sport (actualité) | franceinfo Sports — https://www.francetvinfo.fr/sports.rss | FR | ✅ |
| Curiosités | Sport (méthodes) | TrainingPeaks — https://www.trainingpeaks.com/feed/ | EN | ✅ |
| Curiosités | Sport (méthodes) | Stronger by Science — https://www.strongerbyscience.com/feed/ | EN | ✅ |

**Règle sport** : actualité en **brèves uniquement** (savoir ce qui s'est passé), **football exclu systématiquement** ; les articles sur les **méthodes d'entraînement** sont traités en **article développé**.

Test réel du 19/10/2026 : 29 flux sur 29 lus par le programme.

## 4. Formats rédactionnels (s'appliquent à tous les blocs)

### Deux gabarits d'article, choisis selon la longueur du texte source
- **Long** (une demi-page) : si 40 % du texte source atteint au moins 2 400 caractères ; synthèse de **2 800 caractères maximum**. Structure : rubrique · source · date → titre → chapô en italique → 3 à 5 intertitres en gras adaptés au type d'article → encadré **« Synthèse »** de 2 phrases → « Par [auteur], [média] ».
- **Court** (un quart de page) : tous les autres ; environ **1 100 caractères maximum** (700 au minimum, jamais plus de 70 % d'un texte bref). Structure : titre → chapô → 1 ou 2 intertitres donnant les **informations clés** (faits, chiffres, acteurs, enjeu) → **« Synthèse »** d'une ou deux phrases maximum.
- Un article dont on ne récupère pas au moins 1 000 caractères de texte ne peut faire qu'une brève.
- Aucune information extérieure à l'article ; republication signalée dans la ligne de source.

### Brève
- Rubrique · source · date → titre traduit en français → 1 à 2 phrases (environ 250 caractères) ; 3 brèves par quart de page. Un article développé n'apparaît jamais aussi en brève.

### Sélection et remplissage
- L'IA classe jusqu'à 6 articles par bloc (score de 1 à 10, 9-10 = essentiel) et jusqu'à 6 brèves, par **importance et nouveauté** ; les republications ne comptent pas comme nouvelles.
- **8 pages par défaut** ; **6** si l'actualité ne suffit pas à remplir, **10** si les sujets essentiels dépassent 8 pages.
- Remplissage exact en quarts de page : chaque bloc garde **au moins 2 articles**, puis les meilleurs scores tous blocs confondus ; un quart orphelin est comblé par un article court ou des brèves supplémentaires.
- L'ordre des articles peut varier pour que chaque demi-page soit pleine (deux articles courts, éventuellement de blocs différents, partagent une demi-page).
- Fraîcheur : articles des **dernières 24 h** du mardi au vendredi ; l'édition du **lundi** couvre vendredi, samedi et dimanche.
- **Football exclu dans tous les blocs** (filtre par mots-clés avant l'IA, puis consigne à l'IA).

## 5. Jeux (dernière page)

- **Sudoku** niveau difficile : 26 à 29 chiffres donnés, solution unique, non résoluble avec les seules techniques simples
- **Shikaku** 10×10, solution unique
- **Futoshiki** 6×6, solution unique
- **Le compte est bon** : 6 plaques, cible entre 101 et 999, au moins 4 opérations dont une multiplication
- **Quiz du jour** : 5 questions à choix multiples sur les articles du numéro
- Aucune mention de difficulté ; **solutions dans l'édition du lendemain**

## 6. Exploitation

- Parution : **du lundi au vendredi**
- Génération : réveil du PC à **4 h** (traitement de nuit, -50 %) ; journal prêt et imprimé à **7 h**
- Sortie : **impression recto verso** sur Brother MFC-L2750DW (laser monochrome, recto verso automatique, Wi-Fi, pas d'impression par e-mail)
- Code : **fork GitHub** sur le compte de Cesar
- Exécution : **PC Windows** de Cesar

### Mode numérique (voyage, validé le 27/10/2026)
- Génération dans le cloud **GitHub Actions** à 4 h 07 (Paris), lundi-vendredi, sans PC
- Envoi **par e-mail** : version HTML une colonne pour téléphone dans le corps du message, PDF A4 et page HTML en pièces jointes
- Bascule en appels directs à 5 h 20 (Paris) pour une réception avant 7 h, heure grecque
- Mémoire du journal sur la branche `journal-etat` ; procédure : `docs/MODE-NUMERIQUE.md`

### Répartition IA (API Anthropic)
- Récupération des flux et des articles complets : programme Python, sans coût d'API
- **Claude Haiku 5.5** : tri et classement des articles, brèves, quiz, mots du jour
- **Claude Sonnet 5.5** : les 8 synthèses développées, à partir de l'article complet
- **Traitement différé de nuit** (Batch API, -50 %) et **mise en cache des consignes**
- Budget estimé : environ 1,5 à 2 $ par mois ; plafond conseillé sur la clé : 15 $ par mois

## 7. Mise en page

- Enchaînement : une + 1re demi-page · puis les blocs dans l'ordre, chaque demi-page contenant un article long ou deux quarts (article court, brèves d'un bloc, solutions d'hier) · page Jeux en dernier
- Ajustement automatique : un texte trop long voit sa taille réduite légèrement (jusqu'à 7,6 pt) ; une brève en trop est retirée

- Typographie et style du projet d'origine (journal monochrome A4)
- Pas de libellé « article développé » dans les en-têtes de section
