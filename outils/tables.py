"""Tables de noms du combat : compétences, Personas, ennemis.

    battle/table/skillnametable.tbl    → trad/noms/competences.json
    battle/table/personanametable.tbl  → trad/noms/personas.json
    battle/table/enemynametable.tbl    → trad/noms/ennemis.json

Format : un u16, le nombre de noms ; autant de positions u16 ; puis les noms
à la suite, terminés par un zéro. skillnametable donne la position du début
de chaque nom, les deux autres celle de sa fin. Les positions comptent
depuis le premier nom : la zone des noms tient 65 535 octets, assez pour
des noms plus longs qu'en anglais (15 743 octets pour les compétences).

98 compétences portent le nom d'un objet (« Rudra Ring », l'effet de
l'accessoire) : elles ne sont pas extraites et reprennent la traduction de
trad/noms/objets.json.

Les autres tables de ce format (objets, quêtes, attractions…) sont restées
en japonais : le jeu ne les affiche pas. Relevé sur la version européenne
le 21/11/2026.
"""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass

import texte

COMPETENCES = "battle/table/skillnametable.tbl"
TABLES = {
    COMPETENCES: "noms/competences.json",
    "battle/table/personanametable.tbl": "noms/personas.json",
    "battle/table/enemynametable.tbl": "noms/ennemis.json",
}
_MAX = 0xFFFF

# Cases vides ou réservées, jamais affichées.
_FACTICE = re.compile(r"^(blank|reserve( skill)?|reserved|dummy|null|not used.*|unused)$", re.IGNORECASE)


class ErreurTable(ValueError):
    pass


@dataclass
class TableNoms:
    noms: list[str]
    debuts: bool            # positions de début (sinon : de fin) de chaque nom


def lire_table(brut: bytes) -> TableNoms:
    if len(brut) < 4:
        raise ErreurTable("table de noms trop courte")
    n = struct.unpack_from("<H", brut, 0)[0]
    if n == 0 or 2 + 2 * n > len(brut):
        raise ErreurTable(f"table de noms illisible ({n} noms annoncés)")
    positions = struct.unpack_from(f"<{n}H", brut, 2)
    zone = brut[2 + 2 * n:]
    debuts = positions[0] == 0
    bornes = [*positions, len(zone)] if debuts else [0, *positions]
    morceaux = [zone[a:b] for a, b in zip(bornes, bornes[1:])]
    if bornes[-1] != len(zone) or not all(m.endswith(b"\0") and b"\0" not in m[:-1] for m in morceaux):
        raise ErreurTable("table de noms illisible (positions incohérentes)")
    return TableNoms([texte.decoder_texte(m[:-1]) for m in morceaux], debuts)


def ecrire_table(t: TableNoms) -> bytes:
    codes = [texte.encoder_texte(nom) + b"\0" for nom in t.noms]
    positions, p = [], 0
    for c in codes:
        positions.append(p if t.debuts else p + len(c))
        p += len(c)
    if p > _MAX:
        raise ErreurTable(f"{p} octets de noms : la table en tient 65 535")
    return struct.pack(f"<{len(codes) + 1}H", len(codes), *positions) + b"".join(codes)


def noms_a_traduire(brut: bytes, exclus: set[str] | frozenset[str] = frozenset()) -> list[str]:
    """Les noms à traduire, sans doublon, dans l'ordre de la table."""
    return list(dict.fromkeys(n for n in lire_table(brut).noms
                              if texte.est_a_traduire(n) and not _FACTICE.match(n) and n not in exclus))


def traduire(brut: bytes, traductions: dict[str, str]) -> bytes:
    t = lire_table(brut)
    t.noms = [texte.adapter(traductions[n]) if traductions.get(n) else n for n in t.noms]
    return ecrire_table(t)
