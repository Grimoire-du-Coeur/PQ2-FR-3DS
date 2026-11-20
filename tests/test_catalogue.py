"""Correspondance entre les fichiers du jeu et ceux de trad/."""

import pytest

import catalogue
from fabrique import fabriquer_3ds, fabriquer_bf, fabriquer_cpk, fabriquer_msg1


@pytest.mark.parametrize("jeu, trad", [
    ("event/e100/e101_001.bf", "histoire/e100/e101_001.json"),
    ("event/evt_intro.bmd", "histoire/evt_intro.json"),
    ("dungeon/script/support/s01.bf", "donjons/script/support/s01.json"),
    ("battle/support/message/000.bmd", "combat/support/message/000.json"),
    ("foe/script/foe_001.bf", "combat/foe/script/foe_001.json"),
    ("init/datitemhelp.bmd", "systeme/init/datitemhelp.json"),
    ("msg_racine.bmd", "systeme/msg_racine.json"),
])
def test_chemin_trad(jeu, trad):
    assert catalogue.chemin_trad(jeu) == trad


def test_lire_scripts(tmp_path):
    msg = fabriquer_msg1()
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk({
        "init/aide.bmd": msg,
        "event/e100/e101.bf": fabriquer_bf(msg),
        "battle/ai/vide.bf": fabriquer_bf(None),
        "font/police.bcfnt": b"pas un script",
    })))
    scripts = catalogue.lire_scripts(image)
    assert [s.chemin for s in scripts] == ["event/e100/e101.bf", "init/aide.bmd"]
    assert scripts[1].brut == msg
    assert [m.nom for m in scripts[0].messages.messages] == ["dlg_a", "sel_b"]
