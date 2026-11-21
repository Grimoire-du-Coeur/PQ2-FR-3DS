"""Extraction des textes du jeu vers trad/."""

import pytest

import catalogue
import commun
import extraire
import msg1
import noms
from fabrique import fabriquer_3ds, fabriquer_bf, fabriquer_cpk, fabriquer_msg1, fabriquer_pak

JAPONAIS = msg1.Message("jp_c", False, 0xFFFF, ["テスト".encode("cp932") + b"\0"])


def _scripts(tmp_path, fichiers=None):
    script = msg1.lire_msg1(fabriquer_msg1())
    script.messages.append(JAPONAIS)
    msg = msg1.ecrire_msg1(script)
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk(fichiers or {
        "init/aide.bmd": msg,
        "event/e100/e101.bf": fabriquer_bf(msg),
    })))
    return catalogue.lire_scripts(image)


def test_entrees(tmp_path):
    fichiers, orphelins, revoir = extraire.construire(_scripts(tmp_path), {})
    assert set(fichiers) == {"histoire/e100/e101.json", "systeme/init/aide.json",
                             extraire.LOCUTEURS}
    dlg, sel = fichiers["systeme/init/aide.json"]
    assert dlg == {"id": "dlg_a", "locuteur": "Yosuke", "en": "Hello there!{PAGE}Bye.", "fr": ""}
    assert sel == {"id": "sel_b", "choix": True, "en": "Yes{OPTION}No{OPTION}Maybe", "fr": ""}
    assert fichiers[extraire.LOCUTEURS] == [{"id": "Yosuke", "en": "Yosuke", "fr": ""}]
    assert orphelins == [] and revoir == []


def test_message_japonais_ecarte(tmp_path):
    fichiers, _, _ = extraire.construire(_scripts(tmp_path), {})
    assert "jp_c" not in [e["id"] for e in fichiers["systeme/init/aide.json"]]


@pytest.mark.parametrize("lisible, attendu", [
    ("Dummy", True), ("DUMMY", True), ("Not used", True), ("NOT USED", True), ("Unused", True),
    ("Reserved", True), ("RESERVE Myth", True), ("Blank", True), ("BLANK", True),
    ("Counter Skill help text not used.", True), ("TEST NEWGAME", True), ("Test 1", True),
    ("{f 0 1 2}Dummy{f 0 1 0}{PAGE}Not used", True),
    # de vraies répliques ou des libellés qui peuvent s'afficher en jeu
    ("None", False), ("Reserve", False), ("I AM A DUMMY!", False),
    ("Learned all skills dummy MSG.", False),       # s'affiche : traduit par Tyron26
    ("No, dummy. Obviously it means, like, \"awesome\" here!", False),
    ("Test out your strength on the FOE.", False),
])
def test_texte_factice(lisible, attendu):
    assert extraire.est_factice(lisible) is attendu


def test_message_factice_ecarte(tmp_path):
    script = msg1.lire_msg1(fabriquer_msg1())
    script.messages.append(msg1.Message("dummy_d", False, 0xFFFF, [b"\xf1\x41Dummy\x00"]))
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk({"init/aide.bmd": msg1.ecrire_msg1(script)})))
    fichiers, _, _ = extraire.construire(catalogue.lire_scripts(image), {})
    assert "dummy_d" not in [e["id"] for e in fichiers["systeme/init/aide.json"]]


def test_fr_conserve(tmp_path):
    scripts = _scripts(tmp_path)
    anciennes = {("systeme/init/aide.json", "dlg_a"):
                 {"id": "dlg_a", "en": "Hello there!{PAGE}Bye.", "fr": "Salut !{PAGE}Ciao.",
                  "commentaire": "ton familier"},
                 (extraire.LOCUTEURS, "Yosuke"): {"id": "Yosuke", "en": "Yosuke", "fr": "Yosuke"}}
    fichiers, _, revoir = extraire.construire(scripts, anciennes)
    dlg = fichiers["systeme/init/aide.json"][0]
    assert dlg["fr"] == "Salut !{PAGE}Ciao." and dlg["commentaire"] == "ton familier"
    assert fichiers[extraire.LOCUTEURS][0]["fr"] == "Yosuke"
    assert revoir == []


def test_anglais_change(tmp_path):
    anciennes = {("systeme/init/aide.json", "dlg_a"):
                 {"id": "dlg_a", "en": "Hi!{PAGE}Bye.", "fr": "Salut !{PAGE}Ciao."}}
    fichiers, _, revoir = extraire.construire(_scripts(tmp_path), anciennes)
    dlg = fichiers["systeme/init/aide.json"][0]
    assert dlg["a_revoir"] == "Hi!{PAGE}Bye." and dlg["fr"] == "Salut !{PAGE}Ciao."
    assert revoir == ["systeme/init/aide.json dlg_a"]


def test_orphelin(tmp_path):
    anciennes = {("systeme/init/aide.json", "disparu"): {"id": "disparu", "en": "Gone", "fr": "Parti"},
                 ("systeme/init/aide.json", "vide"): {"id": "vide", "en": "Empty", "fr": ""}}
    _, orphelins, _ = extraire.construire(_scripts(tmp_path), anciennes)
    assert orphelins == [{"fichier": "systeme/init/aide.json", "id": "disparu", "en": "Gone",
                          "fr": "Parti"}]


def test_collision(tmp_path):
    msg = fabriquer_msg1()
    autre = msg1.lire_msg1(msg)
    autre.messages[0].pages[0] = bytes.fromhex("f141") + b"Something else!\n"
    scripts = _scripts(tmp_path, {"event/a/x.bmd": msg,
                                  "event/a/x.bf": fabriquer_bf(msg1.ecrire_msg1(autre))})
    with pytest.raises(ValueError, match="histoire/a/x.json"):
        extraire.construire(scripts, {})


def test_copie_empaquetee_partage_son_json(tmp_path):
    msg = fabriquer_msg1()
    scripts = _scripts(tmp_path, {
        "facility/shop.bmd": msg,
        "facility/pack/shop.arc": fabriquer_pak([("shop.bmd", msg), ("propre.bmd", msg)]),
    })
    assert sorted(s.trad for s in scripts) == ["systeme/facility/pack/shop/propre.json",
                                               "systeme/facility/shop.json", "systeme/facility/shop.json"]
    fichiers, _, _ = extraire.construire(scripts, {})
    assert {"systeme/facility/shop.json", "systeme/facility/pack/shop/propre.json"} <= set(fichiers)


def test_ecrire_puis_verifier(tmp_path):
    racine = tmp_path / "trad"
    fichiers, orphelins, _ = extraire.construire(_scripts(tmp_path), {})
    extraire.ecrire(fichiers, orphelins, racine)
    assert commun.lire_json(racine / "systeme/init/aide.json")[0]["id"] == "dlg_a"
    assert extraire.differences(fichiers, orphelins, racine) == []
    (racine / "systeme/init/aide.json").write_text("[]\n", encoding="utf-8")
    assert extraire.differences(fichiers, orphelins, racine) == ["systeme/init/aide.json"]


def test_noms_d_objets(tmp_path):
    objets = noms.OBJETS.trad
    anciennes = {(objets, "Medicine"): {"id": "Medicine", "en": "Medicine", "max": 21, "fr": "Remède"}}
    fichiers, orphelins, _ = extraire.construire(_scripts(tmp_path), anciennes,
                                                 listes={objets: ["Rebel Knife", "Medicine"]})
    assert fichiers[objets] == [{"id": "Rebel Knife", "en": "Rebel Knife", "max": 21, "fr": ""},
                                {"id": "Medicine", "en": "Medicine", "max": 21, "fr": "Remède"}]
    assert orphelins == []


def test_noms_des_tables_de_combat(tmp_path):
    anciennes = {("noms/personas.json", "Pixie"): {"id": "Pixie", "en": "Pixie", "fr": "Pixie"}}
    fichiers, _, _ = extraire.construire(_scripts(tmp_path), anciennes,
                                         listes={"noms/personas.json": ["Pixie", "Jack Frost"]})
    assert fichiers["noms/personas.json"] == [{"id": "Pixie", "en": "Pixie", "fr": "Pixie"},
                                              {"id": "Jack Frost", "en": "Jack Frost", "fr": ""}]
