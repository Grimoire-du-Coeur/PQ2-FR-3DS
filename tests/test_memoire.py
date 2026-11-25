"""Mémoire de traduction : une réplique traduite une fois l'est partout."""

import commun
import memoire


def _trad(tmp_path, fichiers):
    racine = tmp_path / "trad"
    for rel, entrees in fichiers.items():
        commun.ecrire_json(racine / rel, entrees)
    return racine


def test_reprend_une_traduction_existante(tmp_path):
    trad = _trad(tmp_path, {
        "histoire/e100/a.json": [{"id": "1", "en": "Arf!", "fr": "Ouaf !"}],
        "donjons/b.json": [{"id": "2", "en": "Arf!", "fr": ""}],
    })
    m = memoire.construire(trad)
    assert m.proposer("Arf!") == "Ouaf !"
    assert m.proposer("Woof!") is None


def test_la_traduction_la_plus_frequente_gagne(tmp_path):
    trad = _trad(tmp_path, {
        "a.json": [{"id": "1", "en": "Huh?", "fr": "Hein ?"}, {"id": "2", "en": "Huh?", "fr": "Quoi ?"}],
        "b.json": [{"id": "3", "en": "Huh?", "fr": "Hein ?"}],
    })
    m = memoire.construire(trad)
    assert m.proposer("Huh?") == "Hein ?"
    assert m.divergences() == [("Huh?", {"Hein ?": 2, "Quoi ?": 1})]


def test_ignore_les_noms_et_les_fichiers_techniques(tmp_path):
    trad = _trad(tmp_path, {
        "noms/locuteurs.json": [{"id": "Ann", "en": "Ann", "fr": "Anne"}],
        "_orphelins.json": [{"fichier": "x", "id": "y", "en": "Bye", "fr": "Salut"}],
    })
    m = memoire.construire(trad)
    assert m.proposer("Ann") is None and m.proposer("Bye") is None


def test_couverture(tmp_path):
    trad = _trad(tmp_path, {
        "a.json": [{"id": "1", "en": "Arf!", "fr": "Ouaf !"}, {"id": "2", "en": "Arf!", "fr": ""},
                   {"id": "3", "en": "Woof!", "fr": ""}],
    })
    m = memoire.construire(trad)
    assert m.couvre({"id": "2", "en": "Arf!", "fr": ""}) is True
    assert m.couvre({"id": "3", "en": "Woof!", "fr": ""}) is False
    assert m.couvre({"id": "1", "en": "Arf!", "fr": "Ouaf !"}) is False   # déjà traduit lui-même


def test_noms_de_scene():
    entrees = [{"id": "1", "locuteur": "Serious policeman", "en": "Hm.", "fr": ""},
               {"id": "2", "locuteur": "Serious policeman", "locuteur_fr": "Policier sérieux",
                "en": "Go!", "fr": ""},
               {"id": "3", "locuteur": "Ryuji", "locuteur_fr": "", "en": "Crap!", "fr": ""}]
    assert memoire.noms_de_scene(entrees) == {"Serious policeman": "Policier sérieux"}


def test_un_nom_traduit_dans_une_scene_vaut_partout(tmp_path):
    trad = _trad(tmp_path, {
        "histoire/e000/a.json": [{"id": "1", "locuteur": "Fat policeman",
                                  "locuteur_fr": "Policier corpulent", "en": "Roger!", "fr": ""}],
        "histoire/e000/b.json": [{"id": "1", "locuteur": "Fat policeman", "en": "Stop!", "fr": ""}],
    })
    loc = memoire.construire_locuteurs(trad)
    assert loc.nom("Fat policeman") == "Policier corpulent"
    assert loc.nom("Ryuji") is None


def test_priorite_des_noms(tmp_path):
    trad = _trad(tmp_path, {
        "noms/locuteurs.json": [{"id": "Voice", "en": "Voice", "fr": "Voix"}],
        "a.json": [{"id": "1", "locuteur": "Voice", "locuteur_fr": "Une voix", "en": "Hi", "fr": ""}],
        "b.json": [{"id": "1", "locuteur": "Voice", "locuteur_fr": "La voix", "en": "Hi", "fr": ""}],
    })
    loc = memoire.construire_locuteurs(trad)
    assert loc.nom("Voice", {"Voice": "Une voix"}) == "Une voix"     # la scène garde la main
    assert loc.nom("Voice", {}) == "Voix"                            # puis locuteurs.json
    assert loc.divergences() == [("Voice", {"Une voix": 1, "La voix": 1})]
