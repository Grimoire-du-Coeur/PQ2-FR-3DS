"""Réinjection de trad/ dans les scripts du jeu, puis dans le CPK."""

import pytest

import catalogue
import commun
import ctd
import executable
import injecter
import msg1
import noms
import pak
import tables
from cpk import Cpk
from fabrique import (fabriquer_3ds, fabriquer_bf, fabriquer_code, fabriquer_cpk, fabriquer_ctd, fabriquer_itemtbl, fabriquer_msg1,
                      fabriquer_pak, fabriquer_table_noms)

MSG = fabriquer_msg1()
MSG1_PAGES = msg1.lire_msg1(MSG).messages[0].pages


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


def test_locuteur_traduit_dans_la_scene(tmp_path):
    # Traduit sur une réplique de e101, le nom vaut pour toute la scène, et
    # pour les autres scènes qui n'en donnent pas (aide.bmd).
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"histoire/e100/e101.json": [{**_dlg(""), "locuteur_fr": "Yôsuke"}]})
    nouveaux = injecter.remplacements(scripts, trad)
    attendu = [b"Y" + bytes.fromhex("81a1") + b"suke"]
    assert set(nouveaux) == {"init/aide.bmd", "event/e100/e101.bf"}
    assert msg1.lire_msg1(nouveaux["init/aide.bmd"]).locuteurs == attendu
    assert msg1.lire_msg1(nouveaux["init/aide.bmd"]).messages[0].pages == MSG1_PAGES


def test_le_nom_de_la_scene_garde_la_main(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {
        "noms/locuteurs.json": [{"id": "Yosuke", "en": "Yosuke", "fr": "Yosuke-senpai"}],
        "systeme/init/aide.json": [{**_dlg(""), "locuteur_fr": "Le prince"}],
    })
    nouveaux = injecter.remplacements(scripts, trad)
    assert msg1.lire_msg1(nouveaux["init/aide.bmd"]).locuteurs == [b"Le prince"]
    import flw0
    autre = msg1.lire_msg1(flw0.extraire_messages(nouveaux["event/e100/e101.bf"]))
    assert autre.locuteurs == [b"Yosuke-senpai"]                # locuteurs.json, pas l'autre scène


def test_deux_noms_pour_un_locuteur_refuses(tmp_path):
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = _trad(tmp_path, {"systeme/init/aide.json": [
        {**_dlg(""), "locuteur_fr": "Yosuke"},
        {**_dlg(""), "id": "dlg_z", "locuteur_fr": "Yôsuke"}]})
    with pytest.raises(injecter.ErreurInjection, match=r"aide\.json dlg_z.*Yosuke"):
        injecter.remplacements(scripts, trad)


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


_itemtbl = fabriquer_itemtbl


def test_noms_d_objets(tmp_path):
    brut = _itemtbl("NULL", "Medicine", "Rebel Knife", "Medicine")
    trad = _trad(tmp_path, {noms.OBJETS.trad: [
        {"id": "Medicine", "en": "Medicine", "max": 21, "fr": "Remède"},
        {"id": "Rebel Knife", "en": "Rebel Knife", "max": 21, "fr": ""}]})
    assert noms.lire_noms(injecter.table_fixe(brut, trad))[:4] == ["NULL", "Remède", "Rebel Knife", "Remède"]
    assert injecter.table_fixe(brut, _trad(tmp_path / "vide", {})) is None


def test_nom_d_objet_trop_long(tmp_path):
    trad = _trad(tmp_path, {noms.OBJETS.trad: [{"id": "Medicine", "en": "Medicine", "max": 21,
                                         "fr": "Médicament très fort"}]})
    with pytest.raises(injecter.ErreurInjection, match="22 octets"):
        injecter.table_fixe(_itemtbl("Medicine"), trad)


def test_build_avec_les_noms_d_objets(tmp_path):
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk(
        {"init/aide.bmd": MSG, noms.OBJETS.chemin: _itemtbl("NULL", "Medicine")}, compresses={noms.OBJETS.chemin})))
    trad = _trad(tmp_path, {noms.OBJETS.trad: [{"id": "Medicine", "en": "Medicine", "max": 21, "fr": "Remède"}]})
    sortie = tmp_path / "data.cpk"
    assert injecter.construire(image, trad, sortie) == (1, 0)
    with open(sortie, "rb") as f:
        assert noms.lire_noms(Cpk(f).lire(noms.OBJETS.chemin))[1] == "Remède"


def test_tables_de_noms_du_combat(tmp_path):
    competences = fabriquer_table_noms(["Blank", "Agi", "Rudra Ring", "Luck Knack"])
    personas = fabriquer_table_noms(["BLANK", "Sleipnir"], debuts=False)
    trad = _trad(tmp_path, {
        noms.OBJETS.trad: [{"id": "Rudra Ring", "en": "Rudra Ring", "max": 21, "fr": "Anneau de Rudra"},
                    {"id": "Sleipnir", "en": "Sleipnir", "max": 21, "fr": "Bottes de Sleipnir"}],
        "noms/competences.json": [{"id": "Agi", "en": "Agi", "fr": ""},
                                  {"id": "Luck Knack", "en": "Luck Knack", "fr": "Don de chance"}]})
    sortie = injecter.tables_de_noms({"battle/table/skillnametable.tbl": competences,
                                      "battle/table/personanametable.tbl": personas}, trad)
    assert set(sortie) == {"battle/table/skillnametable.tbl"}   # la Persona ne prend pas le nom des bottes
    assert tables.lire_table(sortie["battle/table/skillnametable.tbl"]).noms == [
        "Blank", "Agi", "Anneau de Rudra", "Don de chance"]


def test_build_avec_une_table_de_noms(tmp_path):
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk(
        {"init/aide.bmd": MSG,
         "battle/table/enemynametable.tbl": fabriquer_table_noms(["blank", "Cowardly Maya"], False)})))
    trad = _trad(tmp_path, {"noms/ennemis.json": [{"id": "Cowardly Maya", "en": "Cowardly Maya",
                                                   "fr": "Maya lâche"}]})
    sortie = tmp_path / "data.cpk"
    assert injecter.construire(image, trad, sortie) == (1, 0)
    with open(sortie, "rb") as f:
        assert tables.lire_table(Cpk(f).lire("battle/table/enemynametable.tbl")).noms == ["blank", "Maya lâche"]


def test_cmptable_scripts_et_tables_ctd(tmp_path):
    config = fabriquer_ctd(["Confirm", "BGM Volume"])
    cmptable = fabriquer_pak([("camp_msg.bmd", MSG), ("cmpConfigItem.ctd", config),
                              ("cmpTypeID_ITEM.ctd", fabriquer_ctd(nombres=bytes(16))),
                              ("cmpConfigItem.ctd", config)])
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk({"init/cmptable.bin": cmptable})))
    trad = _trad(tmp_path, {
        "systeme/init/cmptable/camp_msg.json": [_dlg("Salut !{PAGE}Ciao.")],
        "systeme/init/cmptable/cmpConfigItem.json": [{"id": "01", "en": "BGM Volume", "max": 63,
                                                      "fr": "Volume musique"}]})
    sortie = tmp_path / "data.cpk"
    injecter.construire(image, trad, sortie)
    with open(sortie, "rb") as f:
        refait = dict(reversed(pak.lire_pak(Cpk(f).lire("init/cmptable.bin"))))
    assert msg1.lire_msg1(refait["camp_msg.bmd"]).messages[0].pages[1] == b"\xf2\x05\xff\xffCiao.\x00"
    assert ctd.textes(refait["cmpConfigItem.ctd"]) == ["Confirm", "Volume musique"]


def test_table_ctd_trop_longue(tmp_path):
    cmptable = fabriquer_pak([("cmpConfigItem.ctd", fabriquer_ctd(["Confirm"]))])
    trad = _trad(tmp_path, {"systeme/init/cmptable/cmpConfigItem.json": [
        {"id": "00", "en": "Confirm", "max": 63, "fr": "é" * 40}]})
    with pytest.raises(injecter.ErreurInjection, match="cmpConfigItem"):
        injecter.tables_ctd(cmptable, trad)


def test_textes_de_l_executable(tmp_path, monkeypatch):
    code, d = fabriquer_code([b"\xf2\x05\xff\xff\xf1ASave data?\n", b"\xf2\x05\xff\xff\xf1AYes\nNo\n"])
    monkeypatch.setattr(executable, "EU", d)
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk({"init/aide.bmd": MSG}), code=code))
    sortie = tmp_path / "build" / "romfs" / "data.cpk"
    trad = _trad(tmp_path, {executable.TRAD: [{"id": "001", "en": "Yes{SAUT}No", "fr": "Oui{SAUT}Non"}]})
    injecter.construire(image, trad, sortie)
    ips = tmp_path / "build" / "code.ips"
    assert executable.appliquer_ips(code, ips.read_bytes()) == executable.traduire(code, {"001": "Oui{SAUT}Non"}, d)
    commun.ecrire_json(trad / executable.TRAD, [{"id": "001", "en": "Yes{SAUT}No", "fr": ""}])
    injecter.construire(image, trad, sortie)
    assert not ips.exists()                 # plus rien à patcher : pas de patch périmé
