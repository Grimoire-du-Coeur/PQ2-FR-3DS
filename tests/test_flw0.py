"""Scripts FLW0 (.bf) : on n'y touche qu'à la section des messages."""

import struct

import flw0
from fabrique import fabriquer_bf, fabriquer_msg1

MSG = fabriquer_msg1()


def _sections(bf):
    return [struct.unpack_from("<IIII", bf, 0x20 + 16 * i) for i in range(5)]


def test_extraire():
    assert flw0.extraire_messages(fabriquer_bf(MSG)) == MSG


def test_remplacer_par_le_meme():
    bf = fabriquer_bf(MSG, queue=b"\0" * 7)
    assert flw0.remplacer_messages(bf, flw0.extraire_messages(bf)) == bf


def test_remplacer_plus_long():
    bf = fabriquer_bf(MSG, queue=b"QUEUE")
    nouveau = MSG + b"\0" * 40              # un script plus long de 40 octets
    resultat = flw0.remplacer_messages(bf, nouveau)
    avant, apres = _sections(bf), _sections(resultat)
    assert apres[3][2] == len(nouveau)
    assert apres[4][3] == avant[4][3] + 40
    assert struct.unpack_from("<I", resultat, 4)[0] == apres[4][3]
    assert resultat[apres[4][3]:apres[4][3] + 8] == b"bonjour\0"
    assert resultat.endswith(b"QUEUE")
    assert apres[:3] == avant[:3]
    assert flw0.extraire_messages(resultat) == nouveau


def test_section_vide():
    bf = fabriquer_bf(None)
    assert flw0.extraire_messages(bf) is None
    resultat = flw0.remplacer_messages(bf, MSG)
    assert flw0.extraire_messages(resultat) == MSG
    apres = _sections(resultat)
    assert resultat[apres[4][3]:apres[4][3] + 8] == b"bonjour\0"


def test_refuse_autre_chose():
    try:
        flw0.extraire_messages(MSG)
    except ValueError as e:
        assert "FLW0" in str(e)
    else:
        raise AssertionError("un MSG1 n'est pas un FLW0")
