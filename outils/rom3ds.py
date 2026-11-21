"""Retrouve data.cpk dans l'image 3DS du joueur.

Accepte :
- une image ``.3ds`` / ``.cci`` **décryptée** (conteneur NCSD) ;
- une partition ``.cxi`` décryptée (NCCH seul) ;
- le fichier ``data.cpk`` déjà extrait.

Chemin suivi dans une image : NCSD → partition 0 (NCCH, le jeu) → RomFS
(en-tête IVFC, puis le « niveau 3 » qui contient l'arborescence) → le seul
fichier de la racine, ``data.cpk``. Rien n'est copié : on rend sa position
et sa taille dans l'image, pour le lire sur place.
"""

from __future__ import annotations

import struct
from pathlib import Path
from typing import BinaryIO

import blz

MU = 0x200                          # unité de taille des en-têtes NCSD/NCCH
TITLE_ID_EU = 0x00040000001D7600    # Persona Q2, version européenne (CTR-P-AQ2P)
SANS_LIEN = 0xFFFFFFFF


class ErreurImage(Exception):
    """Image inutilisable ; le message s'affiche tel quel au joueur."""


def _ncch(f: BinaryIO, debut: int) -> tuple[int, int]:
    """Position et taille du RomFS d'une partition NCCH, après contrôles."""
    f.seek(debut)
    tete = f.read(0x200)
    if tete[0x100:0x104] != b"NCCH":
        raise ErreurImage("partition du jeu introuvable : l'image est peut-être abîmée")
    if not tete[0x18F] & 0x04:
        raise ErreurImage(
            "l'image est chiffrée. Décryptez-la d'abord depuis votre console avec GodMode9 "
            "(ou utilisez une image déjà décryptée pour Azahar).")
    (title_id,) = struct.unpack_from("<Q", tete, 0x118)
    if title_id != TITLE_ID_EU:
        raise ErreurImage(
            f"cette image a le title ID {title_id:016X} ; le patch vise la version européenne "
            f"de Persona Q2 ({TITLE_ID_EU:016X}).")
    pos, taille = struct.unpack_from("<II", tete, 0x1B0)
    if not taille:
        raise ErreurImage("la partition du jeu n'a pas de RomFS")
    return debut + pos * MU, taille * MU


def _data_cpk(f: BinaryIO, romfs: int) -> tuple[int, int]:
    """Cherche data.cpk à la racine du RomFS qui commence à ``romfs``."""
    f.seek(romfs)
    ivfc = f.read(0x60)
    if ivfc[:4] != b"IVFC":
        raise ErreurImage("RomFS illisible (en-tête IVFC absent) : l'image est peut-être chiffrée")
    (taille_maitre,) = struct.unpack_from("<I", ivfc, 0x08)
    bloc = 1 << struct.unpack_from("<I", ivfc, 0x0C + 0x18 * 2 + 0x10)[0]
    niveau3 = romfs + (0x60 + taille_maitre + bloc - 1) // bloc * bloc
    f.seek(niveau3)
    (_, _, _, dossiers_pos, dossiers_taille, _, _, fichiers_pos, fichiers_taille, donnees_pos) = \
        struct.unpack("<10I", f.read(0x28))
    f.seek(niveau3 + dossiers_pos)
    dossiers = f.read(dossiers_taille)
    f.seek(niveau3 + fichiers_pos)
    fichiers = f.read(fichiers_taille)

    (premier,) = struct.unpack_from("<I", dossiers, 0x0C)    # premier fichier de la racine
    o = premier
    while o != SANS_LIEN:
        _, suivant, pos, taille, _, longueur = struct.unpack_from("<IIQQII", fichiers, o)
        nom = fichiers[o + 0x20:o + 0x20 + longueur].decode("utf-16-le")
        if nom == "data.cpk":
            return niveau3 + donnees_pos + pos, taille
        o = suivant
    raise ErreurImage("data.cpk introuvable dans le RomFS : est-ce bien Persona Q2 ?")


class PasDeCode(ErreurImage):
    """Le fichier donné (data.cpk seul) ne contient pas le code du jeu."""


def lire_code(chemin: Path) -> bytes:
    """Le code du jeu (ExeFS « .code »), décompressé : c'est lui que patche code.ips."""
    with open(chemin, "rb") as f:
        tete = f.read(0x200)
        if tete[0x100:0x104] == b"NCSD":
            debut = struct.unpack_from("<I", tete, 0x120)[0] * MU
        elif tete[0x100:0x104] == b"NCCH":
            debut = 0
        else:
            raise PasDeCode("le code du jeu n'est que dans l'image complète (.3ds/.cci ou .cxi)")
        _ncch(f, debut)                                 # mêmes contrôles que pour le RomFS
        f.seek(debut)
        ncch = f.read(0x200)
        exefs, taille = (v * MU for v in struct.unpack_from("<II", ncch, 0x1A0))
        if not taille:
            raise PasDeCode("la partition du jeu n'a pas d'ExeFS")
        f.seek(debut + 0x200)
        compresse = f.read(0x400)[0xD] & 1               # exheader, drapeaux du code
        f.seek(debut + exefs)
        tete_exefs = f.read(0x200)
        for k in range(0, 0xA0, 16):
            if tete_exefs[k:k + 8].rstrip(b"\0") == b".code":
                pos, taille_code = struct.unpack_from("<II", tete_exefs, k + 8)
                f.seek(debut + exefs + 0x200 + pos)
                code = f.read(taille_code)
                return blz.decompresser(code) if compresse else code
    raise ErreurImage("code du jeu introuvable dans l'ExeFS")


def localiser_data_cpk(chemin: Path) -> tuple[int, int]:
    """(position, taille) de data.cpk dans ``chemin``."""
    with open(chemin, "rb") as f:
        tete = f.read(0x200)
        f.seek(0, 2)
        taille_fichier = f.tell()
        if tete[:4] == b"CPK ":
            return 0, taille_fichier
        if tete[0x100:0x104] == b"NCSD":
            (partition,) = struct.unpack_from("<I", tete, 0x120)
            return _data_cpk(f, _ncch(f, partition * MU)[0])
        if tete[0x100:0x104] == b"NCCH":
            return _data_cpk(f, _ncch(f, 0)[0])
    raise ErreurImage(
        f"format non reconnu pour {Path(chemin).name} : il faut une image .3ds/.cci décryptée, "
        "une partition .cxi ou le fichier data.cpk.")
