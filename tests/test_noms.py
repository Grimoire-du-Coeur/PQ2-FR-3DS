"""Noms des objets et équipements (init/itemtbl.bin, cases de 22 octets)."""

import pytest

import noms


def _table(*liste):
    zone = b"".join(n.encode("ascii").ljust(noms.CASE, b"\0") for n in liste)
    avant = b"\xaa" * noms.ZONE_DEBUT
    return avant + zone.ljust(noms.ZONE_FIN - noms.ZONE_DEBUT, b"\0")


def test_lire_les_noms():
    brut = _table("NULL", "Rebel Knife", "Not Used", "Medicine", "Medicine", "Acc 0x4FF", "0x623",
                  "Expendables Start", "Acc2 From Here", "(prov) Fist 1", "Not Used 80D", "???",
                  "Sell all materials")
    assert noms.noms_a_traduire(brut) == ["Rebel Knife", "Medicine", "Sell all materials"]


def test_autre_version_refusee():
    with pytest.raises(noms.ErreurNom, match="autre version"):
        noms.lire_noms(_table("NULL") + b"\0")


def test_ecrire_un_nom_dans_toutes_ses_cases():
    brut = _table("Medicine", "Rebel Knife", "Medicine")
    nouveau = noms.ecrire_noms(brut, {"Medicine": "Médicament"})
    assert noms.lire_noms(nouveau)[:3] == ["Médicament", "Rebel Knife", "Médicament"]
    assert len(nouveau) == len(brut)
    assert nouveau[:noms.ZONE_DEBUT] == brut[:noms.ZONE_DEBUT]       # rien d'autre ne bouge


def test_nom_trop_long():
    brut = _table("Medicine")
    with pytest.raises(noms.ErreurNom, match="Médicament à usage très spécial"):
        noms.ecrire_noms(brut, {"Medicine": "Médicament à usage très spécial"})


def test_accent_compte_double():
    assert noms.longueur("Ébène") == 7          # É et è font deux octets chacun
