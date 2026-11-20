"""Le texte d'une page, tel que le traducteur le voit."""

import pytest

import texte

ENTETE = bytes.fromhex("f205ffff f141 f5861a01010101010101")
PAGE = ENTETE + b"Ngh!\nOw." + bytes.fromhex("0a f2230000 f121 00")


def test_page_typique():
    prefixe, lisible, suffixe = texte.decouper_page(PAGE)
    assert prefixe == ENTETE
    assert lisible == "Ngh!{SAUT}Ow."
    assert suffixe == bytes.fromhex("0a f2230000 f121 00")


def test_espaces_japonaises_en_tete():
    page = bytes.fromhex("f205ffff f141 8140 8140 0a f5610201010101010101") + b"Hi." + b"\0"
    prefixe, lisible, suffixe = texte.decouper_page(page)
    assert lisible == "Hi."
    assert prefixe + texte.encoder_texte(lisible) + suffixe == page


def test_code_au_milieu():
    assert texte.decoder_texte(bytes.fromhex("f2010301")) == "{f 0 1 2}"
    assert texte.decoder_texte(bytes.fromhex("f2010101")) == "{f 0 1 0}"
    assert texte.decoder_texte(bytes.fromhex("f2230000")) == "{f 1 3 65535}"
    assert texte.decoder_texte(bytes.fromhex("f141")) == "{f 2 1}"
    assert texte.encoder_texte("{f 0 1 2}") == bytes.fromhex("f2010301")
    assert texte.encoder_texte("{f 1 3 65535}") == bytes.fromhex("f2230000")


def test_shift_jis():
    assert texte.decoder_texte(bytes.fromhex("8163")) == "…"
    assert texte.decoder_texte(bytes.fromhex("8140")) == "　"
    assert texte.encoder_texte("“Yes…”") == bytes.fromhex("8167") + b"Yes" + bytes.fromhex("81638168")


@pytest.mark.parametrize("page", [
    PAGE,
    bytes.fromhex("f205ffff f141") + b"The Support Skill " + bytes.fromhex("f2010301")
    + b"Hikari's Cheer" + bytes.fromhex("f2010101") + b"\nhas been added.\n" + bytes.fromhex("f121 00"),
    bytes.fromhex("f205ffff f141 f1210000"),
    b"",
])
def test_recollage(page):
    prefixe, lisible, suffixe = texte.decouper_page(page)
    assert prefixe + texte.encoder_texte(lisible) + suffixe == page


def test_balise_inconnue():
    with pytest.raises(texte.ErreurTexte, match="BIDULE"):
        texte.encoder_texte("Salut{BIDULE}")


def test_caractere_impossible():
    with pytest.raises(texte.ErreurTexte, match="é"):
        texte.encoder_texte("Café")


def test_separateur_dans_une_page():
    with pytest.raises(texte.ErreurTexte, match="PAGE"):
        texte.encoder_texte("Un{PAGE}Deux")


@pytest.mark.parametrize("lisible, attendu", [
    ("Hello", True),
    ("I obtained {f 3 5 1}.", True),
    ("アクセサリー２　0xC10　１行目", False),
    ("!?", False),
    ("{f 0 1 2}A{f 0 1 0}", False),
])
def test_a_traduire(lisible, attendu):
    assert texte.est_a_traduire(lisible) is attendu
