"""Archives Atlus PAK (.arc) : 323 dans le jeu, 40 contiennent des scripts."""

import pytest

import pak
from fabrique import fabriquer_pak

FICHIERS = [("msg_weapon.bmd", b"MSG1 " * 9), ("weapon.bf", b"FLW0" * 3), ("vide.bin", b"")]


def test_lire():
    assert pak.lire_pak(fabriquer_pak(FICHIERS)) == FICHIERS


def test_aller_retour():
    brut = fabriquer_pak(FICHIERS)
    assert pak.ecrire_pak(pak.lire_pak(brut)) == brut


def test_remplacer_une_entree():
    brut = fabriquer_pak(FICHIERS)
    nouveau = pak.remplacer(brut, {"weapon.bf": b"FLW0 plus long"})
    assert pak.lire_pak(nouveau) == [FICHIERS[0], ("weapon.bf", b"FLW0 plus long"), FICHIERS[2]]


def test_entree_inconnue():
    with pytest.raises(KeyError, match="absent.bmd"):
        pak.remplacer(fabriquer_pak(FICHIERS), {"absent.bmd": b""})


def test_pas_une_archive():
    assert pak.est_pak(fabriquer_pak(FICHIERS))
    assert not pak.est_pak(b"CPK \0\0\0\0" + bytes(64))
