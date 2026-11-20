"""Retrouver data.cpk dans l'image 3DS du joueur."""

import pytest

import rom3ds
from fabrique import fabriquer_3ds, fabriquer_cpk

CPK = fabriquer_cpk({"a/x.bmd": b"bonjour"})


def test_trouve_data_cpk_dans_une_image(tmp_path):
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(CPK))
    decalage, taille = rom3ds.localiser_data_cpk(image)
    assert taille == len(CPK)
    with open(image, "rb") as f:
        f.seek(decalage)
        assert f.read(taille) == CPK


def test_accepte_un_cpk_seul(tmp_path):
    seul = tmp_path / "data.cpk"
    seul.write_bytes(CPK)
    assert rom3ds.localiser_data_cpk(seul) == (0, len(CPK))


def test_image_chiffree(tmp_path):
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(CPK, chiffre=True))
    with pytest.raises(rom3ds.ErreurImage, match="chiffrée.*GodMode9"):
        rom3ds.localiser_data_cpk(image)


def test_autre_region(tmp_path):
    image = tmp_path / "jeu.3ds"
    image.write_bytes(fabriquer_3ds(CPK, title_id=0x0004000000123400))
    with pytest.raises(rom3ds.ErreurImage, match="0004000000123400"):
        rom3ds.localiser_data_cpk(image)


def test_format_inconnu(tmp_path):
    autre = tmp_path / "jeu.zip"
    autre.write_bytes(b"PK\3\4" + bytes(0x400))
    with pytest.raises(rom3ds.ErreurImage, match="non reconnu"):
        rom3ds.localiser_data_cpk(autre)
