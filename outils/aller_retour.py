"""Contrôle de sécurité : relire puis réécrire tous les scripts du jeu.

    python outils/aller_retour.py "chemin/vers/Persona Q2 (Europe).3ds"

Pour chaque .bmd et chaque .bf du CPK, et pour ceux que portent les
archives .arc, lit le script de messages, le réécrit sans rien traduire et
compare au fichier d'origine :

- identique : les octets sont les mêmes ;
- équivalent : le fichier d'origine n'était pas « canonique » (deux lignes
  de table vers un même message, par exemple), mais la réécriture redonne
  exactement les mêmes messages et reste stable si on la relit ;
- échec : tout le reste. Il faut alors corriger msg1.py ou flw0.py avant
  d'injecter la moindre traduction.

La table des noms d'objets (noms.py) est relue puis réécrite avec ses
propres noms : elle doit redonner les mêmes octets.

Chaque page est aussi passée par le texte lisible de trad/ (texte.py) :
découpée, décodée, réencodée, recollée. Elle doit redonner les mêmes octets.

À relancer après toute modification de ces deux modules. Ne lit que l'image
du joueur ; rien n'est écrit.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import commun  # noqa: F401  (console en UTF-8)
import flw0
import msg1
import noms
import pak
import texte
from catalogue import est_archive_a_scripts
from cpk import Cpk
from rom3ds import ErreurImage, localiser_data_cpk


@dataclass
class Bilan:
    fichiers: int = 0
    identiques: int = 0
    sans_messages: int = 0
    messages: int = 0
    pages: int = 0
    noms: int = 0                                   # noms d'objets à traduire
    equivalents: list[str] = field(default_factory=list)
    echecs: list[tuple[str, str]] = field(default_factory=list)


def _controler_pages(chemin: str, script: msg1.ScriptMessages, bilan: Bilan) -> None:
    for m in script.messages:
        for k, page in enumerate(m.pages):
            bilan.pages += 1
            prefixe, lisible, suffixe = texte.decouper_page(page)
            try:
                recollee = prefixe + texte.encoder_texte(lisible) + suffixe
            except texte.ErreurTexte as e:
                bilan.echecs.append((chemin, f"{m.nom} page {k + 1} : {e}"))
                continue
            if recollee != page:
                bilan.echecs.append((chemin, f"{m.nom} page {k + 1} : le texte lisible ne "
                                             "redonne pas la page"))


def _contenu(script: msg1.ScriptMessages) -> list:
    return [[(m.nom, m.choix, m.locuteur, m.pages) for m in script.messages], script.locuteurs]


def _premier_ecart(a: bytes, b: bytes) -> str:
    i = next((k for k in range(min(len(a), len(b))) if a[k] != b[k]), min(len(a), len(b)))
    return f"{len(b)} octets au lieu de {len(a)}, premier écart à 0x{i:x}"


def _controler(chemin: str, donnees: bytes, bilan: Bilan) -> None:
    if chemin.endswith(".bf"):
        script_brut = flw0.extraire_messages(donnees)
        if script_brut is None:
            bilan.sans_messages += 1
            return

        def reconstruire(s: msg1.ScriptMessages) -> bytes:
            return flw0.remplacer_messages(donnees, msg1.ecrire_msg1(s))

        def relire(fichier: bytes) -> bytes:
            return flw0.extraire_messages(fichier) or b""
    else:
        script_brut = donnees

        def reconstruire(s: msg1.ScriptMessages) -> bytes:
            return msg1.ecrire_msg1(s)

        def relire(fichier: bytes) -> bytes:
            return fichier

    script = msg1.lire_msg1(script_brut)
    bilan.messages += len(script.messages)
    _controler_pages(chemin, script, bilan)
    sortie = reconstruire(script)
    if sortie == donnees:
        bilan.identiques += 1
        return
    relu = msg1.lire_msg1(relire(sortie))
    if _contenu(relu) == _contenu(script) and reconstruire(relu) == sortie:
        bilan.equivalents.append(chemin)
    else:
        bilan.echecs.append((chemin, _premier_ecart(donnees, sortie)))


def verifier(image: Path) -> Bilan:
    position, _ = localiser_data_cpk(image)
    bilan = Bilan()
    with open(image, "rb") as f:
        archive = Cpk(f, base=position)
        for chemin in sorted(archive.entrees):
            if not chemin.endswith((".bmd", ".bf")):
                continue
            bilan.fichiers += 1
            try:
                _controler(chemin, archive.lire(chemin), bilan)
            except Exception as e:      # noqa: BLE001 — un fichier cassé ne doit pas arrêter le contrôle
                bilan.echecs.append((chemin, f"illisible : {type(e).__name__}: {e}"))
        # Les archives .arc : toutes, pour repérer une archive à scripts que
        # catalogue.ARCHIVES ne connaîtrait pas (elle resterait en anglais).
        for chemin in sorted(c for c in archive.entrees if c.endswith(".arc")):
            brut_arc = archive.lire(chemin)
            if not pak.est_pak(brut_arc):
                continue
            fichiers = pak.lire_pak(brut_arc)
            if pak.ecrire_pak(fichiers) != brut_arc:
                bilan.echecs.append((chemin, "l'archive ne se réécrit pas à l'identique"))
            scripts = [(nom, brut) for nom, brut in fichiers if nom.endswith((".bmd", ".bf"))]
            if scripts and not est_archive_a_scripts(chemin):
                bilan.echecs.append((chemin, "archive à scripts absente de catalogue.ARCHIVES"))
            for nom, brut in scripts:
                bilan.fichiers += 1
                try:
                    _controler(f"{chemin}/{nom}", brut, bilan)
                except Exception as e:  # noqa: BLE001
                    bilan.echecs.append((f"{chemin}/{nom}", f"illisible : {type(e).__name__}: {e}"))
        if noms.CHEMIN in archive.entrees:
            _controler_noms(archive.lire(noms.CHEMIN), bilan)
    return bilan


def _controler_noms(brut: bytes, bilan: Bilan) -> None:
    try:
        a_traduire = noms.noms_a_traduire(brut)
        if noms.ecrire_noms(brut, {n: n for n in a_traduire}) != brut:
            bilan.echecs.append((noms.CHEMIN, "la table ne se réécrit pas à l'identique"))
        bilan.noms = len(a_traduire)
    except (noms.ErreurNom, texte.ErreurTexte) as e:
        bilan.echecs.append((noms.CHEMIN, str(e)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("image", type=Path, help="image .3ds décryptée, ou data.cpk")
    args = parser.parse_args()
    try:
        bilan = verifier(args.image)
    except ErreurImage as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2
    print(f"{bilan.fichiers} scripts (.bmd + .bf), {bilan.messages} messages, {bilan.pages} pages")
    print(f"noms d'objets : {bilan.noms} (table relue et réécrite)")
    print(f"  identiques   : {bilan.identiques}")
    print(f"  sans messages: {bilan.sans_messages}")
    print(f"  équivalents  : {len(bilan.equivalents)}")
    for chemin in bilan.equivalents:
        print(f"    {chemin}")
    print(f"  échecs       : {len(bilan.echecs)}")
    for chemin, raison in bilan.echecs[:5]:
        print(f"    {chemin} : {raison}")
    return 1 if bilan.echecs else 0


if __name__ == "__main__":
    sys.exit(main())
