"""Calcule l'avancement : SUIVI.md, badges shields.io et bloc du README.

    python outils/stats.py            # réécrit SUIVI.md, .github/badge*.json et le README
    python outils/stats.py --court    # affiche seulement le résumé

Lancé automatiquement par .github/workflows/suivi.yml à chaque fusion.
Personne ne met SUIVI.md à jour à la main : c'est la seule façon qu'il soit
juste.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import commun

CATEGORIES = [("histoire", "Histoire"), ("donjons", "Donjons"), ("combat", "Combat"),
              ("systeme", "Système"), ("noms", "Noms")]
BARRE = 24
DEBUT, FIN = "<!-- avancement:debut -->", "<!-- avancement:fin -->"
_MOT = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_BALISE = re.compile(r"\{[^{}]*\}")


@dataclass
class Compte:
    categories: dict[str, list[int]] = field(default_factory=dict)   # [traduits, total]
    dossiers: dict[str, list[int]] = field(default_factory=dict)
    mots: list[int] = field(default_factory=lambda: [0, 0])          # mots anglais, hors noms
    revoir: list[tuple[str, str]] = field(default_factory=list)


def compter(trad: Path = commun.TRAD) -> Compte:
    c = Compte(categories={cle: [0, 0] for cle, _ in CATEGORIES})
    for p in commun.fichiers_trad(trad):
        rel = p.relative_to(trad).as_posix()
        parties = rel.split("/")
        categorie = parties[0]
        dossier = "/".join(parties[:2]) if len(parties) > 2 else categorie
        for e in commun.lire_json(p):
            fait = bool(e.get("fr"))
            for compteur in (c.categories.setdefault(categorie, [0, 0]),
                             c.dossiers.setdefault(dossier, [0, 0])):
                compteur[0] += fait
                compteur[1] += 1
            if categorie != "noms":
                n = len(_MOT.findall(_BALISE.sub(" ", e.get("en", ""))))
                c.mots[1] += n
                c.mots[0] += n if fait else 0
            if e.get("a_revoir"):
                c.revoir.append((rel, e["id"]))
    return c


def pct(fait: int, total: int) -> int:
    return (100 * fait // total) if total else 0


def barre(fait: int, total: int) -> str:
    n = round(BARRE * fait / total) if total else 0
    return "█" * n + "░" * (BARRE - n)


def _nombre(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def bloc(c: Compte) -> str:
    lignes = []
    for cle, nom in CATEGORIES:
        f, t = c.categories.get(cle, [0, 0])
        lignes.append(f"{nom:<14} {barre(f, t)} {pct(f, t):>4} %   {_nombre(f):>7} / {_nombre(t)} textes")
    f = sum(v[0] for v in c.categories.values())
    t = sum(v[1] for v in c.categories.values())
    lignes.append("")
    lignes.append(f"{'Total':<14} {barre(f, t)} {pct(f, t):>4} %   {_nombre(f):>7} / {_nombre(t)} textes")
    lignes.append(f"{'':<14} {_nombre(c.mots[0])} mots traduits sur {_nombre(c.mots[1])}")
    return "```text\n" + "\n".join(lignes) + "\n```"


def maj_readme(readme: Path, contenu: str) -> None:
    if not readme.exists():
        return
    texte = readme.read_text(encoding="utf-8")
    if DEBUT not in texte or FIN not in texte:
        return
    avant, reste = texte.split(DEBUT, 1)
    _, apres = reste.split(FIN, 1)
    readme.write_text(f"{avant}{DEBUT}\n{contenu}\n{FIN}{apres}", encoding="utf-8", newline="\n")


def _couleur(p: int) -> str:
    return "CE1126" if p < 25 else "F2541B" if p < 75 else "2EC4C6"


def ecrire_badges(c: Compte, dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    f = sum(v[0] for v in c.categories.values())
    t = sum(v[1] for v in c.categories.values())
    badges = {"badge.json": ("traduction", f, t)}
    for cle, nom in CATEGORIES:
        badges[f"badge_{cle}.json"] = (nom.lower(), *c.categories.get(cle, [0, 0]))
    for nom, (etiquette, fait, total) in badges.items():
        p = pct(fait, total)
        contenu = {"schemaVersion": 1, "label": etiquette, "message": f"{p} %",
                   "color": _couleur(p), "labelColor": "0D0D0D", "style": "for-the-badge"}
        (dossier / nom).write_text(json.dumps(contenu, ensure_ascii=False) + "\n",
                                   encoding="utf-8", newline="\n")


def suivi(c: Compte) -> str:
    morceaux = [
        "# Avancement de la traduction",
        "",
        "> Fichier **généré** par `outils/stats.py`. Ne pas le modifier à la main : chaque "
        "fusion l'écrase.",
        "",
        bloc(c),
        "",
        "Une entrée compte comme traduite dès que son champ `fr` est rempli. Sans traduction, "
        "le jeu affiche l'anglais : le patch reste jouable à chaque étape.",
        "",
        "## Par dossier",
        "",
        "| Dossier | Traduits | % |",
        "|---|---:|---:|",
    ]
    for dossier, (f, t) in sorted(c.dossiers.items()):
        morceaux.append(f"| [`{dossier}`](trad/{dossier}) | {_nombre(f)} / {_nombre(t)} | {pct(f, t)} % |")
    if c.revoir:
        morceaux += ["", "## À relire", "",
                     "L'anglais de ces entrées a changé depuis leur traduction : relire, puis "
                     "supprimer le champ `a_revoir`.", ""]
        morceaux += [f"- [`{rel}`](trad/{rel}) — `{ident}`" for rel, ident in c.revoir]
    return "\n".join(morceaux) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--court", action="store_true", help="afficher le résumé seulement")
    args = parser.parse_args()
    c = compter()
    print(bloc(c).strip("`").replace("text\n", "", 1))
    if args.court:
        return 0
    (commun.RACINE / "SUIVI.md").write_text(suivi(c), encoding="utf-8", newline="\n")
    ecrire_badges(c, commun.RACINE / ".github")
    maj_readme(commun.RACINE / "README.md", bloc(c))
    return 0


if __name__ == "__main__":
    sys.exit(main())
