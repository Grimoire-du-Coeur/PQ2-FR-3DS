"""Compression CRILAYLA, utilisée par 7 816 des 8 923 fichiers du CPK."""

import random

import pytest

import crilayla


@pytest.mark.parametrize("taille", [0x100, 0x101, 5000])
def test_aller_retour_litteral(taille):
    alea = random.Random(taille)
    donnees = bytes(alea.randrange(256) for _ in range(taille))
    bloc = crilayla.compresser_litteral(donnees)
    assert bloc[:8] == b"CRILAYLA"
    assert crilayla.decompresser(bloc) == donnees


def test_reference_arriere():
    # Bloc écrit à la main : 0x100 octets bruts « A », puis une partie compressée
    # de 6 octets « xyzxyz » codée comme 3 littéraux suivis d'une référence de
    # longueur 3, distance 3. Le flux se lit à rebours, en partant de la fin.
    bits = "0" + format(ord("z"), "08b")   # dernier octet d'abord
    bits += "0" + format(ord("y"), "08b")
    bits += "0" + format(ord("x"), "08b")
    bits += "1" + format(0, "013b") + "00"  # distance 0+3, longueur 3+0
    bits += "0" * (-len(bits) % 8)
    flux = bytes(int(bits[i:i + 8], 2) for i in range(0, len(bits), 8))[::-1]
    entete_brut = b"A" * 0x100
    bloc = (b"CRILAYLA" + (6).to_bytes(4, "little") + len(flux).to_bytes(4, "little")
            + flux + entete_brut)
    assert crilayla.decompresser(bloc) == entete_brut + b"xyzxyz"


def test_refuse_sans_signature():
    with pytest.raises(ValueError, match="CRILAYLA"):
        crilayla.decompresser(b"PASCRILA" + bytes(0x200))
