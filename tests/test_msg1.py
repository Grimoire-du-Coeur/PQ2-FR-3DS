"""Scripts de messages MSG1 (.bmd, et section 3 des .bf)."""

import msg1
from fabrique import fabriquer_msg1

# Début réel de la table de relocation de battle/combination/msg_POEM.bmd :
# un écart de 4, deux de 8, un de 44, une série de quatre écarts de 4, un
# écart de 480, puis 4, 284, 4.
POEM = bytes.fromhex("0204041617f0028e02")
POEM_POSITIONS = [4, 12, 20, 64, 68, 72, 76, 80, 560, 564, 848, 852]


def test_relocation_cas_du_jeu():
    assert msg1.decoder_relocation(POEM) == POEM_POSITIONS
    assert msg1.encoder_relocation(POEM_POSITIONS) == POEM


def test_relocation_grand_ecart():
    positions = [4, 4 + 0x400, 4 + 0x400 + 0x1FC]
    table = msg1.encoder_relocation(positions)
    assert len(table) == 4                       # 1 + 2 + 1 octets
    assert msg1.decoder_relocation(table) == positions


def test_relocation_longue_serie():
    positions = [4 * (i + 1) for i in range(40)]    # 40 écarts de 4 : 33 + 7
    table = msg1.encoder_relocation(positions)
    assert msg1.decoder_relocation(table) == positions
    assert table == bytes([0xFF, 0x2F])             # séries de 33 et de 7


def test_lecture():
    script = msg1.lire_msg1(fabriquer_msg1())
    a, b = script.messages
    assert (a.nom, a.choix, a.locuteur) == ("dlg_a", False, 0)
    assert a.pages == [b"\xf1\x41Hello there!\n", b"\xf2\x05\xff\xffBye.\x00"]
    assert (b.nom, b.choix) == ("sel_b", True)
    assert b.pages == [b"Yes\x00", b"No\x00", b"Maybe\x00"]
    assert script.locuteurs == [b"Yosuke"]


def test_aller_retour_msg1():
    origine = fabriquer_msg1()
    assert msg1.ecrire_msg1(msg1.lire_msg1(origine)) == origine


def test_page_plus_longue():
    script = msg1.lire_msg1(fabriquer_msg1())
    script.messages[0].pages[0] = b"\xf1\x41Salut, toi ! Comment vas-tu ?\n"
    relu = msg1.lire_msg1(msg1.ecrire_msg1(script))
    assert relu.messages[0].pages[0] == b"\xf1\x41Salut, toi ! Comment vas-tu ?\n"
    assert relu.messages[0].pages[1] == b"\xf2\x05\xff\xffBye.\x00"
    assert relu.messages[1].pages == [b"Yes\x00", b"No\x00", b"Maybe\x00"]
    assert relu.locuteurs == [b"Yosuke"]


def test_pages_ajoutees():
    script = msg1.lire_msg1(fabriquer_msg1())
    script.messages[0].pages.append(b"Une page de plus.\x00")
    relu = msg1.lire_msg1(msg1.ecrire_msg1(script))
    assert len(relu.messages[0].pages) == 3


def test_message_en_double():
    # Deux fichiers du jeu (btlEvent614.bf, e813_040.bf) ont deux lignes de table
    # qui pointent sur le même message ; l'ancien message reste dans le fichier,
    # inaccessible. On le reproduit en faisant pointer « sel_b » sur « dlg_a ».
    import struct
    origine = bytearray(fabriquer_msg1())
    struct.pack_into("<II", origine, 0x28, *struct.unpack_from("<II", origine, 0x20))
    script = msg1.lire_msg1(bytes(origine))
    assert script.messages[0].pages == script.messages[1].pages
    reecrit = msg1.ecrire_msg1(script)
    relu = msg1.lire_msg1(reecrit)
    assert [m.pages for m in relu.messages] == [m.pages for m in script.messages]
    assert msg1.ecrire_msg1(relu) == reecrit       # réécriture stable


def test_octets_apres_le_script_conserves():
    origine = fabriquer_msg1() + b"\0" * 12          # bourrage de section dans un .bf
    script = msg1.lire_msg1(origine)
    assert script.reste == b"\0" * 12
    assert msg1.ecrire_msg1(script) == origine
