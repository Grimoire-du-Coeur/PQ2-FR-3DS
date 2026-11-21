"""Calcul et publication de l'avancement (outils/stats.py)."""

import json
import xml.etree.ElementTree as ET

import commun
import stats


def _trad(tmp_path):
    trad = tmp_path / "trad"
    commun.ecrire_json(trad / "histoire/e000/a.json", [
        {"id": "1", "en": "Hello there friend", "fr": "Salut l'ami"},
        {"id": "2", "en": "Bye", "fr": ""}])
    commun.ecrire_json(trad / "combat/b.json", [
        {"id": "3", "en": "Attack!", "fr": "", "a_revoir": "Hit!"}])
    commun.ecrire_json(trad / "noms/locuteurs.json", [{"id": "Ann", "en": "Ann", "fr": "Ann"}])
    commun.ecrire_json(trad / "_orphelins.json", [{"fichier": "x", "id": "y", "en": "z", "fr": "w"}])
    return trad


def test_compter(tmp_path):
    c = stats.compter(_trad(tmp_path))
    assert c.categories["histoire"] == [1, 2]
    assert c.categories["combat"] == [0, 1]
    assert c.categories["noms"] == [1, 1]
    assert c.dossiers["histoire/e000"] == [1, 2]
    assert c.mots == [3, 5]                       # mots anglais traduits / total (hors noms)
    assert c.revoir == [("combat/b.json", "3")]


def test_barre():
    assert stats.barre(0, 10) == "░" * 24
    assert stats.barre(10, 10) == "█" * 24
    assert stats.barre(1, 2) == "█" * 12 + "░" * 12


def test_pourcentage_lisible():
    assert stats.pourcentage(0, 100) == "0 %"
    assert stats.pourcentage(165, 29183) == "0,5 %"     # une décimale sous 10 %
    assert stats.pourcentage(3, 4922) == "< 0,1 %"
    assert stats.pourcentage(37, 100) == "37 %"
    assert stats.pourcentage(0, 0) == "0 %"


def test_publication(tmp_path):
    c = stats.compter(_trad(tmp_path))
    sortie = tmp_path / "suivi"
    stats.publier(c, sortie)
    assert sorted(p.name for p in sortie.iterdir()) == [
        "SUIVI.md", "avancement.svg", "badge.json", "badge_combat.json", "badge_donjons.json",
        "badge_histoire.json", "badge_noms.json", "badge_systeme.json"]
    b = json.loads((sortie / "badge.json").read_text(encoding="utf-8"))
    assert b["schemaVersion"] == 1 and b["message"] == "50 %"
    # SUIVI.md vit sur la branche « suivi » : ses liens visent main
    suivi = (sortie / "SUIVI.md").read_text(encoding="utf-8")
    assert f"]({stats.DEPOT}/blob/main/trad/histoire/e000)" in suivi
    assert "2 / 4 textes" in suivi


def test_carte_svg(tmp_path):
    c = stats.compter(_trad(tmp_path))
    svg = stats.carte(c)
    racine = ET.fromstring(svg)                      # SVG bien formé
    assert racine.tag.endswith("svg")
    for nom in ("Histoire", "Donjons", "Combat", "Système", "Noms"):
        assert nom in svg
    assert "prefers-reduced-motion" in svg


def test_propagation_comptee(tmp_path):
    trad = tmp_path / "trad"
    commun.ecrire_json(trad / "histoire/e100/a.json", [{"id": "1", "en": "Arf!", "fr": "Ouaf !"}])
    commun.ecrire_json(trad / "donjons/b.json", [{"id": "2", "en": "Arf!", "fr": ""},
                                                 {"id": "3", "en": "Huh?", "fr": ""}])
    c = stats.compter(trad)
    assert c.categories["donjons"] == [1, 2]       # « Arf! » est couvert par propagation
    assert c.propages == 1
    assert "dont 1 par propagation" in stats.bloc(c)


def test_divergences_dans_le_suivi(tmp_path):
    trad = tmp_path / "trad"
    commun.ecrire_json(trad / "histoire/a.json", [{"id": "1", "en": "Huh?", "fr": "Hein ?"},
                                                  {"id": "2", "en": "Huh?", "fr": "Quoi ?"}])
    suivi = stats.suivi(stats.compter(trad))
    assert "## À harmoniser" in suivi and "Hein ?" in suivi and "Quoi ?" in suivi


def test_qui_fait_quoi(tmp_path):
    c = stats.compter(_trad(tmp_path))
    ouvertes = [{"number": 7, "author": {"login": "chenetulipe"}, "isDraft": False,
                 "files": [{"path": "trad/histoire/e000/a.json"}, {"path": "README.md"}]}]
    fusionnees = [{"number": 3, "author": {"login": "tyron2611"},
                   "files": [{"path": "trad/histoire/e000/a.json"}]},
                  {"number": 4, "author": {"login": "CodeByHaamza"},
                   "files": [{"path": "outils/stats.py"}]}]
    stats.ajouter_activite(c, ouvertes, fusionnees)
    assert c.en_cours["histoire/e000"] == [("chenetulipe", 7)]
    assert c.contributeurs["histoire/e000"] == ["tyron2611"]
    suivi = stats.suivi(c)
    assert "@chenetulipe ([#7](" in suivi and "@tyron2611" in suivi
    assert "CodeByHaamza" not in suivi            # une PR d'outillage ne crédite pas un dossier
