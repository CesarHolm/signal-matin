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
from . import mise_en_page as mep
from . import ia
from .etat import DOSSIER, articles_deja_publies, edition_precedente, enregistrer_edition, editions_passees
from .jeux import jeux_du_jour
from .meteo import meteo_du_jour
from .rendu import rendre
from .rendu_mobile import rendre_mobile
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
    # Nettoie les restes de date que l'extraction colle parfois au nom.
    auteur = re.sub(r"\s+(january|february|march|april|may|june|july|august|september|october|"
                    r"november|december|janvier|février|mars|avril|mai|juin|juillet|août|"
                    r"septembre|octobre|novembre|décembre)\b.*$", "", auteur, flags=re.I).strip()
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


def _secours_tri(bloc: art.Bloc) -> tuple[list[tuple[art.Candidat, int]], list[dict]]:
    """Sans IA : les plus recents, en alternant les sources, methodes sport en priorite."""
    def recence(c):
        return c.publie_le or dt.datetime.min.replace(tzinfo=dt.timezone.utc)
    tries = sorted(bloc.candidats, key=recence, reverse=True)
    methodes = [c for c in tries if c.nature == "methode"]
    eligibles = [c for c in tries if not (_rubrique_sport(c) and c.nature == "actu")]
    classement: list[art.Candidat] = []
    for c in methodes[:1] + eligibles:
        if c not in classement:
            classement.append(c)
        if len(classement) == 6:
            break
    reste = [c for c in tries if c not in classement]
    breves = [{"id": c.id, "titre": _couper(c.titre, 100), "texte": _couper(c.resume, 230)} for c in reste[:6]]
    return [(c, 6 - i) for i, c in enumerate(classement)], breves


def _couper(texte: str, limite: int) -> str:
    if len(texte) <= limite:
        return texte
    return texte[: limite - 1].rsplit(" ", 1)[0].rstrip(" ,;:") + "…"


def _developpe_secours(candidat: art.Candidat, format_: str = "long") -> dict:
    chapo = _couper(candidat.resume, 900 if format_ == "long" else 420)
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
    # Version numerique (voyage) : ni meteo ni jeux, donc pas de quiz a generer.
    numerique = bool(conf.get("numerique"))
    meteo = None
    if not numerique:
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
    classements: dict[str, list[tuple[art.Candidat, int]]] = {}
    breves_redigees: dict[str, list[dict]] = {}
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
                classe = []
                for rang, d in enumerate(data.get("developpes", [])):
                    if d.get("id") in index and index[d["id"]] not in [c for c, _ in classe]:
                        score = int(d.get("score", 0)) if str(d.get("score", "")).isdigit() else 6 - rang
                        classe.append((index[d["id"]], max(1, min(10, score))))
                if classe:
                    classements[bloc.id] = classe[:6]
                    breves_redigees[bloc.id] = [b for b in data.get("breves", []) if b.get("id") in index][:6]
            except (ValueError, KeyError, TypeError) as erreur:
                journal(f"  ! tri {bloc.id} illisible : {erreur}")
        if "mots" in reponses:
            try:
                ajout = ajouter_mots(ia.extraire_json(reponses["mots"]).get("mots", []), racine)
                journal(f"  {ajout} mots ajoutés à la base")
            except ValueError:
                journal("  ! réponse vocabulaire illisible")
    for bloc in blocs:
        if bloc.id not in classements:
            classements[bloc.id], breves_redigees[bloc.id] = _secours_tri(bloc)

    # ------------------------------------------- Mesure des textes et plan
    journal("· Récupération des articles complets")
    index_global = {c.id: c for b in blocs for c in b.candidats}
    choix_par_bloc: dict[str, list[mep.Choix]] = {}
    ratio = float(conf.get("ratio_article_court", mep.RATIO))
    for bloc_id, classe in classements.items():
        choix_par_bloc[bloc_id] = []
        for candidat, score in classe:
            candidat.texte, candidat.auteur = art.texte_integral(candidat.url, candidat.resume)
            if client and len(candidat.texte) < mep.TEXTE_MINIMUM:
                # Sans IA, le chapô du flux est affiché tel quel : pas de seuil.
                journal(f"  {candidat.id} écarté des développés : texte trop court ({len(candidat.texte)} car.)")
                continue
            format_, limite_car = mep.gabarit(len(candidat.texte), ratio)
            choix_par_bloc[bloc_id].append(mep.Choix(candidat.id, bloc_id, score, format_, limite_car))
    plan = mep.planifier(
        choix_par_bloc, {b: len(v) for b, v in breves_redigees.items()},
        avec_solutions=precedente is not None,
        pages_defaut=int(conf.get("pages", 8)),
        pages_possibles=tuple(conf.get("pages_possibles", (6, 8, 10))))
    journal(f"  plan : {plan.pages} pages, {len(plan.articles)} articles "
            f"({sum(1 for c in plan.articles if c.format == 'long')} longs)")
    if plan.quarts_libres:
        avertissements.append(f"{plan.quarts_libres} quart(s) de page sans contenu")

    # ---------------------------------------------------------------- Lot 2
    syntheses: dict[str, dict] = {}
    if client and plan.articles:
        journal("· Lot 2 : synthèses (Sonnet)")
        requetes = [ia.requete_synthese(client, index_global[c.id], c.limite, c.format) for c in plan.articles]
        reponses = client.lot(requetes, echeance)
        for choix_ in plan.articles:
            texte = reponses.get(f"syn-{choix_.id}")
            if not texte:
                continue
            try:
                data = ia.ajuster_longueur(ia.extraire_json(texte), choix_.limite)
                if data.get("titre") and data.get("sections"):
                    syntheses[choix_.id] = data
            except ValueError as erreur:
                journal(f"  ! synthèse {choix_.id} illisible : {erreur}")

    # --------------------------------------------------------------- Edition
    titres_blocs = {b.id: b.titre for b in blocs}
    ordre_blocs = [b.id for b in blocs]
    sequence: list[dict] = []
    vue_blocs = []
    for bloc_id in ordre_blocs:
        index = {c.id: c for c in next(b for b in blocs if b.id == bloc_id).candidats}
        articles_bloc = [c for c in plan.articles if c.bloc == bloc_id]
        rang = {c.id: i for i, (c, _) in enumerate(classements.get(bloc_id, []))}
        articles_bloc.sort(key=lambda c: (c.format != "long", rang.get(c.id, 99)))
        vues_dev = []
        for choix_ in articles_bloc:
            c = index[choix_.id]
            if choix_.id in syntheses:
                s_ = syntheses[choix_.id]
                vue = {**_vue_article(c), "titre": s_["titre"], "chapo": s_.get("chapo", ""),
                       "sections": s_["sections"], "synthese": s_.get("synthese", ""),
                       "republication": s_.get("republication", "")}
            else:
                vue = _developpe_secours(c, choix_.format)
            vue["format"] = choix_.format
            vues_dev.append(vue)
            sequence.append({"type": "article", "bloc": bloc_id, "taille": choix_.taille, "article": vue})
        developpes_ids = {c.id for c in plan.articles}
        toutes_breves = [{**_vue_article(index[b["id"]]), "titre": _couper(b.get("titre", ""), 110),
                          "texte": _couper(b.get("texte", ""), 320)}
                         for b in breves_redigees.get(bloc_id, [])
                         if b.get("id") in index and b["id"] not in developpes_ids]
        vues_breves = []
        for k in range(plan.quarts_breves.get(bloc_id, 0)):
            lot_breves = toutes_breves[3 * k: 3 * k + 3]
            if lot_breves:
                vues_breves.extend(lot_breves)
                sequence.append({"type": "breves", "bloc": bloc_id, "taille": 1, "breves": lot_breves})
        vue_blocs.append({"id": bloc_id, "titre": titres_blocs[bloc_id], "developpes": vues_dev,
                          "breves": vues_breves})
    if precedente is not None:
        sequence.append({"type": "solutions", "bloc": "", "taille": 1})

    quiz = []
    if client and syntheses and not numerique:
        journal("· Quiz (Haiku)")
        textes = []
        for b in vue_blocs:
            for d in b["developpes"]:
                if not d.get("secours"):
                    textes.append({"titre": d["titre"], "texte": " ".join(
                        [d["chapo"]] + [s_["texte"] for s_ in d["sections"]] + [d["synthese"]])})
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
        "numerique": numerique,
        "meteo": asdict(meteo) if meteo else None,
        "nouveaux_mots": nouveaux_mots,
        "revisions": [{"mot": m["mot"]} for m in revisions],
        "reponses_hier": (precedente or {}).get("revisions", []),
        "blocs": vue_blocs,
        "titres_blocs": titres_blocs,
        "pages": plan.pages,
        "sequence": sequence,
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
    mobile_path = sortie / "mobile" / f"{nom}.html"
    for chemin in (html_path, pdf_path, json_path, mobile_path):
        chemin.parent.mkdir(parents=True, exist_ok=True)
    html_path.write_text(rendre(edition), encoding="utf-8")
    mobile_path.write_text(rendre_mobile(edition), encoding="utf-8")
    json_path.write_text(json.dumps(edition, ensure_ascii=False, indent=1, default=str), encoding="utf-8")

    from ..pdf import _launch_browser
    with sync_playwright() as playwright:
        navigateur = _launch_browser(playwright)
        page = navigateur.new_page()
        page.goto(html_path.resolve().as_uri())
        page.wait_for_timeout(300)
        debordements = page.eval_on_selector_all("[data-deborde='oui']", "z => z.length")
        page.pdf(path=str(pdf_path), format="A4", print_background=True,
                 margin={"top": "0", "right": "0", "bottom": "0", "left": "0"})
        navigateur.close()
    if debordements:
        journal(f"  ! {debordements} zone(s) de texte encore trop longue(s) malgré l'ajustement")
    if memoriser:
        enregistrer_edition(dt.date.fromisoformat(edition["date"]), resultat["memoire"], racine)
    journal(f"✓ PDF : {pdf_path}")
    return pdf_path
