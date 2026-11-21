"""Le contrôle aller-retour, sur une image synthétique."""

import struct

import aller_retour
from fabrique import fabriquer_3ds, fabriquer_bf, fabriquer_cpk, fabriquer_msg1, fabriquer_pak

MSG = fabriquer_msg1()


def _image(tmp_path, fichiers):
    chemin = tmp_path / "jeu.3ds"
    chemin.write_bytes(fabriquer_3ds(fabriquer_cpk(fichiers, compresses={"event/e100/e101.bf"})))
    return chemin


def test_tout_identique(tmp_path):
    image = _image(tmp_path, {
        "init/aide.bmd": MSG,
        "event/e100/e101.bf": fabriquer_bf(MSG) + bytes(0x100),
        "battle/ai/vide.bf": fabriquer_bf(None),
        "font/police.bcfnt": b"pas un script",
    })
    bilan = aller_retour.verifier(image)
    assert (bilan.fichiers, bilan.identiques, bilan.sans_messages) == (3, 2, 1)
    assert bilan.messages == 4
    assert bilan.pages == 10          # 2 pages + 3 options, dans deux scripts
    assert bilan.equivalents == [] and bilan.echecs == []


def test_message_en_double_est_equivalent(tmp_path):
    double = bytearray(MSG)
    struct.pack_into("<II", double, 0x28, *struct.unpack_from("<II", double, 0x20))
    bilan = aller_retour.verifier(_image(tmp_path, {"battle/event/double.bmd": bytes(double)}))
    assert bilan.equivalents == ["battle/event/double.bmd"]
    assert bilan.echecs == []


def test_script_illisible_est_un_echec(tmp_path):
    casse = MSG[:0x20] + b"\xff" * 8 + MSG[0x28:]
    bilan = aller_retour.verifier(_image(tmp_path, {"init/casse.bmd": casse}))
    assert [chemin for chemin, _ in bilan.echecs] == ["init/casse.bmd"]


def test_archive_connue(tmp_path):
    bilan = aller_retour.verifier(_image(tmp_path, {
        "facility/pack/shop.arc": fabriquer_pak([("shop.bmd", MSG), ("icone.ctpk", b"image")])}))
    assert bilan.fichiers == 1 and bilan.identiques == 1 and bilan.echecs == []


def test_archive_a_scripts_inconnue(tmp_path):
    bilan = aller_retour.verifier(_image(tmp_path, {
        "init/nouvelle.arc": fabriquer_pak([("aide.bmd", MSG)])}))
    assert ("init/nouvelle.arc", "archive à scripts absente de catalogue.ARCHIVES") in bilan.echecs
