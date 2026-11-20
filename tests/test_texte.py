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


@pytest.mark.parametrize("page, attendu", [
    # le nom de l'ennemi inséré en tête doit rester déplaçable : « Des {f 2 4 0} apparaissent ! »
    (bytes.fromhex("f205ffff f141 f2440101") + b"s have appeared!\n\0", "{f 2 4 0}s have appeared!"),
    (bytes.fromhex("f205ffff f141 f2010301") + b"Support Skills" + bytes.fromhex("f2010101") + b" are...\0",
     "{f 0 1 2}Support Skills{f 0 1 0} are..."),
])
def test_codes_de_contenu_restent_visibles(page, attendu):
    prefixe, lisible, suffixe = texte.decouper_page(page)
    assert lisible == attendu
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


def test_accents_de_la_police():
    # La localisation anglaise a redessiné des symboles de la ligne 0x81 en lettres
    # accentuées : ※ (81A6) s'affiche É, 〒 (81A7) s'affiche é, etc.
    octets = (b"Caf" + bytes.fromhex("81a7") + b" cr" + bytes.fromhex("819a") + b"me "
              + bytes.fromhex("819c") + b" l'" + bytes.fromhex("81b8") + b"il, "
              + bytes.fromhex("81a6") + b"lodie " + bytes.fromhex("81a3") + b"a")
    assert texte.decoder_texte(octets) == "Café crème à l'œil, Élodie Ça"
    assert texte.encoder_texte("Café crème à l'œil, Élodie Ça") == octets


def test_symbole_redessine_relu_comme_accent():
    assert texte.decoder_texte(bytes.fromhex("81a6")) == "É"   # et non « ※ »


def test_paire_illisible():
    # Vu dans un fichier traduit avec PersonaEditor : « id[84 9E]e. » pour « idée. »
    octets = b"id" + bytes.fromhex("849e") + b"e."
    assert texte.decoder_texte(octets) == "id{0x84}{0x9E}e."
    assert texte.encoder_texte("id{0x84}{0x9E}e.") == octets


def test_balise_inconnue():
    with pytest.raises(texte.ErreurTexte, match="BIDULE"):
        texte.encoder_texte("Salut{BIDULE}")


def test_caractere_impossible():
    with pytest.raises(texte.ErreurTexte, match="ñ"):
        texte.encoder_texte("Señor")


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
