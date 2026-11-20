"""Briques partagées par les outils du dépôt.

Chaque format du jeu a son propre module (crilayla, cpk, rom3ds, msg1,
flw0). Celui-ci ne contient que ce qui sert partout : les chemins du dépôt
et une console qui affiche correctement les accents.

Ce module ne dépend que de la bibliothèque standard.
"""

from __future__ import annotations

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
