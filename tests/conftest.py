"""Configuration commune des tests.

    python -m pytest tests

Les outils vivent à plat dans outils/ et s'importent entre eux par leur nom
(« from commun import ... »), comme quand on les lance en ligne de commande.
Les tests font de même.

Aucun test ne lit de fichier du jeu : les données dont ils ont besoin sont
fabriquées par tests/fabrique.py.
"""

import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RACINE / "outils"))
sys.path.insert(0, str(RACINE / "tests"))
