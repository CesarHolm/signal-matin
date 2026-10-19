# Signal Matin — spécifications

*Dernière mise à jour : 18 octobre 2026 · maquette de référence : `signal-matin-demo.html`*

## 1. Structure du journal (7 pages A4, recto verso)

| Bloc | Contenu | Volume | Statut |
|---|---|---|---|
| 0. Une | Titre + météo + mots du jour | ~1/2 page (115 mm) | ✅ Validé |
| 1. IA & recherche | 2 articles développés + 2 à 3 brèves | ~1,25 page | ✅ Validé |
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

### Article développé
- Synthèse rédigée en français par Claude (API Anthropic), à partir de l'article complet
- Longueur : **2 800 caractères maximum** (une demi-page), plafonnée à **40 % de l'article d'origine** pour les articles courts
- Structure : rubrique · source · date → titre → chapô en italique → intertitres en gras adaptés au type d'article (ex. *Le déclencheur · De quoi parle-t-on · Les arguments pour · Les risques · Les contre-arguments*) → encadré **« Synthèse »** de 2 phrases → « Par [auteur], [média] »
- Aucun ajout d'information extérieure à l'article
- Republication signalée dans la ligne de source (ex. « paru initialement en mai 2025 »)
- Mise en page : 2 colonnes, 2 articles par page

### Brève
- Rubrique · source · date → titre traduit en français → 1 à 2 phrases (environ 250 caractères)

### Sélection
- Classement par **importance et nouveauté** ; les republications ne comptent pas comme nouvelles
- Fraîcheur : articles des **dernières 24 h** du mardi au vendredi ; l'édition du **lundi** couvre vendredi, samedi et dimanche
- Par bloc : **2 articles développés + 2 à 3 brèves** ; le reste est ignoré (une demi-page « En bref » contient au plus 6 brèves : elle est partagée par deux blocs consécutifs)
- **Football exclu dans tous les blocs** (filtre par mots-clés avant l'IA, puis consigne à l'IA)

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

### Répartition IA (API Anthropic)
- Récupération des flux et des articles complets : programme Python, sans coût d'API
- **Claude Haiku 5.5** : tri et classement des articles, brèves, quiz, mots du jour
- **Claude Sonnet 5.5** : les 8 synthèses développées, à partir de l'article complet
- **Traitement différé de nuit** (Batch API, -50 %) et **mise en cache des consignes**
- Budget estimé : environ 1,5 à 2 $ par mois ; plafond conseillé sur la clé : 15 $ par mois

## 7. Mise en page

- Enchaînement : une + 1er article · puis 2 demi-pages par bloc · une demi-page « En bref » après chaque paire de blocs · solutions d'hier dans la demi-page libre · page Jeux en dernier
- Ajustement automatique : un texte trop long voit sa taille réduite légèrement (jusqu'à 7,6 pt) ; une brève en trop est retirée

- Typographie et style du projet d'origine (journal monochrome A4)
- Pas de libellé « article développé » dans les en-têtes de section
