"""Largeur des caractères à l'écran, pour repérer les lignes trop longues.

    python outils/mesurer.py "chemin/vers/Persona Q2 (Europe).3ds"   # -> police/largeurs.json

Le jeu dessine ses lettres latines avec les cases « pleine largeur » de
font/seurapro_12_12.bcfnt (Ａ, ｂ, ｃ…), qui portent des largeurs
proportionnelles (i = 3 px, m = 10 px). On relève ces largeurs une fois,
depuis l'image du joueur, et on les range dans police/largeurs.json : des
nombres seulement, aucun dessin de la police.

Le même fichier garde, pour chaque partie du jeu (histoire, combat…), la
largeur sous laquelle tiennent 99 % des lignes anglaises : une ligne
française plus large que cette limite, et plus large que la plus longue
ligne anglaise de la même entrée, risque de sortir de sa bulle. (Le
maximum absolu ne convient pas : quelques aides de l'écran du bas et un
poème ont des lignes bien plus longues que les bulles de dialogue.)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

import commun
import texte
from bcfnt import lire_metriques
from cpk import Cpk
from rom3ds import ErreurImage, localiser_data_cpk

POLICE = "font/seurapro_12_12.bcfnt"
FICHIER = commun.RACINE / "police" / "largeurs.json"
LARGEUR_INCONNUE = 12
_LIGATURES = {"œ": "oe", "Œ": "OE", "æ": "ae", "Æ": "AE"}
_BALISE = re.compile(r"\{[^{}]*\}")


def largeurs_caracteres(metriques: dict[int, tuple[int, int, int]]) -> dict[str, int]:
    """Avance en pixels de chaque caractère qu'un traducteur peut écrire."""
    def avance(code: int) -> int | None:
        return metriques[code][2] if code in metriques else None

    largeurs: dict[str, int] = {}
    for o in range(0x20, 0x7F):
        ch = chr(o)
        valeur = None
        if ch != " ":
            try:
                plein = chr(o + 0xFEE0).encode("cp932")
                valeur = avance(int.from_bytes(plein, "big"))
            except UnicodeEncodeError:
                pass
        if valeur is None:
            valeur = avance(o)
        if valeur is not None:
            largeurs[ch] = valeur
    for ch in texte.ACCENTS:
        base = _LIGATURES.get(ch) or unicodedata.normalize("NFD", ch)[0]
        if all(b in largeurs for b in base):
            largeurs[ch] = sum(largeurs[b] for b in base)
    codes_accents = {int.from_bytes(c, "big") for c in texte.ACCENTS.values()}
    for code, (_, _, av) in metriques.items():
        if code >= 0x8140 and code not in codes_accents:
            try:
                ch = code.to_bytes(2, "big").decode("cp932")
            except UnicodeDecodeError:
                continue
            largeurs.setdefault(ch, av)
    return largeurs


def largeur_ligne(ligne: str, largeurs: dict[str, int]) -> int:
    """Largeur d'une ligne de texte lisible ; les balises comptent pour zéro."""
    return sum(largeurs.get(ch, LARGEUR_INCONNUE) for ch in _BALISE.sub("", ligne))


def lignes(lisible: str) -> list[list[str]]:
    """Pages (ou options), puis lignes de chaque page."""
    pages = re.split(r"\{PAGE\}|\{OPTION\}", lisible)
    return [p.split(texte.SAUT) for p in pages]


def limites_anglaises(trad: Path, largeurs: dict[str, int]) -> dict[str, int]:
    """Largeur sous laquelle tiennent 99 % des lignes anglaises, par partie du jeu."""
    mesures: dict[str, list[int]] = {}
    for p in commun.fichiers_trad(trad):
        partie = p.relative_to(trad).parts[0]
        for e in commun.lire_json(p):
            for page in lignes(e["en"]):
                mesures.setdefault(partie, []).extend(largeur_ligne(l, largeurs) for l in page)
    return {partie: sorted(v)[int(len(v) * 0.99)] for partie, v in sorted(mesures.items())}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("image", type=Path, help="image .3ds décryptée, ou data.cpk")
    args = parser.parse_args()
    try:
        position, _ = localiser_data_cpk(args.image)
    except ErreurImage as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2
    with open(args.image, "rb") as f:
        metriques = lire_metriques(Cpk(f, base=position).lire(POLICE))
    largeurs = largeurs_caracteres(metriques)
    limites = limites_anglaises(commun.TRAD, largeurs)
    # On ne garde que ce qu'un traducteur écrit : ASCII, accents, et les
    # symboles que le texte anglais utilise déjà (…, “ ”, ―…).
    utiles = {chr(o) for o in range(0x20, 0x7F)} | set(texte.ACCENTS)
    for p in commun.fichiers_trad():
        for e in commun.lire_json(p):
            utiles.update(_BALISE.sub("", e["en"]))
    largeurs = {ch: v for ch, v in largeurs.items() if ch in utiles}
    contenu = {
        "_lisez_moi": "Avance en pixels de chaque caractère dans la police des dialogues "
                      "(font/seurapro_12_12.bcfnt), et largeur sous laquelle tiennent 99 % des "
                      "lignes anglaises, par partie du jeu. Généré par outils/mesurer.py.",
        "limites": limites,
        "largeurs": dict(sorted(largeurs.items())),
    }
    FICHIER.write_text(json.dumps(contenu, ensure_ascii=False, indent=1) + "\n",
                       encoding="utf-8", newline="\n")
    print(f"{len(largeurs)} caractères mesurés. Limites : {limites}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
