"""Section Sport : collecte (sans réseau), requête, rendu."""
import datetime as dt
import json

from signal_matin.journal import sport
from signal_matin.journal.rendu_mobile import _sport

MAINTENANT = dt.datetime(2026, 11, 6, 4, tzinfo=dt.timezone.utc)
MATCH = {"name": "Liverpool at Fenerbahce", "date": "2026-11-05T20:00Z",
         "status": {"type": {"completed": True, "description": "Full Time"}},
         "competitions": [{"competitors": [
             {"team": {"displayName": "Fenerbahce"}, "score": "1", "homeAway": "home", "winner": False},
             {"team": {"displayName": "Liverpool"}, "score": "3", "homeAway": "away", "winner": True}]}],
         "links": [{"href": "https://espn.com/match/1"}]}
RSS = """<rss><channel><title>L'Équipe</title><item><title><![CDATA[Sinner bat Fritz et file en demies]]></title>
<description>Le n° 1 mondial s'impose 6-3 6-4.</description><link>https://lequipe.fr/1</link>
<pubDate>Thu, 05 Nov 2026 21:00:00 +0100</pubDate></item>
<item><title>Vieille dépêche</title><link>https://lequipe.fr/0</link><pubDate>Mon, 02 Nov 2026 09:00:00 +0100</pubDate></item>
</channel></rss>"""


def test_collecte_scores_programme_et_depeches(monkeypatch):
    def lire(url):
        if "espn" in url:
            evenements = [MATCH] if "uefa.champions" in url and "20261105" in url else []
            return json.dumps({"events": evenements})
        return RSS
    monkeypatch.setattr(sport, "_lire", lire)
    matiere = sport.collecter(MAINTENANT, journal=lambda *a: None)
    assert [m["match"] for m in matiere["resultats"]] == ["Liverpool at Fenerbahce"]
    assert matiere["resultats"][0]["equipes"][1] == {"nom": "Liverpool", "score": "3", "domicile": False,
                                                     "vainqueur": True}
    assert matiere["resultats"][0]["heure"] == "21:00"  # heure de Paris
    assert [d["titre"] for d in matiere["depeches"]] == ["Sinner bat Fritz et file en demies"]
    assert matiere["erreurs"] == []


def test_collecte_hors_ligne_ne_bloque_pas():
    matiere = sport.collecter(MAINTENANT, journal=lambda *a: None)
    assert matiere["resultats"] == [] and "Ligue 1" in matiere["erreurs"]


def test_reponse_plafonnee_et_rendu():
    reponse = json.dumps({
        "resultats": [{"sport": "Tennis", "affiche": f"A{i} – B{i}", "score": "6-3 6-4",
                       "competition": "Masters 1000 de Paris (circuit ATP), 8es de finale",
                       "source": "L'Équipe", "url": "https://lequipe.fr/1"} for i in range(8)],
        "a_suivre": [{"sport": "Rugby", "affiche": "Toulouse – Clermont", "heure": "14 h 30",
                      "competition": "Top 14 (championnat de France)"}] * 5})
    data = sport.lire_reponse(reponse)
    assert len(data["resultats"]) == 5 and len(data["a_suivre"]) == 3
    html = _sport({"date": "2026-11-06", "sport": data})
    assert "Résultats du 05/11" in html and "À suivre aujourd'hui" in html
    assert html.index("Résultats du 05/11") < html.index("À suivre aujourd'hui")
    assert "<b>A0 – B0</b> <b class='score'>6-3 6-4</b>" in html
    assert "<p class='sp-c'>Masters 1000 de Paris (circuit ATP), 8es de finale</p>" in html
    assert "<b class='score'>14 h 30</b>" in html
    assert "lequipe.fr" not in html  # sources non affichées
    assert _sport({"sport": {"resultats": [], "a_suivre": []}}) == ""
