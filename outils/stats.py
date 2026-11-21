"""Calcule l'avancement : SUIVI.md, badges shields.io et carte d'avancement.

    python outils/stats.py                     # -> build/suivi/
    python outils/stats.py --sortie DOSSIER
    python outils/stats.py --court             # affiche seulement le résumé

Lancé automatiquement par .github/workflows/suivi.yml à chaque fusion, qui
publie le résultat sur la branche « suivi ». La branche main est protégée :
aucun robot n'y écrit. Le README affiche la carte et le badge depuis la
branche « suivi ». Personne ne met ces fichiers à jour à la main : c'est la
seule façon qu'ils soient justes.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

import commun
import memoire

DEPOT = "https://github.com/Grimoire-du-Coeur/PQ2-FR-3DS"
CATEGORIES = [("histoire", "Histoire"), ("donjons", "Donjons"), ("combat", "Combat"),
              ("systeme", "Système"), ("noms", "Noms")]
BARRE = 24
_MOT = re.compile(r"[A-Za-z][A-Za-z'’-]*")
_BALISE = re.compile(r"\{[^{}]*\}")


@dataclass
class Compte:
    categories: dict[str, list[int]] = field(default_factory=dict)   # [traduits, total]
    dossiers: dict[str, list[int]] = field(default_factory=dict)
    mots: list[int] = field(default_factory=lambda: [0, 0])          # mots anglais, hors noms
    revoir: list[tuple[str, str]] = field(default_factory=list)
    propages: int = 0                       # entrées couvertes par la mémoire (memoire.py)
    divergences: list = field(default_factory=list)

    def total(self) -> tuple[int, int]:
        return (sum(v[0] for v in self.categories.values()),
                sum(v[1] for v in self.categories.values()))


def compter(trad: Path = commun.TRAD) -> Compte:
    c = Compte(categories={cle: [0, 0] for cle, _ in CATEGORIES})
    reprises = memoire.construire(trad)
    c.divergences = reprises.divergences()
    for p in commun.fichiers_trad(trad):
        rel = p.relative_to(trad).as_posix()
        parties = rel.split("/")
        categorie = parties[0]
        dossier = "/".join(parties[:2]) if len(parties) > 2 else categorie
        for e in commun.lire_json(p):
            propage = categorie != "noms" and reprises.couvre(e)
            fait = bool(e.get("fr")) or propage
            c.propages += propage
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


def pourcentage(fait: int, total: int) -> str:
    """« 37 % », avec une décimale sous 10 % pour que les premiers pas se voient."""
    if not total:
        return "0 %"
    p = 100 * fait / total
    if fait and p < 0.1:
        return "< 0,1 %"
    if p < 10 and fait:                      # tronqué, comme les entiers : jamais surévalué
        return f"{math.floor(p * 10) / 10:.1f} %".replace(".", ",")
    return f"{int(p)} %"


def barre(fait: int, total: int) -> str:
    n = round(BARRE * fait / total) if total else 0
    return "█" * n + "░" * (BARRE - n)


def _nombre(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def bloc(c: Compte) -> str:
    lignes = []
    for cle, nom in CATEGORIES:
        f, t = c.categories.get(cle, [0, 0])
        lignes.append(f"{nom:<14} {barre(f, t)} {pourcentage(f, t):>6}   {_nombre(f):>7} / {_nombre(t)} textes")
    f, t = c.total()
    lignes.append("")
    lignes.append(f"{'Total':<14} {barre(f, t)} {pourcentage(f, t):>6}   {_nombre(f):>7} / {_nombre(t)} textes")
    lignes.append(f"{'':<14} {_nombre(c.mots[0])} mots traduits sur {_nombre(c.mots[1])}")
    if c.propages:
        lignes.append(f"{'':<14} dont {_nombre(c.propages)} par propagation (répliques identiques)")
    return "```text\n" + "\n".join(lignes) + "\n```"


def _couleur(fait: int, total: int) -> str:
    p = pct(fait, total)
    return "CE1126" if p < 25 else "F2541B" if p < 75 else "2EC4C6"


def ecrire_badges(c: Compte, dossier: Path) -> None:
    dossier.mkdir(parents=True, exist_ok=True)
    badges = {"badge.json": ("traduction", *c.total())}
    for cle, nom in CATEGORIES:
        badges[f"badge_{cle}.json"] = (nom.lower(), *c.categories.get(cle, [0, 0]))
    for nom, (etiquette, fait, total) in badges.items():
        contenu = {"schemaVersion": 1, "label": etiquette, "message": pourcentage(fait, total),
                   "color": _couleur(fait, total), "labelColor": "0D0D0D", "style": "for-the-badge"}
        (dossier / nom).write_text(json.dumps(contenu, ensure_ascii=False) + "\n",
                                   encoding="utf-8", newline="\n")


def suivi(c: Compte) -> str:
    morceaux = [
        "# Avancement de la traduction",
        "",
        "> Fichier **généré** par `outils/stats.py` et publié sur la branche `suivi` à chaque "
        f"fusion. Pour participer : [guide de contribution]({DEPOT}/blob/main/CONTRIBUTING.md) "
        f"et [méthode de travail]({DEPOT}/blob/main/docs/GUIDE.md).",
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
        morceaux.append(f"| [`{dossier}`]({DEPOT}/blob/main/trad/{dossier}) | "
                        f"{_nombre(f)} / {_nombre(t)} | {pourcentage(f, t)} |")
    if c.divergences:
        morceaux += ["", "## À harmoniser", "",
                     "Ces répliques ont le même anglais mais plusieurs traductions. Au build, la plus "
                     "fréquente est reprise pour les entrées vides : choisir la bonne, puis aligner les autres.",
                     ""]
        for en, variantes in c.divergences[:50]:
            choix = " · ".join(f"« {fr} » ×{n}" for fr, n in variantes.items())
            morceaux.append(f"- `{en}` → {choix}")
    if c.revoir:
        morceaux += ["", "## À relire", "",
                     "L'anglais de ces entrées a changé depuis leur traduction : relire, puis "
                     "supprimer le champ `a_revoir`.", ""]
        morceaux += [f"- [`{rel}`]({DEPOT}/blob/main/trad/{rel}) — `{ident}`" for rel, ident in c.revoir]
    return "\n".join(morceaux) + "\n"


def carte(c: Compte) -> str:
    """Carte d'avancement animée (barres qui se remplissent), thème salle de cinéma."""
    W, H = 1200, 360
    police = "font-family=\"'Segoe UI','Helvetica Neue',Arial,sans-serif\""
    x_barre, l_barre = 214, 700
    lignes = []
    for i, (cle, nom) in enumerate(CATEGORIES):
        f, t = c.categories.get(cle, [0, 0])
        y = 120 + i * 36
        largeur = 0 if not t else max(l_barre * f / t, 5 if f else 0)
        lignes.append(
            f'<text x="48" y="{y + 12}" {police} font-size="17" font-weight="600" fill="#F5F5F5">{nom}</text>'
            f'<rect x="{x_barre}" y="{y}" width="{l_barre}" height="14" rx="7" fill="#1A0609" '
            f'stroke="#FFC857" stroke-opacity=".35"/>'
            + (f'<rect class="barre" style="animation-delay:{.25 + i * .12:.2f}s" x="{x_barre}" y="{y}" '
               f'width="{largeur:.1f}" height="14" rx="7" fill="url(#remplissage)"/>' if largeur else "")
            + f'<text x="{x_barre + l_barre + 74}" y="{y + 12}" {police} font-size="16" font-weight="700" '
              f'fill="#FFE9A8" text-anchor="end">{pourcentage(f, t)}</text>'
            f'<text x="1152" y="{y + 12}" {police} font-size="14" fill="#F5F5F5" fill-opacity=".7" '
            f'text-anchor="end">{_nombre(f)} / {_nombre(t)}</text>')
    perfos = "".join(f'<rect x="{x}" y="{y}" width="16" height="7" rx="2" fill="#F5F5F5" opacity=".18"/>'
                     for x in range(30, 1170, 40) for y in (14, H - 21))
    f, t = c.total()
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t">
<title id="t">Avancement de la traduction : {pourcentage(f, t)} ({_nombre(f)} textes sur {_nombre(t)})</title>
<defs>
<linearGradient id="fond" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#2A0A10"/><stop offset="1" stop-color="#0B0305"/></linearGradient>
<linearGradient id="remplissage" x1="0" x2="1"><stop offset="0" stop-color="#CE1126"/><stop offset="1" stop-color="#FF5A1F"/></linearGradient>
</defs>
<style>.barre{{transform-box:fill-box;transform-origin:0 50%;animation:pousse 1.6s cubic-bezier(.2,.8,.2,1) both}}@keyframes pousse{{from{{transform:scaleX(0)}}}}.clignote{{animation:clignote 1.4s steps(1) infinite}}@keyframes clignote{{50%{{opacity:.35}}}}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}}}</style>
<rect x="1" y="1" width="{W - 2}" height="{H - 2}" rx="18" fill="url(#fond)" stroke="#FFC857" stroke-width="2"/>
{perfos}
<circle class="clignote" cx="54" cy="66" r="5" fill="#FF5A1F"/>
<text x="70" y="72" {police} font-size="15" font-weight="700" letter-spacing="4" fill="#FFC857">AVANCEMENT DE LA TRADUCTION</text>
<text x="1152" y="78" {police} font-size="40" font-weight="800" fill="#F5F5F5" text-anchor="end">{pourcentage(f, t)}</text>
<text x="1152" y="100" {police} font-size="13" fill="#F5F5F5" fill-opacity=".6" text-anchor="end">{_nombre(f)} textes sur {_nombre(t)}</text>
{"".join(lignes)}
<text x="48" y="{H - 44}" {police} font-size="13" fill="#FFE9A8" fill-opacity=".8">{_nombre(c.mots[0])} mots traduits sur {_nombre(c.mots[1])} · recalculé à chaque fusion</text>
</svg>
'''


def publier(c: Compte, dossier: Path) -> None:
    """Écrit SUIVI.md, les badges et la carte dans ``dossier``."""
    dossier.mkdir(parents=True, exist_ok=True)
    (dossier / "SUIVI.md").write_text(suivi(c), encoding="utf-8", newline="\n")
    ecrire_badges(c, dossier)
    (dossier / "avancement.svg").write_text(carte(c), encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--sortie", type=Path, default=commun.BUILD / "suivi",
                        help="dossier où écrire SUIVI.md, les badges et la carte")
    parser.add_argument("--court", action="store_true", help="afficher le résumé seulement")
    args = parser.parse_args()
    c = compter()
    print(bloc(c).strip("`").replace("text\n", "", 1))
    if not args.court:
        publier(c, args.sortie)
        print(f"→ {args.sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
