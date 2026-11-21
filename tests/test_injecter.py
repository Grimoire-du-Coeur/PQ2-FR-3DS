"""Réinjection de trad/ dans les scripts du jeu, puis dans le CPK."""

import pytest

import catalogue
import commun
import injecter
import msg1
from cpk import Cpk
from fabrique import fabriquer_3ds, fabriquer_bf, fabriquer_cpk, fabriquer_msg1, fabriquer_pak

MSG = fabriquer_msg1()


def _image(tmp_path):
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk(
        {"init/aide.bmd": MSG, "event/e100/e101.bf": fabriquer_bf(MSG)},
        compresses={"event/e100/e101.bf"})))
    return image


def _trad(tmp_path, fichiers):
    racine = tmp_path / "trad"
    for rel, entrees in fichiers.items():
        commun.ecrire_json(racine / rel, entrees)
    return racine


def _dlg(fr):
    return {"id": "dlg_a", "locuteur": "Yosuke", "en": "Hello there!{PAGE}Bye.", "fr": fr}


def test_injecte_un_bmd(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"systeme/init/aide.json": [_dlg("Salut !{PAGE}Ciao.")]})
    nouveaux = injecter.remplacements(scripts, trad)
    assert set(nouveaux) == {"init/aide.bmd"}
    script = msg1.lire_msg1(nouveaux["init/aide.bmd"])
    assert script.messages[0].pages == [b"\xf1\x41Salut !\n", b"\xf2\x05\xff\xffCiao.\x00"]
    assert script.messages[1].pages == [b"Yes\x00", b"No\x00", b"Maybe\x00"]


def test_injecte_un_bf(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"histoire/e100/e101.json": [
        {"id": "sel_b", "choix": True, "en": "Yes{OPTION}No{OPTION}Maybe",
         "fr": "Oui{OPTION}Non{OPTION}Peut-être"}]})
    nouveaux = injecter.remplacements(scripts, trad)
    import flw0
    script = msg1.lire_msg1(flw0.extraire_messages(nouveaux["event/e100/e101.bf"]))
    peut_etre = b"Peut-" + bytes.fromhex("819b") + b"tre\x00"      # ê = 819B dans la police
    assert script.messages[1].pages == [b"Oui\x00", b"Non\x00", peut_etre]


def test_pages_en_nombre_different(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"systeme/init/aide.json": [_dlg("Salut ! Ciao.")]})
    with pytest.raises(injecter.ErreurInjection, match=r"systeme/init/aide\.json.*dlg_a.*2"):
        injecter.remplacements(scripts, trad)


def test_page_vide_refusee(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"systeme/init/aide.json": [_dlg("Salut !{PAGE}")]})
    with pytest.raises(injecter.ErreurInjection, match="vide"):
        injecter.remplacements(scripts, trad)


def test_locuteur_traduit(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"noms/locuteurs.json": [
        {"id": "Yosuke", "en": "Yosuke", "fr": "Yôsuke-kun"}]})
    nouveaux = injecter.remplacements(scripts, trad)
    assert set(nouveaux) == {"init/aide.bmd", "event/e100/e101.bf"}
    assert msg1.lire_msg1(nouveaux["init/aide.bmd"]).locuteurs == [b"Y" + bytes.fromhex("81a1") + b"suke-kun"]


def test_rien_a_traduire(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"systeme/init/aide.json": [_dlg("")]})
    assert injecter.remplacements(scripts, trad) == {}


@pytest.mark.parametrize("fr, attendu", [
    ("Café à l'œil", "Café à l'œil"),                     # accents gardés : la police les a
    ("« Oui » — c’est ça…", "“Oui” ― c’est ça…"),          # pas de « » dans la police ; tirets « ― »
    ("Quoi ? Non !", "Quoi ? Non !"),
    ("Encyclopædia", "Encyclopaedia"),
])
def test_adapter(fr, attendu):
    assert injecter.adapter(fr) == attendu


def test_build_complet_puis_relance(tmp_path):
    image = _image(tmp_path)
    trad = _trad(tmp_path, {"systeme/init/aide.json": [_dlg("Salut !{PAGE}Ciao.")]})
    sortie = tmp_path / "build" / "romfs" / "data.cpk"
    assert injecter.construire(image, trad, sortie) == (1, 1)
    taille = sortie.stat().st_size
    with open(sortie, "rb") as f:
        relu = msg1.lire_msg1(Cpk(f).lire("init/aide.bmd"))
    assert relu.messages[0].pages[1] == b"\xf2\x05\xff\xffCiao.\x00"
    assert injecter.construire(image, trad, sortie) == (1, 1)
    assert sortie.stat().st_size == taille


def test_propagation_d_une_replique_identique(tmp_path):
    # « dlg_a » existe dans les deux scripts avec le même anglais : traduit une
    # seule fois (dans e101), il doit sortir en français dans les deux.
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {
        "histoire/e100/e101.json": [_dlg("Salut !{PAGE}Ciao.")],
        "systeme/init/aide.json": [_dlg("")],
    })
    nouveaux = injecter.remplacements(scripts, trad)
    assert set(nouveaux) == {"init/aide.bmd", "event/e100/e101.bf"}
    assert msg1.lire_msg1(nouveaux["init/aide.bmd"]).messages[0].pages[1] == b"\xf2\x05\xff\xffCiao.\x00"


def test_une_traduction_propre_garde_la_main(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {
        "histoire/e100/e101.json": [_dlg("Salut !{PAGE}Ciao.")],
        "systeme/init/aide.json": [_dlg("Bonjour !{PAGE}Au revoir.")],
    })
    nouveaux = injecter.remplacements(scripts, trad)
    assert msg1.lire_msg1(nouveaux["init/aide.bmd"]).messages[0].pages[1] == b"\xf2\x05\xff\xffAu revoir.\x00"


def test_copie_empaquetee_traduite_aussi(tmp_path):
    # La boutique existe en fichier isolé et dans facility/pack/shop.arc : une seule
    # traduction, écrite aux deux endroits.
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk({
        "facility/shop.bmd": MSG,
        "facility/pack/shop.arc": fabriquer_pak([("shop.bmd", MSG), ("icone.ctpk", b"image")]),
    })))
    scripts = catalogue.lire_scripts(image)
    trad = _trad(tmp_path, {"systeme/facility/shop.json": [_dlg("Salut !{PAGE}Ciao.")]})
    nouveaux = injecter.remplacements(scripts, trad)
    assert set(nouveaux) == {"facility/shop.bmd", "facility/pack/shop.arc"}
    import pak
    contenu = dict(pak.lire_pak(nouveaux["facility/pack/shop.arc"]))
    assert contenu["shop.bmd"] == nouveaux["facility/shop.bmd"]
    assert contenu["icone.ctpk"] == b"image"
