"""Fabrique de données de test, sans aucun octet du jeu.

Les tests ont besoin de CPK, d'images 3DS, de scripts MSG1 et FLW0. Ce module
les écrit de toutes pièces, en suivant les dispositions relevées sur le jeu :
assez fidèles pour exercer les outils, assez petites pour tenir dans un test.
"""

from __future__ import annotations

import struct

import crilayla

# ---------------------------------------------------------------- tables @UTF

_TAILLES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 9: 8, 0xA: 4, 0xB: 8}
_FORMATS = {0: ">B", 1: ">b", 2: ">H", 3: ">h", 4: ">I", 5: ">i", 6: ">Q", 7: ">q",
            8: ">f", 9: ">d"}


def ecrire_utf(nom: str, colonnes: list[tuple[str, int, object]], lignes: list[dict]) -> bytes:
    """Table @UTF : ``colonnes`` = (nom, drapeau stockage|type, constante ou None)."""
    chaines = bytearray(b"<NULL>\0")
    index: dict[str, int] = {}

    def chaine(s: str) -> int:
        if s not in index:
            index[s] = len(chaines)
            chaines.extend(s.encode("utf-8") + b"\0")
        return index[s]

    def valeur(t: int, v) -> bytes:
        if t == 0xA:
            return struct.pack(">I", chaine(v))
        return struct.pack(_FORMATS[t], v)

    nom_table = chaine(nom)
    schema = bytearray()
    taille_ligne = 0
    for nom_col, drapeau, constante in colonnes:
        schema += struct.pack(">BI", drapeau, chaine(nom_col))
        if drapeau & 0xF0 == 0x30:
            schema += valeur(drapeau & 0x0F, constante)
        elif drapeau & 0xF0 == 0x50:
            taille_ligne += _TAILLES[drapeau & 0x0F]
    corps_lignes = bytearray()
    for ligne in lignes:
        for nom_col, drapeau, _ in colonnes:
            if drapeau & 0xF0 == 0x50:
                corps_lignes += valeur(drapeau & 0x0F, ligne[nom_col])

    pos_lignes = 0x18 + len(schema)
    pos_chaines = pos_lignes + len(corps_lignes)
    pos_donnees = pos_chaines + len(chaines)
    entete = struct.pack(">HHIIIHHI", 1, pos_lignes, pos_chaines, pos_donnees, nom_table,
                         len(colonnes), taille_ligne, len(lignes))
    corps = entete + schema + corps_lignes + chaines
    return b"@UTF" + struct.pack(">I", len(corps)) + corps


def _paquet(signature: bytes, table: bytes) -> bytes:
    return signature + b"\xff\0\0\0" + struct.pack("<Q", len(table)) + table


def _aligner(n: int, a: int = 2048) -> int:
    return (n + a - 1) // a * a


# ---------------------------------------------------------------- CPK

def fabriquer_cpk(fichiers: dict[str, bytes], compresses: set[str] = frozenset()) -> bytes:
    """CPK minimal : en-tête, TOC à 2 048, fichiers alignés sur 2 048."""
    chemins = sorted(fichiers)
    stockes = {c: crilayla.compresser_litteral(fichiers[c]) if c in compresses else fichiers[c]
               for c in chemins}
    toc_pos = 2048

    def toc(decalages: dict[str, int]) -> bytes:
        lignes = []
        for i, c in enumerate(chemins):
            dossier, _, nom = c.rpartition("/")
            lignes.append({"DirName": dossier, "FileName": nom, "FileSize": len(stockes[c]),
                           "ExtractSize": len(fichiers[c]), "FileOffset": decalages.get(c, 0),
                           "ID": i})
        return _paquet(b"TOC ", ecrire_utf("CpkTocInfo", [
            ("DirName", 0x5A, None), ("FileName", 0x5A, None), ("FileSize", 0x54, None),
            ("ExtractSize", 0x54, None), ("FileOffset", 0x56, None), ("ID", 0x54, None),
            ("UserString", 0x3A, "<NULL>")], lignes))

    taille_toc = len(toc({}))
    contenu_pos = _aligner(toc_pos + taille_toc)
    decalages, pos = {}, contenu_pos
    for c in chemins:
        decalages[c] = pos - toc_pos          # relatif à TocOffset, comme dans le jeu
        pos = _aligner(pos + len(stockes[c]))
    paquet_toc = toc(decalages)

    entete = _paquet(b"CPK ", ecrire_utf("CpkHeader", [
        ("ContentOffset", 0x56, None), ("ContentSize", 0x56, None), ("TocOffset", 0x56, None),
        ("TocSize", 0x56, None), ("Files", 0x54, None), ("Align", 0x52, None)],
        [{"ContentOffset": contenu_pos, "ContentSize": pos - contenu_pos, "TocOffset": toc_pos,
          "TocSize": len(paquet_toc), "Files": len(chemins), "Align": 2048}]))
    sortie = bytearray(pos)
    sortie[:len(entete)] = entete
    sortie[toc_pos:toc_pos + len(paquet_toc)] = paquet_toc
    for c in chemins:
        debut = toc_pos + decalages[c]
        sortie[debut:debut + len(stockes[c])] = stockes[c]
    return bytes(sortie)
