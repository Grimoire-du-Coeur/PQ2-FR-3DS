"""Scripts de messages Atlus « MSG1 » : fichiers .bmd, et section 3 des .bf.

Disposition relevée sur les 1 304 scripts du jeu (positions relatives à 0x20,
sauf l'en-tête) :

    0x00  en-tête : type u8 (7), compression u8, utilisateur u16, taille u32,
          "MSG1", 0 u32, position de la table de relocation u32 (absolue),
          sa taille u32, nombre de messages u32, 0 u16, version u16 (2)
    0x20  table des messages : (type u32, position u32) par message,
          type 0 = message, 1 = choix
    ....  en-tête des locuteurs : (position des pointeurs u32, nombre u32, 0, 0)
    ....  les messages, chacun aligné sur 4 :
            nom (24 octets)
            message : u16 pages, u16 locuteur (0xFFFF = aucun)
            choix   : u16 champ, u16 options, u16 champ, u16 champ
            positions des pages (u32), taille du texte u32, texte
    ....  pointeurs des locuteurs (alignés sur 4), puis leurs noms, terminés par 0
    ....  table de relocation (alignée sur 4), fin du fichier

La table de relocation liste, dans l'ordre, l'emplacement de chaque pointeur
du fichier (voir ``encoder_relocation``).

Le texte des pages reste ici en octets bruts : les codes de fonction (octets
0xF0 et plus) et l'encodage sont l'affaire de l'extraction.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field

BASE = 0x20
AUCUN_LOCUTEUR = 0xFFFF
_SERIE_MAX = 33                  # (0xFF >> 3) + 2


def decoder_relocation(table: bytes) -> list[int]:
    """Emplacements des pointeurs (relatifs à 0x20) décrits par la table.

    - octet pair ``b`` : pointeur suivant à ``2*b`` octets ;
    - octet impair avec ``b & 7 == 7`` : ``(b >> 3) + 2`` pointeurs, chacun à +4 ;
    - autre octet impair : valeur 16 bits ``v`` sur deux octets, écart ``v - 1``.
    """
    positions = []
    pos = 0
    i = 0
    while i < len(table):
        b = table[i]
        if b % 2 == 0:
            pos += 2 * b
            positions.append(pos)
        elif b & 7 == 7:
            for _ in range((b >> 3) + 2):
                pos += 4
                positions.append(pos)
        else:
            v = b | table[i + 1] << 8
            i += 1
            pos += v - 1
            positions.append(pos)
        i += 1
    return positions


def encoder_relocation(positions: list[int]) -> bytes:
    """Inverse de ``decoder_relocation``, avec les choix de l'encodeur d'Atlus."""
    ecarts = []
    precedent = 0
    for p in positions:
        e = p - precedent
        if e <= 0 or e % 2:
            raise ValueError(f"emplacement de pointeur invalide : {p} après {precedent}")
        ecarts.append(e)
        precedent = p
    sortie = bytearray()
    i = 0
    while i < len(ecarts):
        serie = 0
        while i + serie < len(ecarts) and ecarts[i + serie] == 4 and serie < _SERIE_MAX:
            serie += 1
        if serie >= 2:
            sortie.append((serie - 2) << 3 | 7)
            i += serie
            continue
        e = ecarts[i]
        if e <= 0x1FC:
            sortie.append(e // 2)
        elif e + 1 <= 0xFFFF:
            sortie += struct.pack("<H", e + 1)
        else:
            raise ValueError(f"écart trop grand entre deux pointeurs : {e}")
        i += 1
    return bytes(sortie)


@dataclass
class Message:
    nom: str
    choix: bool
    locuteur: int                     # message : n° de locuteur ; choix : champ +0x18
    pages: list[bytes]
    nom_brut: bytes = b""             # 24 octets d'origine, réécrits si le nom n'a pas changé
    champs_choix: tuple[int, int] = (0, 0)


@dataclass
class ScriptMessages:
    entete: bytes                     # 0x20 octets d'origine ; les champs calculés sont réécrits
    messages: list[Message]
    locuteurs: list[bytes]
    reste: bytes = field(default=b"")  # octets après le script (bourrage de section d'un .bf)


def _a4(n: int) -> int:
    return (n + 3) // 4 * 4


def lire_msg1(donnees: bytes) -> ScriptMessages:
    if donnees[8:12] != b"MSG1":
        raise ValueError("script MSG1 attendu")
    (taille,) = struct.unpack_from("<I", donnees, 4)
    (nombre,) = struct.unpack_from("<I", donnees, 0x18)
    messages = []
    for k in range(nombre):
        type_, pos = struct.unpack_from("<II", donnees, BASE + 8 * k)
        p = BASE + pos
        nom_brut = donnees[p:p + 24]
        if type_ == 0:
            n, locuteur = struct.unpack_from("<HH", donnees, p + 24)
            champs = (0, 0)
            q = p + 28
        elif type_ == 1:
            locuteur, n, c1, c2 = struct.unpack_from("<HHHH", donnees, p + 24)
            champs = (c1, c2)
            q = p + 32
        else:
            raise ValueError(f"message {k} : type {type_} inconnu")
        debuts = list(struct.unpack_from(f"<{n}I", donnees, q))
        q += 4 * n
        (taille_texte,) = struct.unpack_from("<I", donnees, q)
        fin_texte = q + 4 + taille_texte
        bornes = [BASE + d for d in debuts] + [fin_texte]
        pages = [donnees[bornes[i]:bornes[i + 1]] for i in range(n)]
        messages.append(Message(nom_brut.split(b"\0")[0].decode("ascii", "replace"),
                                type_ == 1, locuteur, pages, nom_brut, champs))
    pos_loc, n_loc = struct.unpack_from("<II", donnees, BASE + 8 * nombre)
    locuteurs = []
    for j in range(n_loc):
        (o,) = struct.unpack_from("<I", donnees, BASE + pos_loc + 4 * j)
        debut = BASE + o
        locuteurs.append(donnees[debut:donnees.index(b"\0", debut)])
    return ScriptMessages(donnees[:BASE], messages, locuteurs, donnees[taille:])


def ecrire_msg1(script: ScriptMessages) -> bytes:
    n = len(script.messages)
    table = bytearray()
    corps = bytearray()
    pointeurs = []                            # emplacements relatifs à BASE
    debut_corps = 8 * n + 16

    def position() -> int:
        return debut_corps + len(corps)

    for k, m in enumerate(script.messages):
        corps.extend(bytes(_a4(position()) - position()))
        p = position()
        pointeurs.append(8 * k + 4)
        table += struct.pack("<II", 1 if m.choix else 0, p)
        if m.nom_brut and m.nom_brut.split(b"\0")[0].decode("ascii", "replace") == m.nom:
            nom = m.nom_brut
        else:
            nom = m.nom.encode("ascii").ljust(24, b"\0")
        if m.choix:
            tete = nom + struct.pack("<HHHH", m.locuteur, len(m.pages), *m.champs_choix)
        else:
            tete = nom + struct.pack("<HH", len(m.pages), m.locuteur)
        texte_pos = p + len(tete) + 4 * len(m.pages) + 4
        debuts = []
        o = texte_pos
        for i, page in enumerate(m.pages):
            pointeurs.append(p + len(tete) + 4 * i)
            debuts.append(o)
            o += len(page)
        texte = b"".join(m.pages)
        corps += tete + struct.pack(f"<{len(debuts)}I", *debuts) + struct.pack("<I", len(texte))
        corps += texte

    corps.extend(bytes(_a4(position()) - position()))
    pos_loc = position()
    if script.locuteurs:
        noms_pos = pos_loc + 4 * len(script.locuteurs)
        o = noms_pos
        for j, nom in enumerate(script.locuteurs):
            pointeurs.append(pos_loc + 4 * j)
            corps += struct.pack("<I", o)
            o += len(nom) + 1
        for nom in script.locuteurs:
            corps += nom + b"\0"
        corps.extend(bytes(_a4(position()) - position()))
    pointeurs.append(8 * n)                   # position des pointeurs de locuteurs
    pointeurs.sort()

    relocation = encoder_relocation(pointeurs)
    pos_relocation = BASE + position()
    total = pos_relocation + len(relocation)
    entete = bytearray(script.entete)
    struct.pack_into("<I", entete, 4, total)
    struct.pack_into("<III", entete, 0x10, pos_relocation, len(relocation), n)
    return (bytes(entete) + bytes(table) + struct.pack("<IIII", pos_loc, len(script.locuteurs), 0, 0)
            + bytes(corps) + relocation + script.reste)
