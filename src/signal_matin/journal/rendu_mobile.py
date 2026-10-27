"""Version numerique de l'edition : une colonne, lisible sur telephone et dans un e-mail.

Meme contenu que le PDF (une, blocs, jeux, quiz, solutions d'hier), sans la
pagination A4. Le style est volontairement simple (une seule feuille <style>,
pas de script, pas de police externe) pour passer dans les clients de messagerie.
"""
from __future__ import annotations

import datetime as dt
from html import escape as E

from .rendu import _futoshiki, _kicker, _nombre, _shikaku, _sudoku, date_longue

CSS = """
body{margin:0;padding:0;background:#f4f1ea;color:#151515;-webkit-text-size-adjust:100%}
.page{max-width:640px;margin:0 auto;background:#fffdf8;padding:18px 16px 28px;
 font-family:Georgia,'Times New Roman',serif;font-size:17px;line-height:1.5}
.mast{text-align:center;border-bottom:3px double #151515;padding-bottom:10px;margin-bottom:6px}
.mast .over{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase;color:#555}
.mast h1{font-size:40px;line-height:1.05;margin:6px 0 2px;font-weight:700;letter-spacing:-.01em}
.mast h1 em{font-weight:400}
.mast .motto{font-style:italic;font-size:14px;margin:0;color:#444}
.meta{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.08em;text-transform:uppercase;
 text-align:center;color:#333;padding:6px 0;border-bottom:1px solid #151515;margin-bottom:14px}
.sommaire{font-family:Arial,Helvetica,sans-serif;font-size:13px;margin:0 0 18px;padding:0;list-style:none}
.sommaire li{display:inline-block;margin:0 10px 6px 0}
.sommaire a{color:#151515}
h2.bloc{font-family:Arial,Helvetica,sans-serif;font-size:13px;letter-spacing:.14em;text-transform:uppercase;
 border-top:3px solid #151515;padding-top:6px;margin:30px 0 12px}
h2.bloc span{font-weight:400;color:#666;letter-spacing:.06em}
.kicker{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.08em;text-transform:uppercase;color:#666;margin:0 0 4px}
article{border-bottom:1px solid #cfc9bd;padding-bottom:16px;margin-bottom:18px}
article h3{font-size:24px;line-height:1.2;margin:0 0 8px}
article.court h3{font-size:20px}
.lead{font-style:italic;margin:0 0 10px}
h4{font-family:Arial,Helvetica,sans-serif;font-size:14px;margin:14px 0 4px}
p{margin:0 0 10px}
.synth{background:#efebe1;border-left:4px solid #151515;padding:8px 12px;margin:12px 0}
.synth b{font-family:Arial,Helvetica,sans-serif;font-size:11px;letter-spacing:.12em;text-transform:uppercase;display:block;margin-bottom:2px}
.synth p{margin:0}
.src{font-size:14px;color:#555;margin:6px 0 0}
.src a{color:#555}
.secours{font-size:13px;color:#8a3b12}
.breve{border-top:1px solid #cfc9bd;padding-top:8px;margin-top:8px}
.breve h5{font-size:17px;margin:0 0 3px}
.breve p{margin:0}
.encadre{border:1px solid #151515;padding:10px 12px;margin:0 0 14px}
.temp{font-size:30px;font-weight:700}
.temp small{font-size:18px;font-weight:400;color:#555}
table.wx{border-collapse:collapse;width:100%;font-family:Arial,Helvetica,sans-serif;font-size:13px;margin-top:6px}
table.wx th,table.wx td{border-bottom:1px solid #ddd6c8;padding:4px 3px;text-align:left}
.note{font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#666;margin:6px 0 0}
ul.mots{list-style:none;padding:0;margin:0}
ul.mots li{margin:0 0 12px}
ul.mots em{color:#555;font-size:15px}
.ex{font-style:italic;color:#444}
ol.revisions{margin:0;padding-left:22px}
ol.revisions li{margin-bottom:4px}
details{margin-top:8px;font-size:15px}
summary{cursor:pointer;font-family:Arial,Helvetica,sans-serif;font-size:13px;text-decoration:underline}
.jeu{margin:0 0 22px}
.jeu h3{font-size:20px;margin:0 0 4px}
.regle{font-size:14px;color:#444}
table.sudoku,table.shikaku,table.ms{border-collapse:collapse;margin:6px 0;font-family:Arial,Helvetica,sans-serif}
table.sudoku td,table.ms td{width:30px;height:30px;text-align:center;border:1px solid #999;font-size:17px;font-weight:700;padding:0}
table.sudoku tr:nth-child(3n) td,table.ms.s9 tr:nth-child(3n) td{border-bottom:2px solid #151515}
table.sudoku td:nth-child(3n),table.ms.s9 td:nth-child(3n){border-right:2px solid #151515}
table.sudoku,table.ms.s9{border:2px solid #151515}
table.shikaku{border:2px solid #151515}
table.shikaku td{width:28px;height:28px;text-align:center;border:1px dotted #999;font-weight:700;padding:0}
table.futo{border-collapse:collapse;margin:6px 0;font-family:Arial,Helvetica,sans-serif}
table.futo td.fc{width:34px;height:34px;border:1.5px solid #151515;text-align:center;font-weight:700;font-size:17px}
table.futo td.fs{width:16px;height:16px;text-align:center;font-size:14px}
.cible{font-size:34px;font-weight:700;border:2px solid #151515;display:inline-block;padding:2px 14px;margin:4px 0 8px}
.plaques span{display:inline-block;border:1px solid #151515;min-width:32px;text-align:center;padding:3px 4px;margin:0 4px 4px 0;font-weight:700}
.quiz li{margin-bottom:10px}
.opts{font-size:15px;color:#333}
.pied{font-family:Arial,Helvetica,sans-serif;font-size:12px;color:#777;text-align:center;border-top:1px solid #151515;padding-top:8px;margin-top:30px}
"""


def _meteo(meteo: dict | None) -> str:
    if not meteo:
        return "<div class='encadre'><b>Météo</b><p>Prévision indisponible ce matin.</p></div>"
    lignes = "".join(
        f"<tr><td>{E(p['libelle'])}</td><td>{E(p['ciel'])}</td>"
        f"<td>{_nombre(p['temp_min']) if p['temp_min'] == p['temp_max'] else _nombre(p['temp_min']) + '–' + _nombre(p['temp_max'])}°</td>"
        f"<td>{p['vent']} ({p['rafales']})</td><td>{_nombre(p['pluie'])}</td></tr>"
        for p in meteo.get("plages", []))
    return (f"<div class='encadre'><p class='kicker'>Météo · {E(meteo['lieu'])}</p>"
            f"<div class='temp'>{_nombre(meteo['temp_max'])}°<small> / {_nombre(meteo['temp_min'])}°</small></div>"
            f"<p>{E(meteo['resume'])}</p>"
            f"<table class='wx'><tr><th></th><th>Ciel</th><th>T°</th><th>Vent</th><th>Pluie</th></tr>{lignes}</table>"
            f"<p class='note'>Vent moyen en km/h (rafales) · pluie en mm · source {E(meteo['source'])}</p></div>")


def _mots(edition: dict) -> str:
    nouveaux = "".join(
        f"<li><b>{E(m['mot'])}</b> <em>{E(m.get('nature', ''))}</em><br>{E(m['definition'])}"
        f"<br><span class='ex'>« {E(m.get('exemple', ''))} »</span></li>"
        for m in edition.get("nouveaux_mots", []))
    html = f"<div class='encadre'><p class='kicker'>Nouveaux mots</p><ul class='mots'>{nouveaux}</ul></div>"
    revisions = edition.get("revisions", [])
    if revisions:
        liste = "".join(f"<li><b>{E(m['mot'])}</b></li>" for m in revisions)
        corps = (f"<p class='regle'>Retrouvez la définition de tête. Réponses dans l'édition de demain.</p>"
                 f"<ol class='revisions'>{liste}</ol>")
    else:
        corps = "<p class='regle'>Les révisions commenceront demain, avec les mots appris aujourd'hui.</p>"
    hier = edition.get("reponses_hier", [])
    if hier:
        corps += ("<details><summary>Réponses des révisions d'hier</summary><p>" + "<br>".join(
            f"<b>{E(m['mot'])}</b> : {E(m['definition'])}" for m in hier) + "</p></details>")
    return html + f"<div class='encadre'><p class='kicker'>À réviser</p>{corps}</div>"


def _pied(article: dict) -> str:
    texte = f"Par {article['auteur']}, {article['source']}" if article.get("auteur") else article.get("source", "")
    if article.get("url"):
        return f"<p class='src'>{E(texte)} · <a href='{E(article['url'], quote=True)}'>lire l'original</a></p>"
    return f"<p class='src'>{E(texte)}</p>"


def _article(article: dict) -> str:
    classe = "court" if article.get("format") == "court" else "long"
    sections = "".join(f"<h4>{E(s.get('intertitre', ''))}</h4><p>{E(s.get('texte', ''))}</p>"
                       for s in article.get("sections", []))
    synthese = (f"<div class='synth'><b>Synthèse</b><p>{E(article['synthese'])}</p></div>"
                if article.get("synthese") else "")
    secours = ("<p class='secours'>Synthèse indisponible ce matin : chapô du flux d'origine.</p>"
               if article.get("secours") else "")
    return (f"<article class='{classe}'><p class='kicker'>{E(_kicker(article))}</p>"
            f"<h3>{E(article.get('titre', ''))}</h3><p class='lead'>{E(article.get('chapo', ''))}</p>"
            f"{sections}{synthese}{secours}{_pied(article)}</article>")


def _breves(breves: list[dict]) -> str:
    if not breves:
        return ""
    return "<p class='kicker' style='margin-top:6px'>En bref</p>" + "".join(
        f"<div class='breve'><p class='kicker'>{E(_kicker(b))}</p><h5>{E(b.get('titre', ''))}</h5>"
        f"<p>{E(b.get('texte', ''))}</p></div>" for b in breves)


def _blocs(edition: dict) -> tuple[str, str]:
    sommaire, corps = [], []
    for bloc in edition.get("blocs", []):
        if not bloc.get("developpes") and not bloc.get("breves"):
            continue
        ancre = f"bloc-{bloc['id']}"
        sommaire.append(f"<li><a href='#{ancre}'>{E(bloc['titre'])}</a></li>")
        nombre = len(bloc.get("developpes", []))
        detail = f"{nombre} article{'s' if nombre > 1 else ''}"
        if bloc.get("breves"):
            detail += f" · {len(bloc['breves'])} brèves"
        corps.append(f"<h2 class='bloc' id='{ancre}'>{E(bloc['titre'])} <span>· {detail}</span></h2>"
                     + "".join(_article(a) for a in bloc.get("developpes", []))
                     + _breves(bloc.get("breves", [])))
    if not edition.get("numerique"):
        sommaire.append("<li><a href='#jeux'>Jeux</a></li>")
    return "<ul class='sommaire'>" + "".join(sommaire) + "</ul>", "".join(corps)


def _jeux(edition: dict) -> str:
    jeux = edition["jeux"]
    compte = jeux["compte"]
    quiz = ""
    if edition.get("quiz"):
        items = "".join(
            f"<li><p>{E(q['question'])}</p><p class='opts'>"
            + "<br>".join(f"{'abc'[i]}) {E(o)}" for i, o in enumerate(q['options'][:3])) + "</p></li>"
            for q in edition["quiz"])
        quiz = f"<div class='jeu quiz'><h3>Quiz du jour</h3><p class='regle'>Sur les articles de ce numéro.</p><ol>{items}</ol></div>"
    return f"""<h2 class='bloc' id='jeux'>Jeux <span>· solutions dans l'édition de demain</span></h2>
<div class='jeu'><h3>Sudoku</h3><p class='regle'>Chaque ligne, colonne et carré de 3×3 contient une seule fois les chiffres de 1 à 9.</p>{_sudoku(jeux['sudoku']['grille'])}</div>
<div class='jeu'><h3>Shikaku</h3><p class='regle'>Découpez la grille en rectangles. Chaque rectangle contient un seul chiffre, égal à son nombre de cases.</p>{_shikaku(jeux['shikaku'])}</div>
<div class='jeu'><h3>Futoshiki</h3><p class='regle'>Placez les chiffres de 1 à 6 une seule fois par ligne et par colonne, en respectant les signes &lt; et &gt; entre les cases.</p>{_futoshiki(jeux['futoshiki'])}</div>
<div class='jeu'><h3>Le compte est bon</h3><p class='regle'>Atteignez le nombre cible avec les 6 plaques et les quatre opérations. Chaque plaque ne sert qu'une fois ; toutes ne sont pas obligatoires.</p>
<div class='cible'>{compte['cible']}</div><div class='plaques'>{''.join(f'<span>{t}</span>' for t in compte['plaques'])}</div></div>{quiz}"""


def _solutions(sol: dict | None) -> str:
    if not sol:
        return ""
    morceaux = []
    if sol.get("sudoku"):
        s = sol["sudoku"]
        lignes = "".join("<tr>" + "".join(f"<td>{s[r * 9 + c]}</td>" for c in range(9)) + "</tr>" for r in range(9))
        morceaux.append(f"<p class='kicker'>Sudoku</p><table class='ms s9'>{lignes}</table>")
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
                bords = ["border:1px dotted #bbb"]
                if r == 0 or proprio[r - 1][c] != k:
                    bords.append("border-top:2px solid #151515")
                if c == 0 or proprio[r][c - 1] != k:
                    bords.append("border-left:2px solid #151515")
                if r == sk["hauteur"] - 1 or proprio[r + 1][c] != k:
                    bords.append("border-bottom:2px solid #151515")
                if c == sk["largeur"] - 1 or proprio[r][c + 1] != k:
                    bords.append("border-right:2px solid #151515")
                cases.append(f"<td style='width:22px;height:22px;padding:0;{';'.join(bords)}'></td>")
            lignes.append("<tr>" + "".join(cases) + "</tr>")
        morceaux.append(f"<p class='kicker'>Shikaku</p><table style='border-collapse:collapse;margin:6px 0'>{''.join(lignes)}</table>")
    if sol.get("futoshiki"):
        lignes = "".join("<tr>" + "".join(f"<td>{v}</td>" for v in ligne) + "</tr>" for ligne in sol["futoshiki"])
        morceaux.append(f"<p class='kicker'>Futoshiki</p><table class='ms'>{lignes}</table>")
    if sol.get("compte"):
        morceaux.append("<p class='kicker'>Le compte est bon</p><p>" + " ; ".join(E(e) for e in sol["compte"]) + "</p>")
    if sol.get("quiz"):
        morceaux.append("<p class='kicker'>Quiz</p><ol>" + "".join(f"<li>{E(q)}</li>" for q in sol["quiz"]) + "</ol>")
    return ("<h2 class='bloc'>Solutions d'hier</h2><details><summary>Afficher les solutions</summary>"
            + "".join(morceaux) + "</details>")


def rendre_mobile(edition: dict) -> str:
    jour = dt.date.fromisoformat(edition["date"])
    statut = "Édition de secours" if edition.get("secours") else "Édition numérique"
    sommaire, blocs = _blocs(edition)
    if edition.get("numerique"):
        # Lecture sur telephone : ni meteo, ni jeux, ni solutions.
        haut, bas, pied = _mots(edition), "", "Signal Matin · Le journal anti-scroll"
    else:
        haut = _meteo(edition.get("meteo")) + _mots(edition)
        bas = _jeux(edition) + _solutions(edition.get("solutions_hier"))
        pied = "Signal Matin · Le journal anti-scroll · PDF A4 en pièce jointe"
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Signal Matin · {E(date_longue(jour))}</title><style>{CSS}</style></head>
<body><div class="page">
<div class="mast"><div class="over">Le quotidien personnel · Le journal anti-scroll</div>
<h1>Signal <em>Matin</em></h1><p class="motto">Voir clair avant de voir l'écran.</p></div>
<div class="meta">N° {edition.get('numero', 1):03d} · {E(date_longue(jour))} · {E(statut)}</div>
{sommaire}{haut}{blocs}{bas}
<div class="pied">{pied}</div>
</div></body></html>"""
