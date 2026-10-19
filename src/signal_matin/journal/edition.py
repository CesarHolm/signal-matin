"""Orchestration de l'edition personnalisee.

Etapes (lancees a 4 h par la tache planifiee) :
1. meteo, mots du jour, jeux (local, sans IA) ;
2. collecte des flux par bloc ;
3. lot 1 (Haiku) : tri de chaque bloc + breves ; realimentation des mots si besoin ;
4. recuperation du texte complet des 8 articles retenus ;
5. lot 2 (Sonnet) : les 8 syntheses ;
6. quiz (Haiku, appel direct) ;
7. mise en page HTML -> PDF et memorisation de l'edition (reponses du lendemain).
Toute etape IA en echec bascule sur le mode secours, le journal sort quand meme.
"""
from __future__ import annotations

import datetime as dt
import json
import re
from dataclasses import asdict
from pathlib import Path

from ..config import ROOT
from . import articles as art
from . import ia
from .etat import DOSSIER, articles_deja_publies, edition_precedente, enregistrer_edition, editions_passees
from .jeux import jeux_du_jour
from .meteo import meteo_du_jour
from .rendu import rendre
from .vocabulaire import ajouter_mots, charger_base, niveaux_a_realimenter, selection_du_jour

FOOTBALL = re.compile(
    r"\b(football\w*|foot\b|soccer|ligue 1|ligue 2|ligue des champions|champions league|ligue europa|"
    r"europa league|coupe de france|premier league|la liga|liga\b|serie a|bundesliga|uefa|fifa|"
    r"mercato|psg|paris saint-germain|ballon d'or|olympique (de marseille|lyonnais)|real madrid|"
    r"barcelon\w*|barça|bar[cç]a\b|clasico|atl[ée]tico|chelsea|arsenal|liverpool|tottenham|"
    r"manchester (united|city)|juventus|inter milan|ac milan|bayern|dortmund|mbapp\w*|messi|"
    r"ronaldo|haaland|deschamps|coupe du monde de football|world cup qualif\w*)", re.I)


def _rubrique_sport(candidat: art.Candidat) -> bool:
    return "sport" in candidat.rubrique.casefold()


def _filtrer(blocs: list[art.Bloc]) -> None:
    for bloc in blocs:
        bloc.candidats = [
            c for c in bloc.candidats
            if not (c.nature == "actu" and FOOTBALL.search(f"{c.titre} {c.resume}"))
        ]


def _auteur(candidat: art.Candidat) -> str:
    auteur = (candidat.auteur or "").strip()
    simple = re.sub(r"[^a-z]", "", auteur.casefold())
    source = re.sub(r"[^a-z]", "", candidat.source.casefold())
    if not simple or simple in source or source in simple or len(auteur) > 80:
        return ""
    return auteur


def _vue_article(candidat: art.Candidat) -> dict:
    return {
        "rubrique": candidat.rubrique, "source": candidat.source,
        "date": candidat.publie_le.date().isoformat() if candidat.publie_le else None,
        "url": candidat.url, "auteur": _auteur(candidat),
    }


def _secours_tri(bloc: art.Bloc) -> tuple[list[art.Candidat], list[dict]]:
    """Sans IA : les plus recents, en alternant les sources, methodes sport en priorite."""
    def recence(c):
        return c.publie_le or dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    tries = sorted(bloc.candidats, key=recence, reverse=True)
    methodes = [c for c in tries if c.nature == "methode"]
    eligibles = [c for c in tries if not (_rubrique_sport(c) and c.nature == "actu")]
    developpes: list[art.Candidat] = []
    sources_vues: set[str] = set()
    for c in methodes[:1] + eligibles:
        if c not in developpes and (c.source not in sources_vues or len(developpes) >= 1):
            developpes.append(c)
            sources_vues.add(c.source)
        if len(developpes) == 2:
            break
    reste = [c for c in tries if c not in developpes]
    breves = []
    for c in reste[:3]:
        breves.append({"id": c.id, "titre": _couper(c.titre, 100), "texte": _couper(c.resume, 230)})
    return developpes, breves


def _couper(texte: str, limite: int) -> str:
    if len(texte) <= limite:
        return texte
    return texte[: limite - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def _developpe_secours(candidat: art.Candidat) -> dict:
    chapo = candidat.resume if len(candidat.resume) <= 900 else candidat.resume[:900].rsplit(" ", 1)[0] + "…"
    return {**_vue_article(candidat), "titre": candidat.titre, "chapo": chapo,
            "sections": [], "synthese": "", "secours": True}


def produire(config: dict, maintenant: dt.datetime | None = None, *, avec_ia: bool = True,
             racine: Path = DOSSIER, journal=print) -> dict:
    maintenant = maintenant or dt.datetime.now().astimezone()
    jour = maintenant.date()
    conf = config.get("journal", {})
    avertissements: list[str] = []

    # Heure limite au-dela de laquelle on abandonne le traitement differe.
    limite = dt.time.fromisoformat(conf.get("heure_limite", "06:40"))
    echeance = dt.datetime.combine(jour, limite, tzinfo=maintenant.tzinfo)
    if echeance <= maintenant:
        echeance = maintenant + dt.timedelta(minutes=20)

    precedente = edition_precedente(jour, racine)
    journal("· Météo")
    meteo = meteo_du_jour(conf.get("meteo", {}), jour)
    journal("· Mots du jour")
    nouveaux_mots, revisions = selection_du_jour(jour, racine)
    journal("· Jeux")
    jeux = jeux_du_jour(jour)
    journal("· Collecte des flux")
    deja = articles_deja_publies(jour, racine)
    blocs, erreurs = art.collecter(conf, maintenant, deja)
    _filtrer(blocs)
    if erreurs:
        avertissements.append("Flux indisponibles : " + ", ".join(erreurs))
    journal(f"  {sum(len(b.candidats) for b in blocs)} articles candidats, {len(erreurs)} flux en erreur")

    client = None
    if avec_ia:
        try:
            client = ia.ClientIA(conf.get("ia", {}), journal=journal)
        except ia.IAIndisponible as erreur:
            avertissements.append(f"IA indisponible ({erreur}) : édition de secours")
            journal(f"  ! {erreur}")

    # ---------------------------------------------------------------- Lot 1
    choix: dict[str, tuple[list[art.Candidat], list[dict]]] = {}
    besoins_mots = niveaux_a_realimenter(jour, racine)
    if client:
        journal("· Lot 1 : tri des blocs (Haiku)")
        titres_recents = [t for e in editions_passees(jour, racine)[-5:] for t in e.get("titres", [])]
        requetes = [ia.requete_tri(client, b, titres_recents) for b in blocs if b.candidats]
        if besoins_mots:
            connus = [m["mot"] for m in charger_base(racine)]
            requetes.append(ia.requete_mots(client, besoins_mots, connus))
        reponses = client.lot(requetes, echeance)
        for bloc in blocs:
            texte = reponses.get(f"tri-{bloc.id}")
            if not texte:
                continue
            try:
                data = ia.extraire_json(texte)
                index = {c.id: c for c in bloc.candidats}
                developpes = [index[d["id"]] for d in data.get("developpes", []) if d.get("id") in index][:2]
                breves = [b for b in data.get("breves", []) if b.get("id") in index][:3]
                if developpes:
                    choix[bloc.id] = (developpes, breves)
            except (ValueError, KeyError, TypeError) as erreur:
                journal(f"  ! tri {bloc.id} illisible : {erreur}")
        if "mots" in reponses:
            try:
                ajout = ajouter_mots(ia.extraire_json(reponses["mots"]).get("mots", []), racine)
                journal(f"  {ajout} mots ajoutés à la base")
            except ValueError:
                journal("  ! réponse vocabulaire illisible")
    for bloc in blocs:
        if bloc.id not in choix:
            choix[bloc.id] = _secours_tri(bloc)

    # ------------------------------------------------- Texte integral + lot 2
    journal("· Récupération des articles complets")
    a_developper = [c for d, _ in choix.values() for c in d]
    for candidat in a_developper:
        candidat.texte, candidat.auteur = art.texte_integral(candidat.url, candidat.resume)
    syntheses: dict[str, dict] = {}
    if client and a_developper:
        journal("· Lot 2 : synthèses (Sonnet)")
        plafond = int(conf.get("longueur_max", 2800))
        ratio = float(conf.get("ratio_article_court", 0.40))
        limites = {c.id: ia.limite_caracteres(c.texte, plafond, ratio) for c in a_developper}
        reponses = client.lot([ia.requete_synthese(client, c, limites[c.id]) for c in a_developper], echeance)
        for candidat in a_developper:
            texte = reponses.get(f"syn-{candidat.id}")
            if not texte:
                continue
            try:
                data = ia.ajuster_longueur(ia.extraire_json(texte), limites[candidat.id])
                if data.get("titre") and data.get("sections"):
                    syntheses[candidat.id] = data
            except ValueError as erreur:
                journal(f"  ! synthèse {candidat.id} illisible : {erreur}")

    # --------------------------------------------------------------- Edition
    vue_blocs = []
    for bloc in blocs:
        developpes, breves = choix[bloc.id]
        index = {c.id: c for c in bloc.candidats}
        vues_dev = []
        for c in developpes:
            if c.id in syntheses:
                s = syntheses[c.id]
                vues_dev.append({**_vue_article(c), "titre": s["titre"], "chapo": s.get("chapo", ""),
                                 "sections": s["sections"], "synthese": s.get("synthese", ""),
                                 "republication": s.get("republication", "")})
            else:
                vues_dev.append(_developpe_secours(c))
        vues_breves = [{**_vue_article(index[b["id"]]), "titre": _couper(b.get("titre", ""), 110), "texte": _couper(b.get("texte", ""), 320)}
                       for b in breves if b.get("id") in index]
        vue_blocs.append({"id": bloc.id, "titre": bloc.titre, "developpes": vues_dev, "breves": vues_breves})

    quiz = []
    if client and syntheses:
        journal("· Quiz (Haiku)")
        textes = []
        for b in vue_blocs:
            for d in b["developpes"]:
                if not d.get("secours"):
                    textes.append({"titre": d["titre"], "texte": " ".join(
                        [d["chapo"]] + [s["texte"] for s in d["sections"]] + [d["synthese"]])})
            for br in b["breves"]:
                textes.append({"titre": br["titre"], "texte": br["texte"]})
        reponse = client.direct([ia.requete_quiz(client, textes)]).get("quiz")
        if reponse:
            try:
                quiz = [q for q in ia.extraire_json(reponse).get("questions", [])
                        if len(q.get("options", [])) >= 3 and isinstance(q.get("reponse"), int)][:5]
            except ValueError:
                journal("  ! quiz illisible")

    secours = not syntheses
    solutions_hier = None
    if precedente:
        sj = precedente.get("solutions", {})
        solutions_hier = {**sj, "quiz": precedente.get("reponses_quiz", [])}
    edition = {
        "date": jour.isoformat(),
        "numero": len(editions_passees(jour, racine)) + 1,
        "secours": secours,
        "meteo": asdict(meteo) if meteo else None,
        "nouveaux_mots": nouveaux_mots,
        "revisions": [{"mot": m["mot"]} for m in revisions],
        "reponses_hier": (precedente or {}).get("revisions", []),
        "blocs": vue_blocs,
        "jeux": jeux.en_dict(),
        "quiz": quiz,
        "solutions_hier": solutions_hier,
        "avertissements": avertissements,
    }

    memoire = {
        "date": jour.isoformat(),
        "nouveaux_mots": nouveaux_mots,
        "revisions": [{"mot": m["mot"], "definition": m["definition"]} for m in revisions],
        "articles": [a["url"] for b in vue_blocs for a in b["developpes"] + b["breves"] if a.get("url")],
        "titres": [a["titre"] for b in vue_blocs for a in b["developpes"]],
        "solutions": {
            "sudoku": jeux.sudoku["solution"],
            "shikaku": {k: jeux.shikaku[k] for k in ("largeur", "hauteur", "rectangles")},
            "futoshiki": jeux.futoshiki["solution"],
            "compte": jeux.compte["solution"],
        },
        "reponses_quiz": [f"{'abc'[q['reponse']]}) {q['options'][q['reponse']]}" for q in quiz],
    }
    return {"edition": edition, "memoire": memoire}


def publier(resultat: dict, *, racine: Path = DOSSIER, sortie: Path = ROOT / "output", memoriser: bool = True,
            journal=print) -> Path:
    """Ecrit le HTML, le PDF et la memoire de l'edition. Retourne le chemin du PDF."""
    from playwright.sync_api import sync_playwright

    edition = resultat["edition"]
    nom = f"{edition['date']}-signal-matin"
    html_path = sortie / "preview" / f"{nom}.html"
    pdf_path = sortie / "pdf" / f"{nom}.pdf"
    json_path = sortie / "data" / f"{nom}.json"
    for chemin in (html_path, pdf_path, json_path):
        chemin.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(rendre(edition), encoding="utf-8")
    json_path.write_text(json.dumps(edition, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    from ..pdf import _launch_browser
    with sync_playwright() as playwright:
        navigateur = _launch_browser(playwright)
        page = navigateur.new_page()
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(300)
        debordements = page.eval_on_selector_all(".corps[data-deborde='oui']", "z => z.length")
        page.pdf(path=str(pdf_path), format="A4", print_background=True,
                 margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        navigateur.close()
    if debordements:
        journal(f"  ! {debordements} zone(s) de texte encore trop longue(s) malgré l'ajustement")
    if memoriser:
        enregistrer_edition(dt.date.fromisoformat(edition["date"]), resultat["memoire"], racine)
    journal(f"✓ PDF : {pdf_path}")
    return pdf_path
