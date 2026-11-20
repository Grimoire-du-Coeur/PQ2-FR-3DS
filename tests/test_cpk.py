"""Lecture et patch du CPK (archive CRI qui contient tout le jeu)."""

import io

import pytest

import cpk
from fabrique import fabriquer_cpk

BRUT = b"MSG1 brut " * 10
COMPRESSE = bytes(range(256)) * 3


def _cpk(tmp_path):
    donnees = fabriquer_cpk({"a/x.bmd": BRUT, "b/y.bf": COMPRESSE}, compresses={"b/y.bf"})
    chemin = tmp_path / "data.cpk"
    chemin.write_bytes(donnees)
    return chemin, len(donnees)


def test_lit_un_fichier_brut_et_un_compresse(tmp_path):
    chemin, _ = _cpk(tmp_path)
    with open(chemin, "rb") as f:
        archive = cpk.Cpk(f)
        assert set(archive.entrees) == {"a/x.bmd", "b/y.bf"}
        assert archive.entrees["b/y.bf"].taille != archive.entrees["b/y.bf"].taille_extraite
        assert archive.entrees["a/x.bmd"].taille == archive.entrees["a/x.bmd"].taille_extraite
        assert archive.lire("a/x.bmd") == BRUT
        assert archive.lire("b/y.bf") == COMPRESSE


def test_lit_avec_un_decalage_de_base():
    donnees = fabriquer_cpk({"a/x.bmd": BRUT})
    archive = cpk.Cpk(io.BytesIO(b"\0" * 0x90 + donnees), base=0x90)
    assert archive.lire("a/x.bmd") == BRUT


def test_patch_remplace_et_relit(tmp_path):
    chemin, taille = _cpk(tmp_path)
    nouveau = b"traduction plus longue " * 50
    cpk.patcher_cpk(chemin, taille, {"a/x.bmd": nouveau})
    with open(chemin, "rb") as f:
        archive = cpk.Cpk(f)
        assert archive.lire("a/x.bmd") == nouveau
        assert archive.lire("b/y.bf") == COMPRESSE
        e = archive.entrees["a/x.bmd"]
        assert e.taille == e.taille_extraite == len(nouveau)
        assert e.decalage >= taille and e.decalage % 2048 == 0


def test_patch_remplace_un_fichier_compresse_par_du_brut(tmp_path):
    chemin, taille = _cpk(tmp_path)
    cpk.patcher_cpk(chemin, taille, {"b/y.bf": b"court"})
    with open(chemin, "rb") as f:
        assert cpk.Cpk(f).lire("b/y.bf") == b"court"


def test_patch_relance_ne_s_empile_pas(tmp_path):
    chemin, taille = _cpk(tmp_path)
    cpk.patcher_cpk(chemin, taille, {"a/x.bmd": b"premier essai " * 300})
    premier = chemin.stat().st_size
    cpk.patcher_cpk(chemin, taille, {"a/x.bmd": b"premier essai " * 300})
    assert chemin.stat().st_size == premier


def test_patch_sans_remplacement_rend_l_original(tmp_path):
    chemin, taille = _cpk(tmp_path)
    origine = chemin.read_bytes()
    cpk.patcher_cpk(chemin, taille, {"a/x.bmd": b"essai"})
    cpk.patcher_cpk(chemin, taille, {})
    assert chemin.read_bytes() == origine


def test_patch_chemin_inconnu(tmp_path):
    chemin, taille = _cpk(tmp_path)
    with pytest.raises(KeyError, match="c/inconnu.bmd"):
        cpk.patcher_cpk(chemin, taille, {"c/inconnu.bmd": b"x"})
