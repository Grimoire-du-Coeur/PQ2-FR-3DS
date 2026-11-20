"""Importe dans trad/ des fichiers .bmd/.bf traduits avec un autre outil.

    python outils/importer.py "image.3ds" DOSSIER --table "table caractères FR.txt"

Pensé pour le travail commencé par Tyron26 avec PersonaEditor et Kuriimu2 :
DOSSIER reproduit l'arborescence du jeu (battle/…, event/…) et contient
des scripts dont certains messages ont été traduits. Pour chaque fichier,
on compare chaque message à l'original du jeu ; ceux qui ont changé
deviennent le champ "fr" de l'entrée correspondante dans trad/.

La table de correspondance (une ligne « tapé=affiché » par caractère, par
ex. « ま=à » ou « $=è ») traduit les caractères que l'auteur utilisait pour
ses accents vers les vraies lettres. Le build, lui, utilise les accents
déjà présents dans la police du jeu (police/caracteres.json).

Une entrée qui a déjà un français n'est jamais écrasée : elle est signalée.
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from pathlib import Path

import commun
import flw0
import msg1
import texte
from catalogue import Script, chemin_trad, identifiants, lire_scripts
from rom3ds import ErreurImage


@dataclass
class Bilan:
    fichiers: int = 0
    importes: int = 0
    problemes: list[str] = field(default_factory=list)


def lire_table(chemin: Path) -> dict[str, str]:
    """« tapé=affiché » par ligne ; les lignes vides et les identités sont ignorées."""
    table = {}
    for ligne in chemin.read_text(encoding="utf-8-sig").splitlines():
        if "=" not in ligne.strip():
            continue
        tape, _, affiche = ligne.strip().partition("=")
        if len(tape) == 1 and affiche and tape != affiche:
            table[tape] = affiche
    return table


def _traduire_caracteres(lisible: str, table: dict[str, str]) -> str:
    morceaux = []
    dans_balise = False
    for ch in lisible:
        if ch == "{":
            dans_balise = True
        elif ch == "}":
            dans_balise = False
        morceaux.append(ch if dans_balise or ch == "}" else table.get(ch, ch))
    return "".join(morceaux)


def _lire_fichier(p: Path) -> msg1.ScriptMessages | None:
    donnees = p.read_bytes()
    if p.suffix == ".bf":
        donnees = flw0.extraire_messages(donnees)
        if donnees is None:
            return None
    return msg1.lire_msg1(donnees)


def importer(dossier: Path, table: dict[str, str], scripts: list[Script], trad: Path) -> Bilan:
    bilan = Bilan()
    originaux = {s.chemin: s for s in scripts}
    for p in sorted(dossier.rglob("*")):
        if p.suffix not in (".bmd", ".bf"):
            continue
        chemin = p.relative_to(dossier).as_posix()
        if chemin not in originaux:
            bilan.problemes.append(f"{chemin} : absent du jeu (ou sans messages)")
            continue
        traduit = _lire_fichier(p)
        if traduit is None:
            continue
        bilan.fichiers += 1
        origine = originaux[chemin].messages
        rel = chemin_trad(chemin)
        fichier_json = trad / rel
        entrees = commun.lire_json(fichier_json) if fichier_json.exists() else []
        par_id = {e["id"]: e for e in entrees}
        if len(traduit.messages) != len(origine.messages):
            bilan.problemes.append(f"{chemin} : {len(traduit.messages)} messages au lieu de "
                                   f"{len(origine.messages)} ; fichier ignoré")
            continue
        change = False
        for ident, m_o, m_t in zip(identifiants(origine.messages), origine.messages,
                                   traduit.messages):
            if m_t.pages == m_o.pages:
                continue
            if len(m_t.pages) != len(m_o.pages):
                bilan.problemes.append(f"{rel} {ident} : {len(m_t.pages)} pages au lieu de "
                                       f"{len(m_o.pages)}, à reprendre à la main")
                continue
            e = par_id.get(ident)
            if e is None:
                bilan.problemes.append(f"{rel} {ident} : traduit, mais pas dans trad/ "
                                       "(message japonais ou technique)")
                continue
            if e.get("fr"):
                bilan.problemes.append(f"{rel} {ident} : a déjà un français, non écrasé")
                continue
            lisibles = [_traduire_caracteres(texte.decouper_page(pg)[1], table) for pg in m_t.pages]
            e["fr"] = (texte.OPTION if m_o.choix else texte.PAGE).join(lisibles)
            if "{0x" in e["fr"]:
                bilan.problemes.append(f"{rel} {ident} : octets inconnus de la table, à corriger : "
                                       f"{e['fr'][:60]}")
            bilan.importes += 1
            change = True
        if change:
            commun.ecrire_json(fichier_json, entrees)
    return bilan


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("image", type=Path, help="image .3ds décryptée, ou data.cpk")
    parser.add_argument("dossier", type=Path, help="dossier des fichiers traduits (arborescence du jeu)")
    parser.add_argument("--table", type=Path, help="table de correspondance « tapé=affiché »")
    parser.add_argument("--trad", type=Path, default=commun.TRAD, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        scripts = lire_scripts(args.image)
    except ErreurImage as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2
    table = lire_table(args.table) if args.table else {}
    bilan = importer(args.dossier, table, scripts, args.trad)
    print(f"{bilan.fichiers} fichier(s) lus, {bilan.importes} message(s) importé(s).")
    for p in bilan.problemes:
        print(f"  à voir : {p}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
