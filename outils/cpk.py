"""Lecture et patch du CPK, l'archive CRI qui contient tout le jeu.

Le RomFS de Persona Q2 ne contient qu'un fichier, ``data.cpk`` (2,8 Go,
8 923 fichiers). Ses tables (en-tête, TOC) sont au format @UTF de CRI :
gros-boutiste, une liste de colonnes typées puis des lignes de taille fixe.

Pour remplacer des fichiers, on ne reconstruit pas l'archive : on **ajoute
les nouveaux fichiers à la fin**, non compressés, et on réécrit sur place
leurs lignes dans la TOC (taille, taille extraite, position). Les colonnes
étant de taille fixe, la TOC garde exactement sa taille. Un build ne prend
que quelques secondes, et un patch xdelta du résultat reste petit.

Pour qu'un deuxième build reparte proprement de l'original, le patch range
à la toute fin du fichier une copie de l'en-tête et de la TOC d'origine,
suivie d'une signature. Le jeu ignore ces octets, qui ne sont référencés
par aucune ligne de la TOC.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO

import crilayla

ALIGNEMENT = 2048
SIGNATURE_ORIGINE = b"PQ2FR-ORIGINE\0\0\0"

_TAILLES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 9: 8, 0xA: 4, 0xB: 8}
_FORMATS = {0: ">B", 1: ">b", 2: ">H", 3: ">h", 4: ">I", 5: ">i", 6: ">Q", 7: ">q",
            8: ">f", 9: ">d", 0xA: ">I", 0xB: ">II"}
_ZERO, _CONSTANTE, _PAR_LIGNE = 0x10, 0x30, 0x50


@dataclass
class TableUtf:
    nom: str
    lignes: list[dict[str, object]]
    positions: list[dict[str, tuple[int, int]]]   # colonne -> (position dans la table, type)


def lire_utf(table: bytes) -> TableUtf:
    """Lit une table @UTF ; ``table`` commence à la signature."""
    if table[:4] != b"@UTF":
        raise ValueError("table @UTF attendue (le CPK est peut-être chiffré ou abîmé)")
    _, pos_lignes, pos_chaines, pos_donnees, pos_nom, n_col, taille_ligne, n_lignes = \
        struct.unpack_from(">HHIIIHHI", table, 8)
    chaines = table[8 + pos_chaines:8 + pos_donnees]

    def chaine(o: int) -> str:
        return chaines[o:chaines.index(b"\0", o)].decode("utf-8", "replace")

    def valeur(t: int, pos: int):
        v = struct.unpack_from(_FORMATS[t], table, pos)
        if t == 0xA:
            return chaine(v[0])
        if t == 0xB:
            return table[8 + pos_donnees + v[0]:8 + pos_donnees + v[0] + v[1]]
        return v[0]

    colonnes = []
    pos = 0x20
    for _ in range(n_col):
        drapeau, nom = struct.unpack_from(">BI", table, pos)
        pos += 5
        stockage, t = drapeau & 0xF0, drapeau & 0x0F
        pos_constante = None
        if stockage == _CONSTANTE:
            pos_constante = pos
            pos += _TAILLES[t]
        colonnes.append((chaine(nom), stockage, t, pos_constante))

    lignes, positions = [], []
    for i in range(n_lignes):
        p = 8 + pos_lignes + i * taille_ligne
        ligne, place = {}, {}
        for nom, stockage, t, pos_constante in colonnes:
            if stockage == _PAR_LIGNE:
                ligne[nom], place[nom] = valeur(t, p), (p, t)
                p += _TAILLES[t]
            elif stockage == _CONSTANTE:
                ligne[nom], place[nom] = valeur(t, pos_constante), (pos_constante, t)
            else:
                ligne[nom] = None
        lignes.append(ligne)
        positions.append(place)
    return TableUtf(chaine(pos_nom), lignes, positions)


@dataclass
class EntreeCpk:
    id: int
    chemin: str
    decalage: int          # depuis le début du CPK
    taille: int            # taille stockée (compressée ou non)
    taille_extraite: int
    ligne: int             # indice de la ligne dans la TOC


class Cpk:
    """Un CPK ouvert en lecture, éventuellement à l'intérieur d'un autre fichier."""

    def __init__(self, fichier: BinaryIO, base: int = 0):
        self.fichier = fichier
        self.base = base
        self.entete_brut = self._paquet(0, b"CPK ")
        self.entete = lire_utf(self.entete_brut[0x10:])
        h = self.entete.lignes[0]
        self.toc_offset = int(h["TocOffset"])
        self.content_offset = int(h["ContentOffset"])
        # Les positions de la TOC sont relatives à TocOffset, sauf si la TOC
        # est rangée après le contenu.
        self.origine_decalages = (self.content_offset if self.toc_offset > self.content_offset
                                  else self.toc_offset)
        self.toc_brut = self._paquet(self.toc_offset, b"TOC ")
        self.toc = lire_utf(self.toc_brut[0x10:])
        self.entrees: dict[str, EntreeCpk] = {}
        for i, r in enumerate(self.toc.lignes):
            dossier = r.get("DirName") or ""
            chemin = f"{dossier}/{r['FileName']}" if dossier else str(r["FileName"])
            self.entrees[chemin] = EntreeCpk(
                id=int(r["ID"]), chemin=chemin,
                decalage=int(r["FileOffset"]) + self.origine_decalages,
                taille=int(r["FileSize"]), taille_extraite=int(r["ExtractSize"]), ligne=i)

    def _paquet(self, position: int, signature: bytes) -> bytes:
        self.fichier.seek(self.base + position)
        tete = self.fichier.read(0x10)
        if tete[:4] != signature:
            raise ValueError(f"signature {signature!r} attendue à 0x{position:x}, trouvé {tete[:4]!r}")
        (taille,) = struct.unpack_from("<Q", tete, 8)
        return tete + self.fichier.read(taille)

    def lire(self, chemin: str) -> bytes:
        """Contenu du fichier, décompressé si besoin."""
        e = self.entrees[chemin]
        self.fichier.seek(self.base + e.decalage)
        donnees = self.fichier.read(e.taille)
        if donnees[:8] == crilayla.SIGNATURE:
            donnees = crilayla.decompresser(donnees)
        if len(donnees) != e.taille_extraite:
            raise ValueError(f"{chemin} : {len(donnees)} octets lus, {e.taille_extraite} attendus")
        return donnees


def _ecrire(table: bytearray, place: tuple[int, int], valeur: int) -> None:
    position, t = place
    struct.pack_into(_FORMATS[t], table, position, valeur)


def _aligner(n: int) -> int:
    return (n + ALIGNEMENT - 1) // ALIGNEMENT * ALIGNEMENT


def _restaurer(f: BinaryIO, taille_origine: int) -> None:
    """Remet le CPK dans son état d'origine s'il a déjà été patché par cet outil."""
    f.seek(0, 2)
    taille = f.tell()
    if taille == taille_origine:
        return
    if taille < taille_origine:
        raise ValueError(f"CPK plus petit que l'original ({taille} < {taille_origine} octets)")
    queue = 24 + len(SIGNATURE_ORIGINE)
    f.seek(taille - queue)
    bloc = f.read(queue)
    if not bloc.endswith(SIGNATURE_ORIGINE):
        raise ValueError("ce CPK a été modifié par un autre outil : repartir d'une copie d'origine")
    l_entete, l_toc, origine = struct.unpack_from("<QQQ", bloc)
    if origine != taille_origine:
        raise ValueError(f"ce CPK a été patché depuis une taille de {origine} octets, "
                         f"pas {taille_origine}")
    f.seek(taille - queue - l_toc - l_entete)
    entete, toc = f.read(l_entete), f.read(l_toc)
    f.seek(0)
    f.write(entete)
    f.seek(int(lire_utf(entete[0x10:]).lignes[0]["TocOffset"]))
    f.write(toc)
    f.truncate(taille_origine)


def patcher_cpk(chemin: Path, taille_origine: int, remplacements: dict[str, bytes]) -> None:
    """Remplace des fichiers du CPK ``chemin`` en les ajoutant à la fin.

    ``taille_origine`` est la taille du CPK d'origine : tout ce qui la dépasse
    vient d'un patch précédent et est d'abord retiré. Sans remplacement, le
    fichier redevient identique à l'original.
    """
    with open(chemin, "r+b") as f:
        _restaurer(f, taille_origine)
        if not remplacements:
            return
        archive = Cpk(f)
        inconnus = sorted(c for c in remplacements if c not in archive.entrees)
        if inconnus:
            raise KeyError(f"absent du CPK : {', '.join(inconnus)}")

        entete = bytearray(archive.entete_brut)
        toc = bytearray(archive.toc_brut)
        pos = _aligner(taille_origine)
        f.seek(taille_origine)
        f.write(bytes(pos - taille_origine))
        for nom in sorted(remplacements):
            donnees = remplacements[nom]
            place = archive.toc.positions[archive.entrees[nom].ligne]
            f.seek(pos)
            f.write(donnees)
            # Les positions des tables sont relatives à la table @UTF, qui
            # commence 0x10 octets après le début du paquet.
            for colonne, valeur in (("FileSize", len(donnees)), ("ExtractSize", len(donnees)),
                                    ("FileOffset", pos - archive.origine_decalages)):
                p, t = place[colonne]
                _ecrire(toc, (p + 0x10, t), valeur)
            fin = pos + len(donnees)
            pos = _aligner(fin)
            f.write(bytes(pos - fin))
        place_contenu = archive.entete.positions[0].get("ContentSize")
        if place_contenu:
            _ecrire(entete, (place_contenu[0] + 0x10, place_contenu[1]),
                    pos - archive.content_offset)

        f.seek(pos)
        f.write(archive.entete_brut + archive.toc_brut
                + struct.pack("<QQQ", len(archive.entete_brut), len(archive.toc_brut),
                              taille_origine)
                + SIGNATURE_ORIGINE)
        f.seek(0)
        f.write(entete)
        f.seek(archive.toc_offset)
        f.write(toc)
