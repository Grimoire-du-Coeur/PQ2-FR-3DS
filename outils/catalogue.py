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
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import flw0
import msg1
from cpk import Cpk
from rom3ds import localiser_data_cpk

PARTIES = {
    "event": "histoire",
    "dungeon": "donjons",
    "battle": "combat",
    "foe": "combat/foe",
}
EXTENSIONS = (".bmd", ".bf")


def chemin_trad(chemin_jeu: str) -> str:
    """Chemin du JSON dans trad/ pour un fichier du jeu."""
    p = PurePosixPath(chemin_jeu)
    dossiers = p.parent.parts
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
    chemin: str                     # chemin dans le CPK
    brut: bytes                     # le fichier entier (.bmd ou .bf), décompressé
    messages: msg1.ScriptMessages


def lire_scripts(image: Path) -> list[Script]:
    """Tous les .bmd et .bf qui portent des messages, triés par chemin."""
    position, _ = localiser_data_cpk(image)
    scripts = []
    with open(image, "rb") as f:
        archive = Cpk(f, base=position)
        for chemin in sorted(archive.entrees):
            if not chemin.endswith(EXTENSIONS):
                continue
            brut = archive.lire(chemin)
            if chemin.endswith(".bf"):
                donnees = flw0.extraire_messages(brut)
                if donnees is None:
                    continue
            else:
                donnees = brut
            scripts.append(Script(chemin, brut, msg1.lire_msg1(donnees)))
    return scripts
