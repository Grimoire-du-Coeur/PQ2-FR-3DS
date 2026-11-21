"""Le contrôle aller-retour, sur une image synthétique."""

import struct

import aller_retour
import msg1
import noms
from fabrique import (fabriquer_3ds, fabriquer_bf, fabriquer_cpk, fabriquer_itemtbl, fabriquer_msg1,
                      fabriquer_pak, fabriquer_table_noms)

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


def test_table_des_noms_d_objets(tmp_path):
    table = fabriquer_itemtbl("NULL", "Medicine", "Medicine")
    bilan = aller_retour.verifier(_image(tmp_path, {noms.OBJETS.chemin: table}))
    assert bilan.noms == 1 and bilan.echecs == []
    bilan = aller_retour.verifier(_image(tmp_path, {noms.OBJETS.chemin: table[:-1]}))
    assert [chemin for chemin, _ in bilan.echecs] == [noms.OBJETS.chemin]


def test_tables_de_noms_du_combat(tmp_path):
    bilan = aller_retour.verifier(_image(tmp_path, {
        "battle/table/skillnametable.tbl": fabriquer_table_noms(["Blank", "Agi", "Brand☆New☆Bam"]),
        "battle/table/personanametable.tbl": fabriquer_table_noms(["BLANK", "Pixie"], debuts=False)}))
    assert bilan.noms == 3 and bilan.echecs == []
    bilan = aller_retour.verifier(_image(tmp_path, {
        "battle/table/personanametable.tbl": fabriquer_table_noms(["BLANK", "Pixie"])[:-1]}))
    assert [chemin for chemin, _ in bilan.echecs] == ["battle/table/personanametable.tbl"]


def test_conteneur_gsd_inconnu(tmp_path):
    bilan = aller_retour.verifier(_image(tmp_path, {
        "quest/quest_99.gsd": fabriquer_pak([("quest_99.tbl", b"table"), ("quest_99.bf", fabriquer_bf(MSG))])}))
    assert ("quest/quest_99.gsd", "archive à scripts absente de catalogue.ARCHIVES") not in bilan.echecs
    bilan = aller_retour.verifier(_image(tmp_path, {
        "misc/inconnu.gsd": fabriquer_pak([("x.bf", fabriquer_bf(MSG))])}))
    assert ("misc/inconnu.gsd", "archive à scripts absente de catalogue.ARCHIVES") in bilan.echecs


def test_archive_en_japonais_ignoree(tmp_path):
    script = msg1.lire_msg1(MSG)
    for m in script.messages:
        m.pages = [p if k else "テスト".encode("cp932") + b"\0" for k, p in enumerate(m.pages[:1])]
    japonais = msg1.ecrire_msg1(script)
    bilan = aller_retour.verifier(_image(tmp_path, {
        "battle/result/persona_get.bin": fabriquer_pak([("persona_get.bmd", japonais)])}))
    assert bilan.echecs == []
