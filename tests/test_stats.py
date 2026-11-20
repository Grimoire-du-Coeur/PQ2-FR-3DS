"""Calcul de l'avancement (outils/stats.py)."""

import json

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


def test_bloc_et_readme(tmp_path):
    c = stats.compter(_trad(tmp_path))
    bloc = stats.bloc(c)
    assert "Histoire" in bloc and "Total" in bloc and "2 / 4 textes" in bloc
    readme = tmp_path / "README.md"
    readme.write_text("avant\n<!-- avancement:debut -->\nvieux\n<!-- avancement:fin -->\naprès\n",
                      encoding="utf-8")
    stats.maj_readme(readme, bloc)
    contenu = readme.read_text(encoding="utf-8")
    assert "vieux" not in contenu and "Histoire" in contenu and contenu.endswith("après\n")


def test_badges(tmp_path):
    c = stats.compter(_trad(tmp_path))
    dossier = tmp_path / ".github"
    stats.ecrire_badges(c, dossier)
    b = json.loads((dossier / "badge.json").read_text(encoding="utf-8"))
    assert b["schemaVersion"] == 1 and b["message"] == "50 %"
    assert (dossier / "badge_histoire.json").exists()
