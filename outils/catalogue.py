"""Les scripts du jeu, et où leur texte vit dans trad/.

Un fichier du jeu donne un fichier JSON, rangé par grande partie du jeu :

    event/…    → histoire/…       (scènes, cinéma, intermèdes)
    dungeon/…  → donjons/…
    battle/…   → combat/…
    foe/…      → combat/foe/…     (scripts des ennemis)
    le reste   → systeme/<dossier>/…  (aides, boutiques, camp, tutoriel…)

On garde l'arborescence du jeu sous chaque partie : un traducteur qui a vu
un fichier dans Kuriimu ou PersonaEditor le retrouve sans chercher.
L'injection fait le chemin dans l'autre sens en partant des scripts du jeu :
il n'y a pas d'index à tenir à jour.

Des scripts vivent aussi dans des archives .arc (pak.py). Une copie
identique d'un fichier isolé partage son JSON : la traduction est écrite aux
deux endroits, quelle que soit la copie que le jeu lit. Un script propre à
une archive a son propre JSON (« shop.arc/x.bmd » → « …/shop/x.json »).
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import flw0
import msg1
import pak
from cpk import Cpk
from rom3ds import localiser_data_cpk

PARTIES = {
    "event": "histoire",
    "dungeon": "donjons",
    "battle": "combat",
    "foe": "combat/foe",
}
EXTENSIONS = (".bmd", ".bf")
# Les archives qui portent des scripts, relevées sur la version européenne le
# 21/11/2026 (40 sur 323, 8,6 Mo). Ne décompresser qu'elles garde les builds
# rapides ; outils/aller_retour.py balaie toutes les archives et signale une
# archive à scripts qui manquerait ici.
ARCHIVES = (
    "battle/pack/btl_com.arc", "camp/skladd*.arc", "dungeon/pack/dng_com.arc",
    "facility/pack/cmbroot.arc", "facility/pack/shop.arc", "facility/pack/top.arc",
    "foe/pack/foe_*f.arc",
)


def est_archive_a_scripts(chemin: str) -> bool:
    return any(fnmatch.fnmatch(chemin, motif) for motif in ARCHIVES)


def chemin_trad(chemin_jeu: str) -> str:
    """Chemin du JSON dans trad/ pour un fichier du jeu (ou « archive.arc/fichier »)."""
    p = PurePosixPath(chemin_jeu)
    dossiers = tuple(d[:-4] if d.endswith(".arc") else d for d in p.parent.parts)
    if dossiers and dossiers[0] in PARTIES:
        parties = (PARTIES[dossiers[0]], *dossiers[1:])
    else:
        parties = ("systeme", *dossiers)
    return str(PurePosixPath(*parties, p.stem + ".json"))


def identifiants(messages: list[msg1.Message]) -> list[str]:
    """L'id de chaque message dans trad/ : son nom, suffixé #2, #3… s'il se répète."""
    vus: dict[str, int] = {}
    ids = []
    for m in messages:
        vus[m.nom] = vus.get(m.nom, 0) + 1
        ids.append(m.nom if vus[m.nom] == 1 else f"{m.nom}#{vus[m.nom]}")
    return ids


@dataclass
class Script:
    chemin: str                     # chemin dans le CPK, ou « archive.arc/fichier »
    brut: bytes                     # le fichier entier (.bmd ou .bf), décompressé
    messages: msg1.ScriptMessages
    trad: str = ""                  # fichier de trad/ ; deux copies identiques le partagent
    conteneur: str | None = None    # l'archive .arc dans le CPK, pour un script empaqueté
    interne: str | None = None      # son nom dans l'archive
    conteneur_brut: bytes | None = None

    def __post_init__(self):
        if not self.trad:
            self.trad = chemin_trad(self.chemin)


def messages_de(nom: str, brut: bytes) -> bytes | None:
    """Le script MSG1 porté par un .bmd ou un .bf, ou None."""
    if nom.endswith(".bf"):
        return flw0.extraire_messages(brut) if brut[8:12] == b"FLW0" else None
    return brut if brut[8:12] == b"MSG1" else None


def lire_scripts(image: Path) -> list[Script]:
    """Tous les .bmd et .bf qui portent des messages, isolés puis empaquetés."""
    position, _ = localiser_data_cpk(image)
    scripts = []
    copies: dict[tuple[str, bytes], str] = {}         # (nom, MSG1) -> JSON du fichier isolé
    with open(image, "rb") as f:
        archive = Cpk(f, base=position)
        for chemin in sorted(archive.entrees):
            if not chemin.endswith(EXTENSIONS):
                continue
            brut = archive.lire(chemin)
            donnees = messages_de(chemin, brut)
            if donnees is None:
                continue
            s = Script(chemin, brut, msg1.lire_msg1(donnees))
            copies.setdefault((PurePosixPath(chemin).name, donnees), s.trad)
            scripts.append(s)
        for chemin in sorted(c for c in archive.entrees if est_archive_a_scripts(c)):
            brut_arc = archive.lire(chemin)
            if not pak.est_pak(brut_arc):
                continue
            for nom, brut in pak.lire_pak(brut_arc):
                donnees = messages_de(nom, brut) if nom.endswith(EXTENSIONS) else None
                if donnees is None:
                    continue
                virtuel = f"{chemin}/{nom}"
                scripts.append(Script(virtuel, brut, msg1.lire_msg1(donnees),
                                      trad=copies.get((nom, donnees), ""), conteneur=chemin,
                                      interne=nom, conteneur_brut=brut_arc))
    return scripts
