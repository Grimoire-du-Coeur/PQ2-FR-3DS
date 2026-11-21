"""Noms des objets et des équipements : init/itemtbl.bin.

La fin de ce fichier est une table de 3 584 cases de 22 octets, une par
numéro d'objet (0x000 à 0xDFF) : le nom en ASCII, terminé par un zéro et
complété de zéros. Les menus, les boutiques et les dialogues (« Tu as
obtenu… ») y lisent le nom d'un objet.

Un même nom revient parfois dans plusieurs cases (« Medicine », « Shining
Film »…) : il se traduit une seule fois, dans trad/noms/objets.json, et
part dans toutes ses cases. Chaque case tient 21 octets ; une lettre
accentuée en prend deux (voir police/caracteres.json).

Relevé sur la version européenne le 21/11/2026.
"""

from __future__ import annotations

import re
from pathlib import Path

import texte
from cpk import Cpk
from rom3ds import localiser_data_cpk

CHEMIN = "init/itemtbl.bin"
TRAD = "noms/objets.json"
CASE = 22
NOMBRE = 0xE00
ZONE_DEBUT = 0x065820
ZONE_FIN = ZONE_DEBUT + NOMBRE * CASE      # la table finit le fichier

# Cases sans vrai nom, jamais affichées : « NULL », « Reserved », numéros
# génériques (« Weapon 0x1F4 », « 0x623 »), noms provisoires, et les
# marqueurs qui ouvrent chaque catégorie (« Armor Start »…).
_FACTICE = re.compile(r"^(NULL|Reserved|Not Used.*|(.+ )?0x[0-9A-F]+|\(prov\).*|.+ (start|from here))$",
                      re.IGNORECASE)


class ErreurNom(ValueError):
    pass


def _verifier(brut: bytes) -> None:
    if len(brut) != ZONE_FIN:
        raise ErreurNom(f"{CHEMIN} : {len(brut)} octets au lieu de {ZONE_FIN} "
                        "(une autre version du jeu ?)")


def lire_noms(brut: bytes) -> list[str]:
    """Le nom de chaque case, dans l'ordre des numéros d'objet."""
    _verifier(brut)
    return [texte.decoder_texte(brut[p:p + CASE].split(b"\0")[0])
            for p in range(ZONE_DEBUT, ZONE_FIN, CASE)]


def noms_a_traduire(brut: bytes) -> list[str]:
    """Les noms à traduire, sans doublon, dans l'ordre de la table (armes, armures…)."""
    return list(dict.fromkeys(n for n in lire_noms(brut)
                              if texte.est_a_traduire(n) and not _FACTICE.match(n)))


def longueur(fr: str) -> int:
    """Place prise dans une case, en octets (sans le zéro final)."""
    return len(texte.encoder_texte(texte.adapter(fr)))


def ecrire_noms(brut: bytes, traductions: dict[str, str]) -> bytes:
    """La table avec chaque nom anglais de ``traductions`` remplacé dans toutes ses cases."""
    nouveau = bytearray(brut)
    for k, nom in enumerate(lire_noms(brut)):
        fr = traductions.get(nom)
        if not fr:
            continue
        code = texte.encoder_texte(texte.adapter(fr))
        if len(code) > CASE - 1:
            raise ErreurNom(f"{TRAD} « {fr} » : {len(code)} octets, la case en tient {CASE - 1}")
        p = ZONE_DEBUT + k * CASE
        nouveau[p:p + CASE] = code.ljust(CASE, b"\0")
    return bytes(nouveau)


def lire_table(image: Path) -> bytes:
    position, _ = localiser_data_cpk(image)
    with open(image, "rb") as f:
        return Cpk(f, base=position).lire(CHEMIN)
