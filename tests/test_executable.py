"""Textes de l'exécutable (executable.py), décompression BLZ et lecture de l'ExeFS."""

import struct

import pytest

import blz
import executable
import rom3ds
import texte
from fabrique import fabriquer_3ds, fabriquer_blz, fabriquer_code, fabriquer_cpk

DEBUT = b"\xf2\x05\xff\xff\xf1A"
MESSAGES = [DEBUT + b"Save endgame data?\n",
            b"\x81\x40\nResume the game from here?\n",
            DEBUT + b"Yes\nNo\n"]


def _pointeur(code, d, k):
    return struct.unpack_from("<I", code, d.table + 8 * k)[0] - executable.BASE


def _message(code, d, k):
    p = _pointeur(code, d, k)
    return code[p:code.index(b"\0", p)]


def test_entrees():
    code, d = fabriquer_code(MESSAGES)
    assert executable.entrees(code, d) == [
        {"id": "000", "en": "Save endgame data?"},
        {"id": "001", "en": "Resume the game from here?"},
        {"id": "002", "en": "Yes{SAUT}No"}]


def test_sans_traduction_rien_ne_change():
    code, d = fabriquer_code(MESSAGES)
    assert executable.traduire(code, {}, d) == code
    tout = {e["id"]: e["en"] for e in executable.entrees(code, d)}
    assert executable.traduire(code, tout, d) == code


def test_traduction_plus_longue_deborde_dans_la_marge():
    code, d = fabriquer_code(MESSAGES)
    nouveau = executable.traduire(code, {"000": "Sauvegarder les données de fin de partie ?",
                                         "002": "Oui{SAUT}Non"}, d)
    assert len(nouveau) == len(code)
    lus = {k: _message(nouveau, d, k) for k in range(3)}
    assert lus[0] == DEBUT + texte.encoder_texte("Sauvegarder les données de fin de partie ?") + b"\n"
    assert lus[1] == MESSAGES[1]                        # non traduit : même texte
    assert lus[2] == DEBUT + b"Oui\nNon\n"
    marge = d.marges[0]
    assert any(marge[0] <= _pointeur(nouveau, d, k) < marge[1] for k in range(3))
    # Les deux u16 de chaque entrée ne bougent pas.
    assert all(nouveau[d.table + 8 * k + 4:d.table + 8 * k + 8] == code[d.table + 8 * k + 4:d.table + 8 * k + 8]
               for k in range(3))


def test_trop_long():
    code, d = fabriquer_code(MESSAGES, marge=0x10)
    with pytest.raises(executable.ErreurExecutable, match="octets de trop"):
        executable.traduire(code, {"000": "x" * 200}, d)


def test_autre_version():
    code, d = fabriquer_code(MESSAGES)
    with pytest.raises(executable.ErreurExecutable, match="autre version"):
        executable.lire_messages(code + b"\0", d)


def test_ips():
    code, d = fabriquer_code(MESSAGES)
    nouveau = executable.traduire(code, {"002": "Oui{SAUT}Non"}, d)
    patch = executable.ips(code, nouveau)
    assert patch.startswith(b"PATCH") and patch.endswith(b"EOF")
    assert executable.appliquer_ips(code, patch) == nouveau
    assert executable.ips(code, code) == b"PATCHEOF"


def test_blz():
    clair = b"en-tete non compresse " + b"Persona Q2, cinema " * 40
    compresse = fabriquer_blz(clair, non_compresse=22)
    assert len(compresse) < len(clair)
    assert blz.decompresser(compresse) == clair


def test_blz_abime():
    with pytest.raises(blz.ErreurBlz):
        blz.decompresser(b"\0" * 4)


@pytest.mark.parametrize("compresse", [False, True])
def test_lire_code(tmp_path, compresse):
    clair = b"code " * 300
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(fabriquer_cpk({"init/x.bin": b"x"}),
                                    code=fabriquer_blz(clair, 16) if compresse else clair,
                                    code_compresse=compresse))
    assert rom3ds.lire_code(image) == clair


def test_data_cpk_seul_n_a_pas_de_code(tmp_path):
    cpk = tmp_path / "data.cpk"
    cpk.write_bytes(fabriquer_cpk({"init/x.bin": b"x"}))
    with pytest.raises(rom3ds.PasDeCode):
        rom3ds.lire_code(cpk)
