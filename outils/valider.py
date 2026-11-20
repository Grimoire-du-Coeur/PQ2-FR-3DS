"""Vérifie les traductions de trad/ avant qu'elles partent en jeu.

    python outils/valider.py                              # tout trad/
    python outils/valider.py trad/histoire/e000/e000_015.json
    python outils/valider.py --github --base <commit> trad/…   # dans la CI

ERREUR    = le build casserait, ou le texte serait faux à coup sûr. Bloquant.
ATTENTION = à regarder : ligne trop large, terme du dictionnaire, typographie.

Avec ``--base``, chaque fichier est aussi comparé à sa version sur la branche
cible : on refuse une proposition qui modifie l'anglais ou un identifiant, ou
qui efface une traduction (c'est ce que fait la copie périmée d'un fork).

Ne lit aucune donnée du jeu : la CI le lance sur chaque Pull Request.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import commun
import texte
from mesurer import largeur_ligne

CHAMPS = {"id", "locuteur", "choix", "en", "fr", "a_revoir", "commentaire"}
FIGES = ("id", "locuteur", "choix", "en")
LIGNES_PAR_BULLE = 3
_CODE = re.compile(r"\{f [^{}]*\}")
_BALISE = re.compile(r"\{[^{}]*\}")
# Typographie française : une espace avant « ! ? ; » et avant « : » (sauf 10:30) ;
# « !? » et « ?? » restent permis.
_SANS_ESPACE = re.compile(r"[^\s{}\d.…\"“”'’!?][!?;]|[^\s{}\d]:(?!\d)")

DICTIONNAIRE = commun.RACINE / "docs" / "Dictionnaire.md"
LARGEURS = commun.RACINE / "police" / "largeurs.json"


@dataclass
class Remarque:
    niveau: str          # ERREUR ou ATTENTION
    fichier: str         # chemin depuis la racine du dépôt (trad/…)
    id: str
    texte: str
    ligne: int = 1


def lire_dictionnaire(chemin: Path) -> list[tuple[list[str], list[str]]]:
    """Termes validés (✅) du dictionnaire : [(formes anglaises, formes françaises)]."""
    if not chemin.exists():
        return []
    termes = []
    for ligne in chemin.read_text(encoding="utf-8").splitlines():
        cellules = [c.strip() for c in ligne.strip().strip("|").split("|")]
        if len(cellules) < 3 or "✅" not in cellules[-1]:
            continue

        def formes(cellule: str) -> list[str]:
            cellule = re.sub(r"\*\(.*?\)\*|\(.*?\)|\*\*|`", "", cellule).split(" — ")[0]
            return [f.strip() for f in cellule.split(" / ") if len(f.strip()) >= 3]

        en, fr = formes(cellules[0]), formes(cellules[1])
        if en and fr:
            termes.append((en, fr))
    return termes


def _charger_largeurs() -> dict:
    if LARGEURS.exists():
        return json.loads(LARGEURS.read_text(encoding="utf-8"))
    return {"largeurs": {}, "limites": {}}


def _ligne_du_champ(lignes: list[str], ident: str, champ: str = "fr") -> int:
    """Numéro (1…) de la ligne du champ ``champ`` de l'entrée ``ident``."""
    cle = f'"id": {json.dumps(ident, ensure_ascii=False)}'
    for i, l in enumerate(lignes):
        if cle in l:
            for j in range(i, min(i + 12, len(lignes))):
                if lignes[j].lstrip().startswith(f'"{champ}"'):
                    return j + 1
            return i + 1
    return 1


def _verifier_texte(e: dict, partie: str, largeurs: dict, dico) -> list[tuple[str, str]]:
    remarques: list[tuple[str, str]] = []
    fr, en = e.get("fr", ""), e.get("en", "")
    if not fr:
        return remarques
    choix = bool(e.get("choix"))
    sep, autre = (texte.OPTION, texte.PAGE) if choix else (texte.PAGE, texte.OPTION)
    nom = "option" if choix else "page"
    if autre in fr:
        remarques.append(("ERREUR", f"{autre} n'a pas sa place ici : séparer avec {sep}"))
    pages_en, pages_fr = en.split(sep), fr.split(sep)
    if len(pages_en) != len(pages_fr):
        remarques.append(("ERREUR", f"{len(pages_fr)} {nom}(s) en français pour {len(pages_en)} "
                                    f"en anglais : garder le même nombre de {sep}"))
        return remarques

    table = largeurs.get("largeurs", {})
    limite = largeurs.get("limites", {}).get(partie)
    for k, (p_en, p_fr) in enumerate(zip(pages_en, pages_fr), 1):
        ou = f"{nom} {k}" if len(pages_en) > 1 else ""
        if not p_fr.strip() and p_en.strip():
            remarques.append(("ERREUR", f"{ou or nom} vide en français"))
            continue
        try:
            texte.encoder_texte(texte.adapter(p_fr))
        except texte.ErreurTexte as err:
            remarques.append(("ERREUR", f"{ou + ' : ' if ou else ''}{err}"))
        codes_en, codes_fr = _CODE.findall(p_en), _CODE.findall(p_fr)
        if Counter(codes_en) != Counter(codes_fr):
            manque = list((Counter(codes_en) - Counter(codes_fr)).elements())
            trop = list((Counter(codes_fr) - Counter(codes_en)).elements())
            details = (f"manque {' '.join(manque)}" if manque else "") + \
                      (" ; " if manque and trop else "") + (f"en trop {' '.join(trop)}" if trop else "")
            remarques.append(("ERREUR", f"{ou + ' : ' if ou else ''}balises de code différentes "
                                        f"de l'anglais ({details})"))
        elif codes_en != codes_fr:
            remarques.append(("ATTENTION", f"{ou + ' : ' if ou else ''}balises de code dans un "
                                           "autre ordre que l'anglais : vérifier en jeu"))

        lignes_en, lignes_fr = p_en.split(texte.SAUT), p_fr.split(texte.SAUT)
        if len(lignes_fr) > max(len(lignes_en), LIGNES_PAR_BULLE):
            remarques.append(("ATTENTION", f"{ou + ' : ' if ou else ''}{len(lignes_fr)} lignes, "
                                           f"l'anglais en a {len(lignes_en)}"))
        if table and limite:
            plafond = max(limite, max(largeur_ligne(l, table) for l in lignes_en))
            for n, l in enumerate(lignes_fr, 1):
                w = largeur_ligne(texte.adapter(l), table)
                if w > plafond:
                    remarques.append(("ATTENTION", f"{ou + ', ' if ou else ''}ligne {n} : {w} px, "
                                                   f"la bulle en tient environ {plafond}"))

    nu = _BALISE.sub(" ", fr)
    for m in _SANS_ESPACE.finditer(nu):
        signe = m.group(0)[-1]
        remarques.append(("ATTENTION", f"espace manquante avant « {signe} » "
                                       f"(…{nu[max(0, m.start() - 12):m.end()]})"))
        break
    if "  " in nu and "  " not in _BALISE.sub(" ", en):
        remarques.append(("ATTENTION", "double espace"))
    for formes_en, formes_fr in dico:
        if any(re.search(rf"\b{re.escape(t)}\b", en, re.I) for t in formes_en) and \
                not any(t.lower() in fr.lower() for t in formes_fr):
            remarques.append(("ATTENTION", f"« {formes_en[0]} » se traduit « {formes_fr[0]} » "
                                           "(docs/Dictionnaire.md)"))
    if e.get("a_revoir"):
        remarques.append(("ATTENTION", "l'anglais a changé : relire, puis supprimer a_revoir"))
    return remarques


def verifier_fichier(chemin: Path, trad: Path = commun.TRAD, base: list | None = None,
                     largeurs: dict | None = None, dico=None) -> list[Remarque]:
    largeurs = _charger_largeurs() if largeurs is None else largeurs
    dico = lire_dictionnaire(DICTIONNAIRE) if dico is None else dico
    rel = "trad/" + chemin.relative_to(trad).as_posix()
    partie = chemin.relative_to(trad).parts[0]
    contenu = chemin.read_text(encoding="utf-8")
    lignes = contenu.splitlines()
    try:
        entrees = json.loads(contenu)
    except json.JSONDecodeError as err:
        return [Remarque("ERREUR", rel, "-", f"JSON invalide : {err.msg}", err.lineno)]
    if not isinstance(entrees, list) or not all(isinstance(e, dict) and "id" in e for e in entrees):
        return [Remarque("ERREUR", rel, "-", "le fichier doit être une liste d'entrées avec un id")]

    remarques: list[Remarque] = []
    vus: set[str] = set()
    for e in entrees:
        ident = e["id"]
        ligne = _ligne_du_champ(lignes, ident)
        if ident in vus:
            remarques.append(Remarque("ERREUR", rel, ident, "identifiant présent deux fois", ligne))
        vus.add(ident)
        inconnus = sorted(set(e) - CHAMPS)
        if inconnus:
            remarques.append(Remarque("ERREUR", rel, ident, f"champ inconnu : {', '.join(inconnus)}",
                                      ligne))
        for niveau, message in _verifier_texte(e, partie, largeurs, dico):
            remarques.append(Remarque(niveau, rel, ident, message, ligne))

    if base is not None:
        anciennes = {e.get("id"): e for e in base if isinstance(e, dict)}
        nouvelles = {e["id"]: e for e in entrees}
        for ident in sorted(anciennes.keys() - nouvelles.keys()):
            remarques.append(Remarque("ERREUR", rel, ident, "entrée supprimée"))
        for ident in sorted(nouvelles.keys() - anciennes.keys()):
            remarques.append(Remarque("ERREUR", rel, ident, "entrée ajoutée : seul l'outil "
                                      "d'extraction ajoute des entrées",
                                      _ligne_du_champ(lignes, ident, "id")))
        for ident in sorted(anciennes.keys() & nouvelles.keys()):
            a, n = anciennes[ident], nouvelles[ident]
            for champ in FIGES:
                if a.get(champ) != n.get(champ):
                    remarques.append(Remarque("ERREUR", rel, ident, f"le champ « {champ} » ne se "
                                              "modifie pas", _ligne_du_champ(lignes, ident, champ)))
            if a.get("fr") and not n.get("fr"):
                remarques.append(Remarque("ERREUR", rel, ident, "traduction effacée : la copie de "
                                          "ce fichier est peut-être périmée (mettre son fork à jour)",
                                          _ligne_du_champ(lignes, ident)))
    return remarques


def annotation(r: Remarque) -> str:
    """Annotation GitHub, posée directement sur la ligne du diff."""
    genre = "error" if r.niveau == "ERREUR" else "warning"
    message = f"{r.id} : {r.texte}".replace("%", "%25").replace("\n", "%0A")
    return f"::{genre} file={r.fichier},line={r.ligne},title={r.niveau}::{message}"


def _version_de_base(base: str, chemin: Path) -> list | None:
    rel = chemin.resolve().relative_to(commun.RACINE).as_posix()
    res = subprocess.run(["git", "show", f"{base}:{rel}"], cwd=commun.RACINE,
                         capture_output=True, text=True, encoding="utf-8")
    if res.returncode != 0:
        return None                 # fichier nouveau sur cette branche
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("fichiers", nargs="*", type=Path, help="fichiers de trad/ (défaut : tous)")
    parser.add_argument("--github", action="store_true", help="annotations pour les Pull Requests")
    parser.add_argument("--base", help="commit de la branche cible, pour comparer")
    parser.add_argument("--erreurs", action="store_true", help="n'afficher que les erreurs")
    args = parser.parse_args()
    fichiers = [f.resolve() for f in args.fichiers] or commun.fichiers_trad()
    largeurs, dico = _charger_largeurs(), lire_dictionnaire(DICTIONNAIRE)
    remarques: list[Remarque] = []
    for f in fichiers:
        if f.name.startswith("_") or f.suffix != ".json":
            continue
        base = _version_de_base(args.base, f) if args.base else None
        remarques += verifier_fichier(f, base=base, largeurs=largeurs, dico=dico)
    erreurs = [r for r in remarques if r.niveau == "ERREUR"]
    for r in (erreurs if args.erreurs else remarques):
        print(annotation(r) if args.github else f"{r.niveau:9} {r.fichier}:{r.ligne}  {r.id}  {r.texte}")
    print(f"{len(fichiers)} fichier(s) vérifié(s) : {len(erreurs)} erreur(s), "
          f"{len(remarques) - len(erreurs)} remarque(s).")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
