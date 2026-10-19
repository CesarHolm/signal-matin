"""Tests de l'edition personnalisee (sans reseau ni cle API)."""
import datetime as dt
import json
import random
from pathlib import Path
from types import SimpleNamespace

import pytest

from signal_matin.journal import edition as ed
from signal_matin.journal import ia
from signal_matin.journal.articles import Bloc, Candidat, fenetre_heures
from signal_matin.journal.etat import enregistrer_edition
from signal_matin.journal.jeux import _compter_solutions, compte_est_bon, futoshiki, shikaku
from signal_matin.journal.meteo import _plages, lire_meteociel, resumer
from signal_matin.journal.rendu import rendre
from signal_matin.journal.vocabulaire import charger_base, selection_du_jour

FIXTURES = Path(__file__).parent / "fixtures"


# ------------------------------------------------------------------ Meteo

def test_meteociel_est_lu_par_plages():
    page = (FIXTURES / "meteociel_issy.htm").read_bytes().decode("latin-1")
    pas = lire_meteociel(page, dt.date(2026, 10, 19))
    assert [p.heure for p in pas][:3] == [5, 8, 11]
    plages = _plages(pas)
    assert [p.libelle for p in plages] == ["8h–12h", "12h–14h", "14h–18h", "18h–22h"]
    assert plages[0].temp_min == 9 and plages[0].rafales == 15
    phrase = resumer(pas, plages)
    assert phrase.endswith(".") and "vent faible d'est" in phrase


# ------------------------------------------------------------------ Jeux

def test_sudoku_du_jour_a_solution_unique():
    from signal_matin.journal.jeux import sudoku_difficile
    jeu = sudoku_difficile(random.Random(1))
    assert 26 <= sum(1 for v in jeu["grille"] if v) <= 29
    assert _compter_solutions(jeu["grille"]) == 1
    assert all(g in (0, s) for g, s in zip(jeu["grille"], jeu["solution"]))


def test_autres_jeux_coherents():
    sk = shikaku(random.Random(2))
    assert sum(a for *_, a in sk["indices"]) == sk["largeur"] * sk["hauteur"]
    fu = futoshiki(random.Random(3))
    for a, b in fu["signes"]:
        assert fu["solution"][a[0]][a[1]] < fu["solution"][b[0]][b[1]]
    ce = compte_est_bon(random.Random(4))
    assert 101 <= ce["cible"] <= 999 and len(ce["plaques"]) == 6


# ------------------------------------------------------------ Vocabulaire

def test_base_de_mots_valide():
    mots = charger_base(Path("/nonexistent-signal-matin"))
    assert len(mots) >= 120
    assert {m["niveau"] for m in mots} == {"facile", "intermediaire", "difficile"}
    assert all(m["definition"] and m["exemple"] for m in mots)


def test_selection_2_1_2_et_revisions_le_lendemain(tmp_path):
    lundi = dt.date(2026, 10, 19)
    nouveaux, revisions = selection_du_jour(lundi, tmp_path)
    assert [m["niveau"] for m in nouveaux] == ["facile", "facile", "intermediaire", "difficile", "difficile"]
    assert sum(1 for m in nouveaux if m["domaine"] == "pro") == 1
    assert revisions == []
    enregistrer_edition(lundi, {"date": lundi.isoformat(), "nouveaux_mots": nouveaux}, tmp_path)
    nouveaux2, revisions2 = selection_du_jour(lundi + dt.timedelta(days=1), tmp_path)
    assert not {m["mot"] for m in nouveaux2} & {m["mot"] for m in nouveaux}
    assert {m["mot"] for m in revisions2} <= {m["mot"] for m in nouveaux}


def test_fenetre_du_lundi():
    assert fenetre_heures(dt.date(2026, 10, 19), {}) == 72
    assert fenetre_heures(dt.date(2026, 10, 20), {}) == 24


# --------------------------------------------------------------------- IA

def test_extraire_json_tolere_les_balises():
    assert ia.extraire_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert ia.extraire_json('Voici : {"a": {"b": 2}} fin') == {"a": {"b": 2}}
    with pytest.raises(ValueError):
        ia.extraire_json("rien")


def test_limite_et_ajustement_de_longueur():
    assert ia.limite_caracteres("x" * 20000) == 2800
    assert ia.limite_caracteres("x" * 5000) == 2000
    article = {"chapo": "c" * 100, "synthese": "s" * 100,
               "sections": [{"intertitre": "t", "texte": "x" * 900} for _ in range(4)]}
    ajuste = ia.ajuster_longueur(article, 2000)
    assert len(ajuste["sections"]) == 2


class FauxLots:
    def __init__(self, reponses, terminer=True):
        self.reponses, self.terminer, self.annule = reponses, terminer, False

    def create(self, requests):
        self.ids = [r["custom_id"] for r in requests]
        return SimpleNamespace(id="lot1", processing_status="ended" if self.terminer else "in_progress")

    def retrieve(self, _):
        return SimpleNamespace(id="lot1", processing_status="ended" if self.terminer else "in_progress")

    def cancel(self, _):
        self.annule = True

    def results(self, _):
        if not self.terminer:
            return []
        for cid in self.ids:
            message = SimpleNamespace(content=[SimpleNamespace(type="text", text=self.reponses[cid])])
            yield SimpleNamespace(custom_id=cid, result=SimpleNamespace(type="succeeded", message=message))


class FauxMessages:
    def __init__(self, lots, direct):
        self.batches, self.direct_reponses, self.appels_directs = lots, direct, 0

    def create(self, **params):
        self.appels_directs += 1
        texte = params["messages"][0]["content"]
        return SimpleNamespace(content=[SimpleNamespace(type="text", text=self.direct_reponses(texte))])


def _client(lots, direct=lambda t: "{}", config=None):
    client = object.__new__(ia.ClientIA)
    client.config = {"intervalle_sondage_s": 0, **(config or {})}
    client.journal = lambda *a: None
    client.modele_tri, client.modele_synthese = ia.MODELE_TRI, ia.MODELE_SYNTHESE
    client.client = SimpleNamespace(messages=FauxMessages(lots, direct))
    return client


def test_lot_de_nuit_puis_bascule_en_direct_a_l_heure_limite():
    requetes = [ia.Requete(id="r1", modele="m", systeme="s", contenu="a")]
    client = _client(FauxLots({"r1": '{"ok": 1}'}))
    assert client.lot(requetes, dt.datetime.now().astimezone() + dt.timedelta(hours=1)) == {"r1": '{"ok": 1}'}

    lents = FauxLots({}, terminer=False)
    client = _client(lents, direct=lambda t: '{"direct": 1}')
    resultat = client.lot(requetes, dt.datetime.now().astimezone() - dt.timedelta(seconds=1))
    assert lents.annule and resultat == {"r1": '{"direct": 1}'}


def test_cle_absente_donne_ia_indisponible(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    with pytest.raises(ia.IAIndisponible):
        ia.ClientIA({})


# ---------------------------------------------------------- Bout en bout

def _candidat(i, bloc, rubrique="IA", titre="Titre", nature="actu"):
    return Candidat(id=f"a{i}", bloc=bloc, rubrique=rubrique, source="Source", titre=f"{titre} {i}",
                    resume="Résumé " * 30, url=f"https://exemple.org/{i}",
                    publie_le=dt.datetime(2026, 10, 19, 6, tzinfo=dt.timezone.utc), nature=nature)


def test_edition_complete_avec_ia_simulee(tmp_path, monkeypatch):
    blocs = [Bloc(id="ia", titre="IA & recherche", rubriques=["IA"],
                  candidats=[_candidat(i, "ia") for i in range(1, 7)]),
             Bloc(id="curiosites", titre="Curiosités", rubriques=["Sport"],
                  candidats=[_candidat(10, "curiosites", "Sport", "Le PSG gagne"),
                             _candidat(11, "curiosites", "Sport", "Tennis"),
                             _candidat(12, "curiosites", "Sport", "Fractionné", "methode"),
                             _candidat(13, "curiosites", "Science", "Mars")])]
    monkeypatch.setattr(ed.art, "collecter", lambda *a, **k: (blocs, []))
    monkeypatch.setattr(ed.art, "texte_integral", lambda url, repli: ("Texte intégral. " * 400, "Jane Doe"))
    monkeypatch.setattr(ed, "meteo_du_jour", lambda *a: None)

    def reponse(texte):
        if texte.startswith("{\"bloc\": \"IA"):
            return json.dumps({"developpes": [{"id": "a1"}, {"id": "a2"}],
                               "breves": [{"id": "a3", "titre": "Brève 3", "texte": "Texte."}]})
        if texte.startswith("{\"bloc\""):
            assert "PSG" not in texte  # filtre football avant l'IA
            return json.dumps({"developpes": [{"id": "a12"}, {"id": "a13"}],
                               "breves": [{"id": "a11", "titre": "Tennis", "texte": "Texte."}]})
        if texte.startswith("Limite"):
            return json.dumps({"titre": "Titre FR", "chapo": "Chapô.", "synthese": "Deux phrases. Fin.",
                               "sections": [{"intertitre": "Le principe", "texte": "Paragraphe."}]})
        if texte.startswith("["):
            return json.dumps({"questions": [{"question": "Q ?", "options": ["a", "b", "c"], "reponse": 2}]})
        return json.dumps({"mots": []})

    client = _client(None, direct=reponse, config={"traitement_differe": False})
    monkeypatch.setattr(ed.ia, "ClientIA", lambda conf, journal=print: client)
    resultat = ed.produire({"journal": {}}, dt.datetime(2026, 10, 19, 4, tzinfo=dt.timezone.utc),
                           racine=tmp_path, journal=lambda *a: None)
    edition = resultat["edition"]
    assert not edition["secours"]
    assert [d["titre"] for d in edition["blocs"][0]["developpes"]] == ["Titre FR", "Titre FR"]
    assert edition["blocs"][0]["developpes"][0]["auteur"] == "Jane Doe"
    assert edition["quiz"][0]["reponse"] == 2
    assert resultat["memoire"]["reponses_quiz"] == ["c) c"]
    html = rendre(edition)
    assert "Synthèse" in html and "Le compte est bon" in html and "PSG" not in html


def test_edition_de_secours_sans_cle(tmp_path, monkeypatch):
    blocs = [Bloc(id="ia", titre="IA & recherche", rubriques=["IA"],
                  candidats=[_candidat(i, "ia") for i in range(1, 6)])]
    monkeypatch.setattr(ed.art, "collecter", lambda *a, **k: (blocs, ["Flux X"]))
    monkeypatch.setattr(ed.art, "texte_integral", lambda url, repli: (repli, ""))
    monkeypatch.setattr(ed, "meteo_du_jour", lambda *a: None)
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    resultat = ed.produire({"journal": {}}, dt.datetime(2026, 10, 20, 4, tzinfo=dt.timezone.utc),
                           racine=tmp_path, journal=lambda *a: None)
    edition = resultat["edition"]
    assert edition["secours"] and len(edition["blocs"][0]["developpes"]) == 2
    assert any("IA indisponible" in a for a in edition["avertissements"])
    assert "Édition de secours".upper() in rendre(edition)


def test_collecte_produit_des_url_texte(monkeypatch):
    from signal_matin.journal import articles
    from signal_matin.models import NewsItem, SourceRef, DataSourceStatus, DataState
    item = NewsItem(title="T", summary="R", source=SourceRef(name="S", url="https://exemple.org/a"))
    monkeypatch.setattr(articles, "collect_rss", lambda *a, **k: (
        [item], DataSourceStatus(name="S", state=DataState.LIVE, detail="1/1 flux lus")))
    conf = {"blocs": [{"id": "b", "titre": "B", "sources": [{"nom": "S", "url": "https://exemple.org/rss"}]}]}
    blocs, _ = articles.collecter(conf, dt.datetime(2026, 10, 20, 4, tzinfo=dt.timezone.utc), set())
    assert isinstance(blocs[0].candidats[0].url, str)
    blocs, _ = articles.collecter(conf, dt.datetime(2026, 10, 20, 4, tzinfo=dt.timezone.utc),
                                  {"https://exemple.org/a"})
    assert blocs[0].candidats == []  # deja publie : ecarte


def test_auteur_nettoye():
    c = _candidat(1, "ia")
    c.source, c.auteur = "Quanta Magazine", "John Pavlus October"
    assert ed._auteur(c) == "John Pavlus"
    c.source, c.auteur = "franceinfo", "Franceinfo"
    assert ed._auteur(c) == ""
