"""Tables .ctd des menus du camp (init/cmptable.bin)."""

import pytest

import ctd
from fabrique import fabriquer_ctd, fabriquer_pak


def test_textes():
    brut = fabriquer_ctd(["Confirm", "BGM Volume", "SAFTYのヘルプ", "", "None"])
    assert ctd.textes(brut) == ["Confirm", "BGM Volume", "SAFTYのヘルプ", "", "None"]
    assert ctd.a_traduire(brut) == [(0, "Confirm"), (1, "BGM Volume"), (4, "None")]


def test_table_de_nombres():
    brut = fabriquer_ctd(nombres=bytes(range(16)))
    assert ctd.textes(brut) is None and ctd.a_traduire(brut) == []


def test_ecrire_sur_place():
    brut = fabriquer_ctd(["Confirm", "BGM Volume"])
    nouveau = ctd.ecrire(brut, {1: "Volume de la musique"})
    assert len(nouveau) == len(brut) and nouveau[:16] == brut[:16] and nouveau[-16:] == brut[-16:]
    assert ctd.textes(nouveau) == ["Confirm", "Volume de la musique"]


def test_texte_trop_long():
    brut = fabriquer_ctd(["Confirm"])
    with pytest.raises(ctd.ErreurCtd, match="64 octets"):
        ctd.ecrire(brut, {0: "é" * 32})


def _cmptable(*entrees):
    return fabriquer_pak(list(entrees))


def test_tables_et_entrees():
    aide = fabriquer_ctd(["Not used. (If this appears, it is a bug.", "Adjust music volume"])
    brut = _cmptable(("cmpConfigHelp.ctd", aide), ("cmpTypeID_ITEM.ctd", fabriquer_ctd(nombres=bytes(16))),
                     ("camp_msg.bmd", b"script"), ("cmpConfigHelp.ctd", aide))
    assert list(ctd.tables(brut)) == ["cmpConfigHelp.ctd"]          # une fois, et sans la table de nombres
    assert ctd.entrees(brut) == {"systeme/init/cmptable/cmpConfigHelp.json": [
        {"id": "01", "en": "Adjust music volume", "max": 63}]}
