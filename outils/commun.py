"""Briques partagées par les outils du dépôt.

Chaque format du jeu a son propre module (crilayla, cpk, rom3ds, msg1,
flw0). Celui-ci ne contient que ce qui sert partout : les chemins du dépôt
et une console qui affiche correctement les accents.

Ce module ne dépend que de la bibliothèque standard.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

# Les consoles Windows ne sont pas en UTF-8 par défaut : sans ça, « entrées »
# s'affiche « entr�es ».
for _flux in (sys.stdout, sys.stderr):
    if hasattr(_flux, "reconfigure"):
        _flux.reconfigure(encoding="utf-8")

RACINE = Path(__file__).resolve().parent.parent
TRAD = RACINE / "trad"
BUILD = RACINE / "build"


def lire_json(p: Path) -> list[dict]:
    return json.loads(p.read_text(encoding="utf-8"))


def texte_json(entrees: list[dict]) -> str:
    """Le JSON tel qu'il est écrit dans trad/ : indenté, accents lisibles, LF final."""
    return json.dumps(entrees, ensure_ascii=False, indent=2) + "\n"


def ecrire_json(p: Path, entrees: list[dict]) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(texte_json(entrees), encoding="utf-8", newline="\n")


def fichiers_trad(racine: Path = TRAD) -> list[Path]:
    """Les JSON de traduction ; ceux qui commencent par « _ » sont techniques."""
    return sorted(p for p in racine.rglob("*.json") if not p.name.startswith("_"))


def charger_traductions(racine: Path = TRAD) -> dict[tuple[str, str], dict]:
    """{(fichier relatif, id): entrée} pour tout trad/."""
    out = {}
    for p in fichiers_trad(racine):
        rel = p.relative_to(racine).as_posix()
        for e in lire_json(p):
            out[(rel, e["id"])] = e
    return out
