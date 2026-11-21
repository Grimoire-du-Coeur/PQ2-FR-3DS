"""Archives Atlus « PAK » (.arc) : plusieurs fichiers mis bout à bout.

    nombre d'entrées u32
    pour chaque entrée : nom (32 octets, ASCII complété de zéros), taille u32, données

Relevé sur les 323 .arc du jeu : entrées contiguës, sans alignement ni
octet après la dernière. 40 d'entre elles portent des scripts de messages
(boutique, fusion, camp, donjons, ennemis…), le plus souvent des copies
identiques de fichiers isolés du CPK.
"""

from __future__ import annotations

import struct

TAILLE_NOM = 32


def lire_pak(donnees: bytes) -> list[tuple[str, bytes]]:
    """[(nom, contenu)] dans l'ordre de l'archive."""
    (n,) = struct.unpack_from("<I", donnees, 0)
    pos = 4
    sortie = []
    for _ in range(n):
        nom = donnees[pos:pos + TAILLE_NOM].split(b"\0")[0].decode("ascii")
        (taille,) = struct.unpack_from("<I", donnees, pos + TAILLE_NOM)
        debut = pos + TAILLE_NOM + 4
        sortie.append((nom, donnees[debut:debut + taille]))
        pos = debut + taille
    if pos != len(donnees):
        raise ValueError(f"archive PAK incohérente : {len(donnees) - pos} octet(s) en trop")
    return sortie


def ecrire_pak(fichiers: list[tuple[str, bytes]]) -> bytes:
    sortie = bytearray(struct.pack("<I", len(fichiers)))
    for nom, contenu in fichiers:
        sortie += nom.encode("ascii").ljust(TAILLE_NOM, b"\0")
        sortie += struct.pack("<I", len(contenu)) + contenu
    return bytes(sortie)


def remplacer(donnees: bytes, nouveaux: dict[str, bytes]) -> bytes:
    """La même archive, avec certaines entrées remplacées."""
    fichiers = lire_pak(donnees)
    noms = {nom for nom, _ in fichiers}
    absents = sorted(set(nouveaux) - noms)
    if absents:
        raise KeyError(f"absent de l'archive : {', '.join(absents)}")
    return ecrire_pak([(nom, nouveaux.get(nom, contenu)) for nom, contenu in fichiers])


def est_pak(donnees: bytes) -> bool:
    """Vrai si les données se lisent comme une archive PAK complète."""
    if len(donnees) < 4:
        return False
    try:
        fichiers = lire_pak(donnees)
    except (ValueError, UnicodeDecodeError, struct.error):
        return False
    return bool(fichiers) and all(nom and nom.isprintable() for nom, _ in fichiers)
