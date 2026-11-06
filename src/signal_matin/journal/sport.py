"""Section Sport de la version numerique (decision du 06/11/2026).

Deux sortes de matiere, sans rien inventer :
- scores et programme structures (service public de resultats d'ESPN) : football, rugby,
  F1, basket ; resultats de la veille et matchs du jour ;
- titres et resumes des depeches sportives (L'Equipe par sport, RMC Sport) : tennis,
  cyclisme, athletisme et tout autre sport, ou seuls les titres donnent les resultats.

Une requete a l'IA (modele de tri) en tire au plus 5 resultats (une ligne de contexte)
et 3 rendez-vous « A suivre aujourd'hui » : evenements majeurs, plus les Francais en lice.
"""
from __future__ import annotations

import datetime as dt
import json
import re
import urllib.request
from zoneinfo import ZoneInfo

PARIS = ZoneInfo("Europe/Paris")
ESPN = "https://site.api.espn.com/apis/site/v2/sports/"
COMPETITIONS = {
    "soccer/uefa.champions": ("Football", "Ligue des champions"),
    "soccer/uefa.europa": ("Football", "Ligue Europa"),
    "soccer/fra.1": ("Football", "Ligue 1"),
    "soccer/eng.1": ("Football", "Premier League"),
    "soccer/esp.1": ("Football", "Liga"),
    "soccer/ita.1": ("Football", "Serie A"),
    "soccer/ger.1": ("Football", "Bundesliga"),
    "soccer/uefa.nations": ("Football", "Ligue des nations"),
    "soccer/fifa.friendly": ("Football", "Match amical international"),
    "soccer/fifa.world": ("Football", "Coupe du monde"),
    "rugby/270559": ("Rugby", "Top 14"),
    "rugby/180659": ("Rugby", "Tournoi des Six Nations"),
    "rugby/289234": ("Rugby", "Test-matchs internationaux"),
    "racing/f1": ("F1", "Formule 1"),
    "basketball/nba": ("Basket", "NBA"),
}
DEPECHES = {
    "L'Équipe Tennis": "https://dwh.lequipe.fr/api/edito/rss?path=/Tennis/",
    "L'Équipe Cyclisme": "https://dwh.lequipe.fr/api/edito/rss?path=/Cyclisme-sur-route/",
    "L'Équipe Athlétisme": "https://dwh.lequipe.fr/api/edito/rss?path=/Athletisme/",
    "L'Équipe Rugby": "https://dwh.lequipe.fr/api/edito/rss?path=/Rugby/",
    "L'Équipe Formule 1": "https://dwh.lequipe.fr/api/edito/rss?path=/Formule-1/",
    "L'Équipe Football": "https://dwh.lequipe.fr/api/edito/rss?path=/Football/",
    "L'Équipe (une)": "https://dwh.lequipe.fr/api/edito/rss?path=/",
    "RMC Sport": "https://rmcsport.bfmtv.com/rss/fil-sport/",
}
UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/130 Safari/537.36"}
MAX_RESULTATS, MAX_A_SUIVRE = 5, 3


def _lire(url: str) -> str:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=20) as reponse:
        return reponse.read().decode("utf-8", "replace")


def _match(evenement: dict, sport: str, competition: str) -> dict:
    statut = evenement.get("status", {}).get("type", {})
    debut = dt.datetime.fromisoformat(evenement["date"].replace("Z", "+00:00")).astimezone(PARIS)
    equipes = []
    for c in (evenement.get("competitions") or [{}])[0].get("competitors", []):
        nom = (c.get("team") or c.get("athlete") or {}).get("displayName", "")
        equipes.append({"nom": nom, "score": c.get("score"), "domicile": c.get("homeAway") == "home",
                        "vainqueur": c.get("winner")})
    return {"sport": sport, "competition": competition, "match": evenement.get("name", ""),
            "date": debut.strftime("%Y-%m-%d"), "heure": debut.strftime("%H:%M"),
            "termine": bool(statut.get("completed")), "statut": statut.get("description", ""),
            "equipes": equipes if len(equipes) <= 4 else equipes[:3],
            "url": next((l.get("href") for l in evenement.get("links", []) if l.get("href")), "")}


def _depeches(nom: str, url: str, depuis: dt.datetime) -> list[dict]:
    corps = _lire(url)
    sortie = []
    for item in re.findall(r"<item>(.*?)</item>", corps, re.S)[:40]:
        def champ(balise):
            m = re.search(rf"<{balise}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{balise}>", item, re.S)
            return re.sub(r"<[^>]+>", "", m.group(1)).strip() if m else ""
        try:
            from email.utils import parsedate_to_datetime
            date = parsedate_to_datetime(champ("pubDate"))
            if date < depuis:
                continue
        except (TypeError, ValueError):
            pass
        import html
        sortie.append({"source": nom.split(" ")[0] if nom.startswith("L'") else nom,
                       "titre": html.unescape(champ("title")),
                       "resume": html.unescape(champ("description"))[:300], "url": champ("link")})
    return sortie


def collecter(maintenant: dt.datetime, journal=print) -> dict:
    """Scores d'hier, programme du jour et depeches des dernieres 30 h."""
    jour = maintenant.astimezone(PARIS).date()
    hier = jour - dt.timedelta(days=1)
    resultats, programme, depeches, erreurs = [], [], [], []
    for chemin, (sport, competition) in COMPETITIONS.items():
        for date, liste in ((hier, resultats), (jour, programme)):
            try:
                donnees = json.loads(_lire(f"{ESPN}{chemin}/scoreboard?dates={date:%Y%m%d}"))
            except Exception:
                erreurs.append(competition)
                break
            for evenement in donnees.get("events", []):
                match = _match(evenement, sport, competition)
                if (liste is resultats and match["termine"]) or (liste is programme and not match["termine"]):
                    liste.append(match)
    depuis = maintenant - dt.timedelta(hours=30)
    vus = set()
    for nom, url in DEPECHES.items():
        try:
            for d in _depeches(nom, url, depuis):
                if d["titre"] and d["titre"] not in vus:
                    vus.add(d["titre"])
                    depeches.append(d)
        except Exception:
            erreurs.append(nom)
    journal(f"  sport : {len(resultats)} résultats, {len(programme)} matchs au programme, "
            f"{len(depeches)} dépêches" + (f" ; indisponibles : {', '.join(sorted(set(erreurs)))}" if erreurs else ""))
    return {"jour": jour.isoformat(), "resultats": resultats, "programme": programme,
            "depeches": depeches[:150], "erreurs": sorted(set(erreurs))}


SYSTEME_SPORT = f"""Tu rédiges la rubrique Sport d'un journal personnel lu sur téléphone, en français, pour un lecteur qui veut l'essentiel en quelques lignes.

Matière fournie : « resultats » (scores définitifs d'hier), « programme » (matchs d'aujourd'hui, heure de Paris) et « depeches » (titres et résumés des dernières 30 heures : tennis, cyclisme, athlétisme et autres sports).

Règles :
- Uniquement les événements importants : finales et phases finales, Grands Chelems et Masters 1000, grands tours et classiques, grands marathons et championnats, matchs de premier plan des grandes compétitions (Ligue des champions, grands championnats européens, Top 14, Six Nations, Grand Prix de F1…), sélections nationales ; plus les sportifs et équipes français engagés dans un grand événement. Tous les sports sont possibles.
- « resultats » : au plus {MAX_RESULTATS} lignes ; chacune donne le sport, puis le résultat exact et une seule phrase de contexte (enjeu, qualification, record, classement). Chaque score, nom ou temps doit figurer tel quel dans la matière fournie : n'invente rien, ne complète rien de mémoire ; un résultat seulement évoqué dans un titre peut être repris s'il y est explicite.
- « a_suivre » : au plus {MAX_A_SUIVRE} rendez-vous d'aujourd'hui, avec l'heure si elle est connue (format 14 h 30).
- Formule 1 (et sports mécaniques) : dans « programme », la date et l'heure sont celles du début du week-end de course (essais), pas de la course. N'écris jamais « Grand Prix » suivi de cette heure ; mentionne la séance du jour (essais, qualifications, sprint, course) seulement si une dépêche la précise, sinon écris « week-end du Grand Prix de … » sans heure.
- Phrases courtes, style dépêche. Pas de rumeurs, de transferts ni de polémiques. Listes vides acceptées s'il n'y a rien d'important.
- Pour chaque ligne, reprends « source » et « url » de l'élément utilisé (pour les scores structurés : source « ESPN »)."""

SCHEMA_SPORT = {"type": "object", "properties": {
    "resultats": {"type": "array", "items": {"type": "object", "properties": {
        "sport": {"type": "string"}, "texte": {"type": "string"},
        "source": {"type": "string"}, "url": {"type": "string"}}, "required": ["sport", "texte"]}},
    "a_suivre": {"type": "array", "items": {"type": "object", "properties": {
        "sport": {"type": "string"}, "texte": {"type": "string"}, "heure": {"type": "string"},
        "source": {"type": "string"}, "url": {"type": "string"}}, "required": ["sport", "texte"]}}},
    "required": ["resultats", "a_suivre"]}


def requete(client, matiere: dict):
    from .ia import Requete
    contenu = {k: matiere.get(k, []) for k in ("resultats", "programme", "depeches")}
    return Requete(id="sport", modele=client.modele_tri, systeme=SYSTEME_SPORT,
                   contenu=json.dumps(contenu, ensure_ascii=False), max_tokens=3000, schema=SCHEMA_SPORT)


def lire_reponse(texte: str) -> dict:
    from .ia import extraire_json
    data = extraire_json(texte)
    return {"resultats": [r for r in data.get("resultats", []) if r.get("texte")][:MAX_RESULTATS],
            "a_suivre": [r for r in data.get("a_suivre", []) if r.get("texte")][:MAX_A_SUIVRE]}
