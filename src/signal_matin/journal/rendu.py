"""Mise en page HTML A4 de l'edition (reprend la maquette validee)."""
from __future__ import annotations

import datetime as dt
from html import escape as E
from pathlib import Path

ASSETS = Path(__file__).resolve().parents[1] / "assets"
CSS_JOURNAL = Path(__file__).with_name("journal.css")

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août",
        "septembre", "octobre", "novembre", "décembre"]
MOIS_COURTS = ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août",
               "sept.", "oct.", "nov.", "déc."]
JOURS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]


def date_longue(jour: dt.date) -> str:
    return f"{JOURS[jour.weekday()]} {jour.day} {MOIS[jour.month - 1]} {jour.year}"


def date_courte(valeur: str | None) -> str:
    if not valeur:
        return ""
    try:
        d = dt.date.fromisoformat(valeur[:10])
    except ValueError:
        return ""
    return f"{d.day} {MOIS_COURTS[d.month - 1]}"


def _nombre(valeur: float) -> str:
    return f"{valeur:g}".replace(".", ",")


# ------------------------------------------------------------------------ Une


def _masthead(edition: dict) -> str:
    jour = dt.date.fromisoformat(edition["date"])
    statut = "Édition de secours" if edition.get("secours") else "Édition du matin"
    return f"""<header class="masthead">
<div class="masthead-overline"><span>Le quotidien personnel</span><span>Le journal anti-scroll</span></div>
<h1><span>Signal</span><em>Matin</em></h1>
<p class="masthead-motto">Voir clair avant de voir l'écran.</p>
<div class="edition-meta"><span>N° {edition.get('numero', 1):03d}</span><span style="text-align:center">{E(date_longue(jour).upper())}</span><span style="text-align:right">{E(statut.upper())}</span></div>
</header>"""


def _meteo(meteo: dict | None) -> str:
    if not meteo:
        return """<div class="meteo"><div class="blk-title"><h2>Météo</h2></div>
<p>Prévision indisponible ce matin.</p></div>"""
    lignes = "".join(
        f"<tr><td>{E(p['libelle'])}</td><td>{E(p['ciel'])}</td>"
        f"<td>{_nombre(p['temp_min']) if p['temp_min'] == p['temp_max'] else _nombre(p['temp_min']) + '–' + _nombre(p['temp_max'])}°</td>"
        f"<td>{p['vent']} <small>({p['rafales']})</small></td><td>{_nombre(p['pluie'])}</td></tr>"
        for p in meteo["plages"])
    return f"""<div class="meteo"><div class="blk-title"><h2>Météo</h2><span>{E(meteo['lieu'])}</span></div>
<div class="temp">{_nombre(meteo['temp_max'])}°<small> / {_nombre(meteo['temp_min'])}°</small></div>
<p>{E(meteo['resume'])}</p>
<table class="wx"><thead><tr><th></th><th>Ciel</th><th>T°</th><th>Vent</th><th>Pluie</th></tr></thead><tbody>{lignes}</tbody></table>
<p class="illus">Vent moyen en km/h (rafales) · pluie en mm · source {E(meteo['source'])}</p></div>"""


def _mots(nouveaux: list[dict]) -> str:
    items = "".join(
        f"""<li><div class="wtop"><strong>{E(m['mot'])}</strong> <em>{E(m.get('nature', ''))}</em></div>
<p>{E(m['definition'])}</p><p class="ex">« {E(m.get('exemple', ''))} »</p></li>"""
        for m in nouveaux)
    return f"""<div><div class="blk-title"><h2>Nouveaux mots</h2></div><ul class="words">{items}</ul></div>"""


def _revisions(revisions: list[dict], reponses_hier: list[dict]) -> str:
    if revisions:
        liste = "<ol class='review'>" + "".join(
            f"<li><strong>{E(m['mot'])}</strong></li>" for m in revisions) + "</ol>"
        consigne = "Écrivez la définition. Réponses dans l'édition de demain."
    else:
        liste = ""
        consigne = "Les révisions commenceront demain, avec les mots appris aujourd'hui."
    hier = ""
    if reponses_hier:
        hier = "<div class='yest'><span class='lab'>Réponses des révisions d'hier</span>" + " · ".join(
            f"<b>{E(m['mot'])}</b> : {E(m['definition'].rstrip('.'))}" for m in reponses_hier) + "</div>"
    return f"""<div><div class="blk-title"><h2>À réviser</h2></div>
<p class="review-note">{consigne}</p>{liste}{hier}</div>"""


def _une(edition: dict) -> str:
    return f"""<div class="une">{_masthead(edition)}
<div class="une-grid">{_meteo(edition.get('meteo'))}{_mots(edition.get('nouveaux_mots', []))}{_revisions(edition.get('revisions', []), edition.get('reponses_hier', []))}</div></div>"""


# -------------------------------------------------------------------- Articles


def _kicker(article: dict) -> str:
    morceaux = [article.get("rubrique", ""), article.get("source", ""), date_courte(article.get("date"))]
    texte = " · ".join(m for m in morceaux if m)
    if article.get("republication"):
        texte += f" ({article['republication']})"
    return texte


def _developpe(article: dict) -> str:
    sections = "".join(
        f"<h4>{E(s.get('intertitre', ''))}</h4><p>{E(s.get('texte', ''))}</p>"
        for s in article.get("sections", []))
    synthese = ""
    if article.get("synthese"):
        synthese = f"<div class='synth'><span>Synthèse</span><p>{E(article['synthese'])}</p></div>"
    secours = ""
    if article.get("secours"):
        secours = "<p class='secours'>Synthèse indisponible ce matin : chapô du flux d'origine.</p>"
    pied = f"Par {article['auteur']}, {article['source']}" if article.get("auteur") else article.get("source", "")
    return f"""<article class="dev"><p class="kicker">{E(_kicker(article))}</p><h3>{E(article.get('titre', ''))}</h3>
<p class="lead">{E(article.get('chapo', ''))}</p>{sections}{synthese}{secours}<p class="src">{E(pied)}</p></article>"""


def _court(article: dict) -> str:
    sections = "".join(
        f"<h4>{E(s.get('intertitre', ''))}</h4><p>{E(s.get('texte', ''))}</p>"
        for s in article.get("sections", []))
    synthese = ""
    if article.get("synthese"):
        synthese = f"<div class='synth'><span>Synthèse</span><p>{E(article['synthese'])}</p></div>"
    secours = "<p class='secours'>Synthèse indisponible : chapô du flux.</p>" if article.get("secours") else ""
    pied = f"Par {article['auteur']}, {article['source']}" if article.get("auteur") else article.get("source", "")
    return f"""<article class="dev court"><p class="kicker">{E(_kicker(article))}</p><h3>{E(article.get('titre', ''))}</h3>
<p class="lead">{E(article.get('chapo', ''))}</p>{sections}{synthese}{secours}<p class="src">{E(pied)}</p></article>"""


def _breves(breves: list[dict]) -> str:
    return "<div class='breves'>" + "".join(
        f"<div class='breve'><p class='kicker'>{E(_kicker(b))}</p><h5>{E(b.get('titre', ''))}</h5>"
        f"<p>{E(b.get('texte', ''))}</p></div>" for b in breves) + "</div>"


def _entete(bloc: str, premier: bool, precision: str = "") -> str:
    classe = "slot-head" if premier else "slot-head suite"
    titre = E(bloc) if premier else f"{E(bloc)} · suite"
    return f"<div class='{classe}'><h2>{titre}</h2><span>{E(precision)}</span></div>"


# ------------------------------------------------------------------------ Jeux


def _sudoku(grille: list[int]) -> str:
    lignes = "".join("<tr>" + "".join(f"<td>{grille[r * 9 + c] or ''}</td>" for c in range(9)) + "</tr>"
                     for r in range(9))
    return f"<table class='sudoku'>{lignes}</table>"


def _shikaku(jeu: dict) -> str:
    indices = {(r, c): a for r, c, a in jeu["indices"]}
    lignes = "".join("<tr>" + "".join(f"<td>{indices.get((r, c), '')}</td>" for c in range(jeu["largeur"]))
                     + "</tr>" for r in range(jeu["hauteur"]))
    return f"<table class='shikaku'>{lignes}</table>"


def _futoshiki(jeu: dict) -> str:
    n = jeu["n"]
    donnes = {(r, c): v for r, c, v in jeu["donnes"]}
    horizontal, vertical = {}, {}
    for a, b in jeu["signes"]:  # a < b
        a, b = tuple(a), tuple(b)
        if a[0] == b[0]:
            gauche = min(a, b, key=lambda x: x[1])
            horizontal[gauche] = "<" if gauche == a else ">"
        else:
            haut = min(a, b, key=lambda x: x[0])
            vertical[haut] = "∧" if haut == a else "∨"
    lignes = []
    for r in range(n):
        cases = []
        for c in range(n):
            cases.append(f"<td class='fc'>{donnes.get((r, c), '')}</td>")
            if c < n - 1:
                cases.append(f"<td class='fs'>{horizontal.get((r, c), '')}</td>")
        lignes.append("<tr>" + "".join(cases) + "</tr>")
        if r < n - 1:
            cases = []
            for c in range(n):
                cases.append(f"<td class='fs'>{vertical.get((r, c), '')}</td>")
                if c < n - 1:
                    cases.append("<td class='fs'></td>")
            lignes.append("<tr class='fsr'>" + "".join(cases) + "</tr>")
    return f"<table class='futo'>{''.join(lignes)}</table>"


def _quiz(quiz: list[dict]) -> str:
    if not quiz:
        return ""
    items = "".join(
        f"<li><p>{E(q['question'])}</p><p class='opts'>"
        + " ".join(f"<span>{'abc'[i]}) {E(o)}</span>" for i, o in enumerate(q['options'][:3]))
        + "</p></li>" for q in quiz)
    return f"""<div class="quiz"><div class="blk-title" style="border-top:0;padding-top:0"><h2>Quiz du jour</h2><span>Sur les articles de ce numéro</span></div><ol>{items}</ol></div>"""


def page_jeux(edition: dict) -> str:
    jeux = edition["jeux"]
    compte = jeux["compte"]
    return f"""<div class="slot-head"><h2>Jeux</h2><span>Solutions dans l'édition de demain</span></div>
<div class="games">
<div class="game"><h3>Sudoku</h3><p class="rules">Chaque ligne, colonne et carré de 3×3 contient une seule fois les chiffres de 1 à 9.</p>{_sudoku(jeux['sudoku']['grille'])}</div>
<div class="game"><h3>Shikaku</h3><p class="rules">Découpez la grille en rectangles. Chaque rectangle contient un seul chiffre, égal à son nombre de cases.</p>{_shikaku(jeux['shikaku'])}</div>
</div>
<div class="games games2">
<div class="game"><h3>Futoshiki</h3><p class="rules">Placez les chiffres de 1 à 6 une seule fois par ligne et par colonne, en respectant les signes &lt; et &gt; entre les cases.</p>{_futoshiki(jeux['futoshiki'])}</div>
<div class="game"><h3>Le compte est bon</h3><p class="rules">Atteignez le nombre cible avec les 6 plaques et les quatre opérations. Chaque plaque ne sert qu'une fois ; toutes ne sont pas obligatoires.</p>
<div class="target">{compte['cible']}</div><div class="tiles">{''.join(f'<span>{t}</span>' for t in compte['plaques'])}</div><div class="scratch"></div></div>
</div>{_quiz(edition.get('quiz', []))}"""


def solutions_hier(sol: dict | None) -> str:
    if not sol:
        return ""
    blocs = []
    if sol.get("sudoku"):
        s = sol["sudoku"]
        lignes = "".join("<tr>" + "".join(f"<td>{s[r * 9 + c]}</td>" for c in range(9)) + "</tr>" for r in range(9))
        blocs.append(f"<div><span class='lab'>Sudoku</span><table class='ms'>{lignes}</table></div>")
    if sol.get("shikaku"):
        sk = sol["shikaku"]
        proprio = [[0] * sk["largeur"] for _ in range(sk["hauteur"])]
        for k, (r, c, h, w) in enumerate(sk["rectangles"]):
            for dr in range(h):
                for dc in range(w):
                    proprio[r + dr][c + dc] = k
        lignes = []
        for r in range(sk["hauteur"]):
            cases = []
            for c in range(sk["largeur"]):
                k = proprio[r][c]
                bords = []
                if r == 0 or proprio[r - 1][c] != k:
                    bords.append("border-top:.35mm solid #151515")
                if c == 0 or proprio[r][c - 1] != k:
                    bords.append("border-left:.35mm solid #151515")
                if r == sk["hauteur"] - 1 or proprio[r + 1][c] != k:
                    bords.append("border-bottom:.35mm solid #151515")
                if c == sk["largeur"] - 1 or proprio[r][c + 1] != k:
                    bords.append("border-right:.35mm solid #151515")
                cases.append(f"<td style='{';'.join(bords)}'></td>")
            lignes.append("<tr>" + "".join(cases) + "</tr>")
        blocs.append(f"<div><span class='lab'>Shikaku</span><table class='msk'>{''.join(lignes)}</table></div>")
    if sol.get("futoshiki"):
        f = sol["futoshiki"]
        lignes = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in ligne) + "</tr>" for ligne in f)
        blocs.append(f"<div><span class='lab'>Futoshiki</span><table class='ms'>{lignes}</table></div>")
    texte = []
    if sol.get("compte"):
        texte.append("<span class='lab'>Le compte est bon</span>" + " ; ".join(E(e) for e in sol["compte"]))
    if sol.get("quiz"):
        texte.append("<span class='lab' style='margin-top:2mm'>Quiz</span><ol>" + "".join(
            f"<li>{E(q)}</li>" for q in sol["quiz"]) + "</ol>")
    blocs.append("<div>" + "".join(f"<p>{t}</p>" for t in texte) + "</div>")
    return f"<div class='sol'><h3>Solutions d'hier</h3><div class='sol-grid'>{''.join(blocs)}</div></div>"


# ---------------------------------------------------------------------- Pages


AJUSTEMENT = """<script>
// Reduit legerement le corps d'un article qui deborderait de sa demi-page.
document.querySelectorAll('.quart, .corps:not(:has(.quarts))').forEach(function (zone) {
  var taille = 8.85;
  var deborde = function () { return zone.scrollHeight > zone.clientHeight + 1 || zone.scrollWidth > zone.clientWidth + 1; };
  while (deborde() && taille > 7.6) { taille -= 0.15; zone.style.fontSize = taille + 'pt'; }
  // Demi-page de breves encore trop pleine : on retire la derniere breve.
  var breves = zone.querySelectorAll('.breve');
  for (var i = breves.length - 1; deborde() && i > 0; i--) { breves[i].remove(); }
  if (deborde()) { zone.dataset.deborde = 'oui'; }
});
</script>"""


def _feuille(contenu: str, numero: int) -> str:
    return (f"<section class='sheet'><div class='page-content colonne'>{contenu}</div>"
            f"<footer class='pfoot'><span>Signal Matin · Le journal anti-scroll</span><span>{numero}</span></footer></section>")


def _slot(entete: str, corps: str, fixe: str = "") -> str:
    style = f" style='flex:0 0 {fixe}'" if fixe else ""
    return f"<div class='slot'{style}>{entete}<div class='corps'>{corps}</div></div>"


def _unite(unite: dict, edition: dict, deja_vus: set[str]) -> tuple[str, str]:
    """Retourne (bloc, html) d'une unite de contenu."""
    if unite["type"] == "article":
        article = unite["article"]
        corps = _developpe(article) if unite["taille"] == 2 else _court(article)
        return unite["bloc"], corps
    if unite["type"] == "breves":
        titre = edition.get("titres_blocs", {}).get(unite["bloc"], "")
        return unite["bloc"], f"<p class='breves-bloc'>En bref · {E(titre)}</p>{_breves(unite['breves'])}"
    return "", solutions_hier(edition.get("solutions_hier"))


def demi_pages(edition: dict) -> list[tuple[str, str]]:
    """Demi-pages (entete, corps) a partir de la sequence d'unites planifiee."""
    from .mise_en_page import assembler

    titres = edition.get("titres_blocs", {})
    deja_vus: set[str] = set()
    demis: list[tuple[str, str]] = []
    for groupe in assembler(edition.get("sequence", [])):
        rendus = [_unite(u, edition, deja_vus) for u in groupe]
        blocs = [b for b, _ in rendus if b]
        entete = ""
        if blocs:
            bloc = blocs[0]
            nouveaux = [b for b in dict.fromkeys(blocs) if b not in deja_vus]
            if bloc not in deja_vus:
                entete = _entete(titres.get(bloc, ""), True,
                                 " · ".join(titres.get(b, "") for b in nouveaux[1:]))
            else:
                autres = [titres.get(b, "") for b in dict.fromkeys(blocs)]
                entete = _entete(" · ".join(autres), False)
            deja_vus.update(blocs)
        if len(rendus) == 1:
            corps = rendus[0][1]
        else:
            corps = "<div class='quarts'>" + "".join(f"<div class='quart'>{h}</div>" for _, h in rendus) + "</div>"
        demis.append((entete, corps))
    return demis


def rendre(edition: dict) -> str:
    css = (ASSETS / "signal_matin.css").read_text(encoding="utf-8") + "\n" + CSS_JOURNAL.read_text(encoding="utf-8")
    demis = demi_pages(edition)
    pages = []
    # Page 1 : la une (demi-page) puis la premiere demi-page de contenu.
    premier = demis.pop(0) if demis else ("", "")
    pages.append(_feuille(f"<div class='slot' style='flex:0 0 115mm'>{_une(edition)}</div>" + _slot(*premier), 1))
    if len(demis) % 2 == 1:
        demis.append(("", ""))
    for i in range(0, len(demis), 2):
        pages.append(_feuille(_slot(*demis[i]) + _slot(*demis[i + 1]), len(pages) + 1))
    jeux = page_jeux(edition)
    pages.append(_feuille(jeux, len(pages) + 1))
    jour = dt.date.fromisoformat(edition["date"])
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Signal Matin · {E(date_longue(jour))}</title><style>{css}</style></head>
<body><main class="publication">{''.join(pages)}</main>{AJUSTEMENT}</body></html>"""
