"""Scripts Atlus « FLW0 » (.bf) : remplacer le script de messages qu'ils portent.

Relevé sur les 1 632 .bf du jeu : un en-tête de 0x20 octets, puis des
en-têtes de section de 16 octets (type, taille d'un élément, nombre,
position), puis les sections, contiguës, dans l'ordre :

    0 procédures   1 étiquettes   2 code   3 messages (MSG1)   4 chaînes

La section 3 contient le script MSG1 tel quel (472 fichiers l'ont vide).
Le champ u32 à +0x04 de l'en-tête vaut la position de la section 4. Certains
fichiers portent quelques octets après la dernière section : on les garde.

Le code (section 2) désigne les messages par leur numéro, pas par leur
position : changer la taille de la section 3 ne demande que de décaler les
sections suivantes.
"""

from __future__ import annotations

import struct

SECTION_MESSAGES = 3


def _sections(bf: bytes) -> list[list[int]]:
    if bf[8:12] != b"FLW0":
        raise ValueError("script FLW0 attendu")
    (nombre,) = struct.unpack_from("<I", bf, 0x10)
    return [list(struct.unpack_from("<IIII", bf, 0x20 + 16 * i)) for i in range(nombre)]


def _indice_messages(sections: list[list[int]]) -> int:
    for i, s in enumerate(sections):
        if s[0] == SECTION_MESSAGES:
            return i
    raise ValueError("script FLW0 sans section de messages")


def extraire_messages(bf: bytes) -> bytes | None:
    """Le script MSG1 du fichier, ou None s'il n'en a pas."""
    sections = _sections(bf)
    _, taille, nombre, position = sections[_indice_messages(sections)]
    if nombre == 0:
        return None
    return bf[position:position + taille * nombre]


def remplacer_messages(bf: bytes, msg1: bytes) -> bytes:
    """Le même fichier, avec ``msg1`` comme script de messages."""
    sections = _sections(bf)
    i = _indice_messages(sections)
    _, taille, nombre, position = sections[i]
    if taille != 1:
        raise ValueError(f"section de messages à éléments de {taille} octets, 1 attendu")
    fin = position + nombre
    ecart = len(msg1) - nombre
    sortie = bytearray(bf[:position] + msg1 + bf[fin:])

    sections[i][2] = len(msg1)
    for j, s in enumerate(sections):
        if j > i and s[3] >= fin:
            s[3] += ecart
    for j, s in enumerate(sections):
        struct.pack_into("<IIII", sortie, 0x20 + 16 * j, *s)
    (repere,) = struct.unpack_from("<I", bf, 4)
    if repere >= fin:
        struct.pack_into("<I", sortie, 4, repere + ecart)
    return bytes(sortie)
