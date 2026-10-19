"""Meteo du jour depuis Meteociel (pas de 3 h, modele GFS), repli Open-Meteo.

Meteociel ne propose pas d'API : la page de prevision est lue telle quelle.
Si sa structure change, `meteo_du_jour` bascule automatiquement sur Open-Meteo.
"""
from __future__ import annotations

import datetime as dt
import html
import json
import re
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

USER_AGENT = "Signal-Matin/1.0 (journal personnel, une lecture par jour)"
PLAGES = ((8, 12), (12, 14), (14, 18), (18, 22))

# Du plus calme au plus marque : sert a choisir le ciel representatif d'une plage.
_GRAVITE = (
    ("clair", 0), ("ensoleill", 0), ("peu nuageux", 1), ("mitig", 2),
    ("nuageux", 3), ("couvert", 3), ("brouillard", 3), ("bruine", 4),
    ("pluie faible", 4), ("averse", 5), ("pluie", 5), ("neige", 6),
    ("orage", 7),
)

_JOURS = {"lun": 0, "mar": 1, "mer": 2, "jeu": 3, "ven": 4, "sam": 5, "dim": 6}


@dataclass
class Pas:
    heure: int
    temperature: float
    vent: int
    rafales: int
    pluie: float
    ciel: str
    direction: str = ""


@dataclass
class Plage:
    libelle: str
    ciel: str
    temp_min: float
    temp_max: float
    vent: int
    rafales: int
    pluie: float


@dataclass
class Meteo:
    lieu: str
    source: str
    temp_min: float
    temp_max: float
    resume: str
    plages: list[Plage] = field(default_factory=list)


def _gravite(ciel: str) -> int:
    ciel = ciel.casefold()
    score = -1
    for cle, valeur in _GRAVITE:
        if cle in ciel:
            score = max(score, valeur)
    return score


def _texte(cellule: str) -> str:
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", cellule)).split())


def _nombre(valeur: str) -> float:
    match = re.search(r"-?\d+(?:[.,]\d+)?", valeur or "")
    return float(match.group(0).replace(",", ".")) if match else 0.0


def lire_meteociel(page: str, jour: dt.date) -> list[Pas]:
    """Extrait les pas de 3 h du jour demande depuis le HTML Meteociel."""
    pas: list[Pas] = []
    jour_courant: int | None = None
    for ligne in re.findall(r"<tr[^>]*>(.*?)</tr>", page, flags=re.S | re.I):
        cellules = re.findall(r"<td[^>]*>(.*?)</td>", ligne, flags=re.S | re.I)
        if not cellules:
            continue
        premiere = _texte(cellules[0])
        entete = re.match(r"([A-Za-zé]{3})\s+(\d{1,2})$", premiere)
        if entete and entete.group(1).casefold()[:3] in _JOURS:
            jour_courant = int(entete.group(2))
            cellules = cellules[1:]
        if len(cellules) < 10 or not re.fullmatch(r"\d{2}:\d{2}", _texte(cellules[0])):
            continue
        if jour_courant != jour.day:
            continue
        direction = re.search(r"alt='([^':]+)", cellules[3])
        ciel = re.search(r'alt="([^"]+)"', cellules[9]) or re.search(r"alt='([^']+)'", cellules[9])
        pluie = _texte(cellules[6])
        pas.append(Pas(
            heure=int(_texte(cellules[0])[:2]),
            temperature=_nombre(_texte(cellules[1])),
            vent=int(_nombre(_texte(cellules[4]))),
            rafales=int(_nombre(_texte(cellules[5]))),
            pluie=0.0 if pluie.startswith("--") else _nombre(pluie),
            ciel=html.unescape(ciel.group(1)) if ciel else "",
            direction=html.unescape(direction.group(1)).strip() if direction else "",
        ))
    return pas


def _plages(pas: list[Pas]) -> list[Plage]:
    resultat: list[Plage] = []
    for debut, fin in PLAGES:
        dans = [p for p in pas if debut <= p.heure <= fin]
        if not dans:
            dans = sorted(pas, key=lambda p: min(abs(p.heure - debut), abs(p.heure - fin)))[:1]
        # La pluie Meteociel couvre les 3 h precedant l'echeance.
        pluvieux = [p for p in pas if p.heure > debut and p.heure - 3 < fin]
        if not dans:
            continue
        resultat.append(Plage(
            libelle=f"{debut}h–{fin}h",
            ciel=max(dans, key=lambda p: _gravite(p.ciel)).ciel,
            temp_min=min(p.temperature for p in dans),
            temp_max=max(p.temperature for p in dans),
            vent=max(p.vent for p in dans),
            rafales=max(p.rafales for p in dans),
            pluie=round(sum(p.pluie for p in pluvieux), 1),
        ))
    return resultat


def _direction_dominante(pas: list[Pas]) -> str:
    journee = [p.direction for p in pas if 8 <= p.heure <= 22 and p.direction]
    if not journee:
        return ""
    dominante = max(set(journee), key=journee.count)
    return dominante.casefold().strip()


def resumer(pas: list[Pas], plages: list[Plage]) -> str:
    """Une phrase sobre, construite sans IA a partir des donnees."""
    if not plages:
        return "Prévision indisponible."
    ciels = [p.ciel.casefold() for p in plages]
    if len(set(ciels)) == 1:
        ciel = f"{plages[0].ciel} toute la journée"
    else:
        matin, soir = plages[0].ciel, plages[-1].ciel
        ciel = f"{matin} le matin, {soir.casefold()} en soirée"
    vent_max = max(p.vent for p in plages)
    force = "faible" if vent_max < 15 else "modéré" if vent_max < 30 else "fort"
    direction = _direction_dominante(pas)
    if direction:
        liaison = "d'" if direction[0] in "aeiouéèy" else "de "
        vent = f"vent {force} {liaison}{direction}"
    else:
        vent = f"vent {force}"
    phrase = f"{ciel}, {vent}."
    pluvieuses = [p.libelle for p in plages if p.pluie >= 0.2]
    if pluvieuses:
        phrase += f" Pluie attendue sur {', '.join(pluvieuses)}."
    else:
        tard = [p for p in pas if p.heure >= 23 and p.pluie > 0]
        if tard:
            phrase += " Pluie faible attendue après 22 h."
    rafales = max(p.rafales for p in plages)
    if rafales >= 50:
        phrase += f" Rafales jusqu'à {rafales} km/h."
    return phrase[0].upper() + phrase[1:]


def _telecharger(url: str) -> bytes:
    requete = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(requete, timeout=15) as reponse:
        return reponse.read(1_500_000)


def _open_meteo(latitude: float, longitude: float, jour: dt.date) -> list[Pas]:
    params = urllib.parse.urlencode({
        "latitude": latitude, "longitude": longitude, "timezone": "Europe/Paris",
        "hourly": "temperature_2m,precipitation,wind_speed_10m,wind_gusts_10m,weather_code",
        "start_date": jour.isoformat(), "end_date": jour.isoformat(),
    })
    data = json.loads(_telecharger("https://api.open-meteo.com/v1/forecast?" + params))
    h = data["hourly"]
    codes = {0: "Ciel clair", 1: "Peu nuageux", 2: "Mitigé", 3: "Couvert", 45: "Brouillard",
             48: "Brouillard", 51: "Bruine", 53: "Bruine", 55: "Bruine", 61: "Pluie faible",
             63: "Pluie", 65: "Pluie forte", 80: "Averses", 81: "Averses", 82: "Averses",
             71: "Neige", 73: "Neige", 75: "Neige", 95: "Orage", 96: "Orage", 99: "Orage"}
    pas = []
    for index, horodatage in enumerate(h["time"]):
        heure = int(horodatage[11:13])
        if heure % 3 != 2:  # meme rythme que Meteociel : 02, 05, 08, ... 23 h
            continue
        pluie = sum(h["precipitation"][max(0, index - 2): index + 1])
        pas.append(Pas(
            heure=heure, temperature=h["temperature_2m"][index],
            vent=round(h["wind_speed_10m"][index]), rafales=round(h["wind_gusts_10m"][index]),
            pluie=round(pluie, 1), ciel=codes.get(h["weather_code"][index], "Variable"),
        ))
    return pas


def meteo_du_jour(config: dict, jour: dt.date) -> Meteo | None:
    lieu = config.get("lieu", "Issy-les-Moulineaux")
    url = config.get("meteociel_url", "https://www.meteociel.fr/previsions/33205/issy_les_moulineaux.htm")
    source = "Meteociel (modèle GFS)"
    try:
        pas = lire_meteociel(_telecharger(url).decode("latin-1"), jour)
        if len(pas) < 4:
            raise ValueError("structure Meteociel inattendue")
    except Exception:
        try:
            pas = _open_meteo(float(config.get("latitude", 48.8236)),
                              float(config.get("longitude", 2.2700)), jour)
            source = "Open-Meteo (secours)"
        except Exception:
            return None
    plages = _plages(pas)
    journee = [p for p in pas if 5 <= p.heure <= 23] or pas
    return Meteo(
        lieu=lieu, source=source,
        temp_min=min(p.temperature for p in journee),
        temp_max=max(p.temperature for p in journee),
        resume=resumer(pas, plages), plages=plages,
    )
