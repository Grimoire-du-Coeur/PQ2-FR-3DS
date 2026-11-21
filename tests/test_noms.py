"""Tables de noms à cases fixes : objets (init/itemtbl.bin), lieux (camp/dictionary.tbl)."""

import pytest

import noms

T = noms.OBJETS


def _table(*liste):
    zone = b"".join(n.encode("ascii").ljust(T.case, b"\0") for n in liste)
    avant = b"\xaa" * T.debut
    return avant + zone.ljust(T.fin - T.debut, b"\0")


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
    assert nouveau[:T.debut] == brut[:T.debut]                       # rien d'autre ne bouge


def test_nom_trop_long():
    brut = _table("Medicine")
    with pytest.raises(noms.ErreurNom, match="Médicament à usage très spécial"):
        noms.ecrire_noms(brut, {"Medicine": "Médicament à usage très spécial"})


def test_accent_compte_double():
    assert noms.longueur("Ébène") == 7          # É et è font deux octets chacun


def _fiches(*liste):
    """camp/dictionary.tbl : 152 fiches de 60 octets, nom à +8, drapeaux à +30."""
    fiches = []
    for k in range(noms.LIEUX.nombre):
        nom = liste[k % len(liste)].encode("ascii")
        fiches.append(b"\0\0\0\0\x01\x00\x04\x01" + nom.ljust(22, b"\0") + b"\x01\0" + bytes(28))
    return b"".join(fiches)


def test_lieux():
    brut = _fiches("1st Ave.~", "Kamoshida Square", "1st Ave.~")
    assert len(brut) == noms.LIEUX.fin
    assert noms.noms_a_traduire(brut, noms.LIEUX) == ["1st Ave.~", "Kamoshida Square"]
    nouveau = noms.ecrire_noms(brut, {"Kamoshida Square": "Place Kamoshida"}, noms.LIEUX)
    assert noms.lire_noms(nouveau, noms.LIEUX)[:3] == ["1st Ave.~", "Place Kamoshida", "1st Ave.~"]
    assert nouveau[60 + 30] == 1                                    # les drapeaux restent
    with pytest.raises(noms.ErreurNom, match="19"):
        noms.ecrire_noms(brut, {"Kamoshida Square": "Grand-place de Kamoshida"}, noms.LIEUX)
