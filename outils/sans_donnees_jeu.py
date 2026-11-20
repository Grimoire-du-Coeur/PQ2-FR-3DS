"""Refuse tout fichier qui ressemble à une donnée du jeu.

    python outils/sans_donnees_jeu.py

Lancé par la CI sur chaque Pull Request. Le dépôt ne doit contenir que du
texte, des outils et quelques images à nous : ni image du jeu, ni archive,
ni police, ni texture, ni script ou message d'origine, même modifiés.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import commun  # noqa: F401  (console en UTF-8)

INTERDITS = {
    # images et conteneurs 3DS
    ".3ds", ".cia", ".cci", ".cxi", ".app",
    # archives et formats du jeu
    ".cpk", ".bcfnt", ".bffnt", ".ctpk", ".bcmdl", ".bmd", ".bf", ".mbm", ".tbl",
    ".arc", ".pac", ".spr3", ".acb", ".awb", ".usm",
    # patchs, sauvegardes, exécutables
    ".xdelta", ".sav", ".exe",
}
# Un nom qui trahit un fichier du jeu, sauf dans la documentation et les
# données de traduction, qui ont le droit de citer la référence du jeu.
NOMS = ("CTR-P-AQ2P", "00040000001D7600")
EXTENSIONS_LIBRES_POUR_LES_NOMS = {".md", ".json"}
TAILLE_MAX = 2 * 1024 * 1024          # 2 Mo : largement assez pour une capture
EXCEPTIONS_TAILLE: set[str] = set()


def verifier(racine: Path) -> int:
    """Affiche une annotation par fichier fautif ; renvoie 1 s'il y en a."""
    suivis = subprocess.run(["git", "ls-files"], cwd=racine, capture_output=True, text=True,
                            check=True).stdout.splitlines()
    fautes = []
    for f in suivis:
        p = racine / f
        if not p.is_file():
            continue
        ext = p.suffix.lower()
        if ext in INTERDITS:
            fautes.append((f, f"type de fichier interdit ({p.suffix})"))
        elif (any(n.lower() in p.name.lower() for n in NOMS)
              and ext not in EXTENSIONS_LIBRES_POUR_LES_NOMS):
            fautes.append((f, "nom de fichier du jeu"))
        elif p.stat().st_size > TAILLE_MAX and f not in EXCEPTIONS_TAILLE:
            fautes.append((f, f"{p.stat().st_size} octets (plus de {TAILLE_MAX // 1024 // 1024} Mo)"))
    for f, raison in fautes:
        print(f"::error file={f}::{f} : {raison}")
    print(f"{len(suivis)} fichiers suivis, {len(fautes)} problème(s).")
    return 1 if fautes else 0


def main() -> int:
    return verifier(Path(__file__).resolve().parent.parent)


if __name__ == "__main__":
    sys.exit(main())
