"""Import de fichiers traduits ailleurs (PersonaEditor + table de correspondance)."""

import catalogue
import commun
import importer
import msg1
from fabrique import fabriquer_3ds, fabriquer_cpk, fabriquer_msg1

# Extrait de la table de Tyron : il tapait « ま » pour « à » et « $ » pour « è ».
TABLE = "%=%\r\nま=à\r\n$=è\r\nら=é\r\n\r\n   \r\n"


def _image(tmp_path):
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk({"init/aide.bmd": fabriquer_msg1()})))
    return image


def _fichier_traduit(tmp_path, pages):
    script = msg1.lire_msg1(fabriquer_msg1())
    script.messages[0].pages = pages
    p = tmp_path / "TRADUITS" / "init" / "aide.bmd"
    p.parent.mkdir(parents=True)
    p.write_bytes(msg1.ecrire_msg1(script))
    return tmp_path / "TRADUITS"


def test_lire_table(tmp_path):
    (tmp_path / "t.txt").write_text(TABLE, encoding="utf-8")
    assert importer.lire_table(tmp_path / "t.txt") == {"ま": "à", "$": "è", "ら": "é"}


def test_import(tmp_path):
    (tmp_path / "t.txt").write_text(TABLE, encoding="utf-8")
    ma, ra = "ま".encode("cp932"), "ら".encode("cp932")
    dossier = _fichier_traduit(tmp_path, [b"\xf1\x41Voil" + ma + b" un r" + ra + b"ve!\n",
                                          b"\xf2\x05\xff\xffTr$s bien.\x00"])
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = tmp_path / "trad"
    commun.ecrire_json(trad / "systeme/init/aide.json", [
        {"id": "dlg_a", "locuteur": "Yosuke", "en": "Hello there!{PAGE}Bye.", "fr": ""},
        {"id": "sel_b", "choix": True, "en": "Yes{OPTION}No{OPTION}Maybe", "fr": ""}])
    bilan = importer.importer(dossier, importer.lire_table(tmp_path / "t.txt"), scripts, trad)
    entrees = commun.lire_json(trad / "systeme/init/aide.json")
    assert entrees[0]["fr"] == "Voilà un réve!{PAGE}Très bien."
    assert entrees[1]["fr"] == ""                    # inchangé chez lui : rien à importer
    assert bilan.importes == 1 and bilan.problemes == []


def test_ne_remplace_pas_une_traduction_existante(tmp_path):
    (tmp_path / "t.txt").write_text(TABLE, encoding="utf-8")
    dossier = _fichier_traduit(tmp_path, [b"\xf1\x41Salut!\n", b"\xf2\x05\xff\xffCiao.\x00"])
    scripts = catalogue.lire_scripts(_image(tmp_path))
    trad = tmp_path / "trad"
    commun.ecrire_json(trad / "systeme/init/aide.json", [
        {"id": "dlg_a", "en": "Hello there!{PAGE}Bye.", "fr": "Coucou !{PAGE}Salut."}])
    bilan = importer.importer(dossier, {}, scripts, trad)
    assert commun.lire_json(trad / "systeme/init/aide.json")[0]["fr"] == "Coucou !{PAGE}Salut."
    assert bilan.importes == 0 and len(bilan.problemes) == 1
