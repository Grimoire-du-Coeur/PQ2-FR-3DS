"""Tables .ctd : les textes des menus du camp, dans init/cmptable.bin.

    init/cmptable.bin/cmpConfigItem.ctd → trad/systeme/init/cmptable/cmpConfigItem.json

En-tête de 16 octets : u32 taille des données, u32 nombre de cases, 8 zéros.
Puis les cases, puis une copie (parfois tronquée) de l'en-tête. 18 des 37
tables sont des textes en cases de 64 octets : un texte terminé par un zéro
et complété de zéros (« Confirm », « Adjust music volume »…) ; les autres
sont des nombres. Seules les cases de texte sont réécrites, à la même
place : la table ne change pas de taille, et un texte tient 63 octets
(une lettre accentuée en prend deux).

Relevé sur la version européenne le 21/11/2026.
"""

from __future__ import annotations

import re
import struct

import pak
import texte
from catalogue import chemin_trad

CONTENEUR = "init/cmptable.bin"
CASE = 64
_ENTETE = 16
# Restes japonais (« SAFTYのヘルプ ») : le jeu européen ne les affiche pas.
_JAPONAIS = re.compile("[{}-{}{}-{}{}-{}]".format(*map(chr, (0x3040, 0x30FF, 0x4E00, 0x9FFF, 0xFF00, 0xFFEF))))
# « Not used. (If this appears, it is a bug. » : case vide, jamais affichée.
_FACTICE = re.compile(r"^not used\b", re.IGNORECASE)


class ErreurCtd(ValueError):
    pass


def _cases(brut: bytes) -> list[bytes] | None:
    """Les cases d'une table de texte, ou None pour une table de nombres."""
    if len(brut) < _ENTETE:
        return None
    taille, nombre = struct.unpack_from("<II", brut, 0)
    if nombre == 0 or taille != nombre * CASE or _ENTETE + taille > len(brut):
        return None
    cases = [brut[_ENTETE + k * CASE:_ENTETE + (k + 1) * CASE] for k in range(nombre)]
    if not all(c[-1] == 0 and not any(c.split(b"\0", 1)[1]) for c in cases):
        return None
    return cases


def textes(brut: bytes) -> list[str] | None:
    cases = _cases(brut)
    return None if cases is None else [texte.decoder_texte(c.split(b"\0")[0]) for c in cases]


def a_traduire(brut: bytes) -> list[tuple[int, str]]:
    """(numéro de case, texte) des textes à traduire."""
    return [(k, t) for k, t in enumerate(textes(brut) or [])
            if texte.est_a_traduire(t) and not _JAPONAIS.search(t) and not _FACTICE.match(t)]


def ecrire(brut: bytes, traductions: dict[int, str]) -> bytes:
    """La table avec certaines cases remplacées (numéro de case → texte)."""
    if _cases(brut) is None:
        raise ErreurCtd("ce n'est pas une table de texte")
    nouveau = bytearray(brut)
    for k, fr in traductions.items():
        code = texte.encoder_texte(texte.adapter(fr))
        if len(code) > CASE - 1:
            raise ErreurCtd(f"« {fr} » : {len(code)} octets, la case en tient {CASE - 1}")
        p = _ENTETE + k * CASE
        nouveau[p:p + CASE] = code.ljust(CASE, b"\0")
    return bytes(nouveau)


def tables(conteneur: bytes) -> dict[str, bytes]:
    """Les tables de texte à traduire de cmptable.bin, une fois chacune.

    Trois tables y figurent deux fois (cmpSkillHelp…), à l'identique :
    pak.remplacer réécrit les deux copies.
    """
    vues: dict[str, bytes] = {}
    for nom, brut in pak.lire_pak(conteneur):
        if nom.endswith(".ctd") and nom not in vues and a_traduire(brut):
            vues[nom] = brut
    return vues


def entrees(conteneur: bytes) -> dict[str, list[dict]]:
    """Fichier de trad/ → entrées (id = numéro de case sur deux chiffres)."""
    return {chemin_trad(f"{CONTENEUR}/{nom}"): [{"id": f"{k:02d}", "en": t, "max": CASE - 1}
                                               for k, t in a_traduire(brut)]
            for nom, brut in tables(conteneur).items()}
