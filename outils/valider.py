"""Vérifie les traductions de trad/ avant qu'elles partent en jeu.

    python outils/valider.py                              # tout trad/
    python outils/valider.py trad/histoire/e000/e000_015.json
    python outils/valider.py --github --base <commit> trad/…   # dans la CI

ERREUR    = le build casserait, ou le texte serait faux à coup sûr. Bloquant.
ATTENTION = à regarder : ligne trop large, terme du dictionnaire, typographie.

Avec ``--base``, chaque fichier est aussi comparé à sa version sur la branche
cible : on refuse une proposition qui modifie l'anglais ou un identifiant, ou
qui efface une traduction (c'est ce que fait la copie périmée d'un fork).

Avec ``--github``, les remarques deviennent des annotations sur les lignes de
la Pull Request, et la liste complète va dans le résumé de la vérification.

Ne lit aucune donnée du jeu : la CI le lance sur chaque Pull Request.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

import commun
import memoire
import noms
import texte
from mesurer import largeur_ligne

# « max » : place en octets d'un nom dans sa table (noms/objets.json).
# « locuteur_fr » : le nom français du locuteur, donné dans la scène.
CHAMPS = {"id", "locuteur", "locuteur_fr", "choix", "en", "max", "fr", "a_revoir", "commentaire"}
FIGES = ("id", "locuteur", "choix", "en", "max")
# GitHub n'affiche que 10 annotations d'erreur et 10 d'avertissement par
# étape ; au-delà, elles disparaissent sans prévenir.
ANNOTATIONS_MAX = 10
LIGNES_DU_RESUME = 500
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
        else:
            if "max" in e and noms.longueur(p_fr) > e["max"]:
                remarques.append(("ERREUR", f"{noms.longueur(p_fr)} octets, la case en tient "
                                            f"{e['max']} (une lettre accentuée compte double)"))
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


def _verifier_locuteur(e: dict, largeurs: dict) -> list[tuple[str, str]]:
    """Le nom français du locuteur, écrit dans la scène (« locuteur_fr »)."""
    if "locuteur_fr" not in e:
        return []
    fr = e["locuteur_fr"]
    if not isinstance(fr, str):
        return [("ERREUR", "« locuteur_fr » s'écrit entre guillemets")]
    if not e.get("locuteur"):
        return [("ERREUR", "« locuteur_fr » sans « locuteur » : ce message n'affiche aucun nom")]
    if not fr:
        return []
    if _BALISE.search(fr):
        return [("ERREUR", "pas de balise dans un nom de locuteur")]
    try:
        texte.encoder_texte(texte.adapter(fr))
    except texte.ErreurTexte as err:
        return [("ERREUR", f"nom du locuteur : {err}")]
    remarques = []
    if fr != fr.strip():
        remarques.append(("ATTENTION", "nom du locuteur : espace au début ou à la fin"))
    table, limite = largeurs.get("largeurs", {}), largeurs.get("limites", {}).get("noms")
    if table and limite:
        plafond = max(limite, largeur_ligne(e["locuteur"], table))
        w = largeur_ligne(texte.adapter(fr), table)
        if w > plafond:
            remarques.append(("ATTENTION", f"nom du locuteur : {w} px, plus large que les noms "
                                           f"anglais du jeu ({plafond} px) : vérifier en jeu"))
    return remarques


def verifier_fichier(chemin: Path, trad: Path = commun.TRAD, base: list | None = None,
                     largeurs: dict | None = None, dico=None, extraction: bool = False) -> list[Remarque]:
    """Remarques sur un fichier de trad/.

    ``extraction`` : la Pull Request modifie l'outillage, donc ce que sort
    l'extraction. Les entrées ajoutées, retirées ou dont l'anglais change
    sont alors permises ; une traduction effacée reste refusée (l'extraction
    range les anciennes dans _orphelins.json, elle n'en perd jamais).
    """
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
    noms_scene: dict[str, tuple[str, str]] = {}      # nom anglais -> (nom français, id)
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
        ligne_nom = _ligne_du_champ(lignes, ident, "locuteur_fr")
        for niveau, message in _verifier_locuteur(e, largeurs):
            remarques.append(Remarque(niveau, rel, ident, message, ligne_nom))
        en, fr = e.get("locuteur"), e.get("locuteur_fr")
        if isinstance(en, str) and isinstance(fr, str) and en and fr:
            # Le jeu range chaque nom une fois par script : une seule traduction possible.
            if en in noms_scene and noms_scene[en][0] != fr:
                deja, ou = noms_scene[en]
                remarques.append(Remarque("ERREUR", rel, ident, f"« {en} » est déjà traduit "
                                          f"« {deja} » plus haut ({ou}) : un nom n'a qu'une "
                                          "traduction dans une scène", ligne_nom))
            noms_scene.setdefault(en, (fr, ident))

    if base is not None:
        base = [e for e in base if isinstance(e, dict)]
        anciennes = {e.get("id"): e for e in base}
        nouvelles = {e["id"]: e for e in entrees}
        for ident in sorted(anciennes.keys() & nouvelles.keys()):
            if anciennes[ident].get("fr") and not nouvelles[ident].get("fr"):
                remarques.append(Remarque("ERREUR", rel, ident, "traduction effacée : la copie de "
                                          "ce fichier est peut-être périmée (mettre son fork à jour)",
                                          _ligne_du_champ(lignes, ident)))
        apres = memoire.noms_de_scene(entrees)
        for en, fr in sorted(memoire.noms_de_scene(base).items()):
            if en not in apres:
                ident = next((e["id"] for e in entrees if e.get("locuteur") == en), "-")
                remarques.append(Remarque("ERREUR", rel, ident, f"nom traduit effacé (« {en} » → "
                                          f"« {fr} ») : la copie de ce fichier est peut-être "
                                          "périmée (mettre son fork à jour)",
                                          _ligne_du_champ(lignes, ident, "locuteur")))
        if extraction:
            return remarques
        for ident in sorted(anciennes.keys() - nouvelles.keys()):
            remarques.append(Remarque("ERREUR", rel, ident, "entrée supprimée"))
        for ident in sorted(nouvelles.keys() - anciennes.keys()):
            remarques.append(Remarque("ERREUR", rel, ident, "entrée ajoutée : seul l'outil "
                                      "d'extraction ajoute des entrées",
                                      _ligne_du_champ(lignes, ident, "id")))
        for ident in sorted(anciennes.keys() & nouvelles.keys()):
            a, n = anciennes[ident], nouvelles[ident]
            for champ in FIGES:
                if a.get(champ) == n.get(champ):
                    continue
                message = f"le champ « {champ} » ne se modifie pas"
                if champ == "locuteur" and a.get(champ) and n.get(champ):
                    # Le geste naturel : traduire le nom là où on le voit.
                    message = (f"« locuteur » garde le nom anglais du jeu : remettre « {a[champ]} », "
                               "puis écrire le nom français juste en dessous, sur une seule réplique "
                               "de la scène : \"locuteur_fr\": "
                               f"{json.dumps(n[champ], ensure_ascii=False)},")
                remarques.append(Remarque("ERREUR", rel, ident, message,
                                          _ligne_du_champ(lignes, ident, champ)))
    return remarques


def annotation(r: Remarque, titre: str | None = None) -> str:
    """Annotation GitHub, posée directement sur la ligne du diff."""
    genre = "error" if r.niveau == "ERREUR" else "warning"
    message = f"{r.id} : {r.texte}".replace("%", "%25").replace("\r", "").replace("\n", "%0A")
    titre = (titre or r.niveau).replace("%", "%25").replace(",", "%2C").replace(":", "%3A")
    return f"::{genre} file={r.fichier},line={r.ligne},title={titre}::{message}"


def annotations(remarques: list[Remarque]) -> list[str]:
    """Les annotations de la Pull Request, sans en perdre aucune.

    GitHub n'en affiche que ANNOTATIONS_MAX de chaque niveau : quand il y en
    a plus, la dernière place regroupe toutes celles qui restent.
    """
    sortie = []
    for niveau in ("ERREUR", "ATTENTION"):
        liste = [r for r in remarques if r.niveau == niveau]
        if len(liste) <= ANNOTATIONS_MAX:
            sortie += [annotation(r) for r in liste]
            continue
        sortie += [annotation(r) for r in liste[:ANNOTATIONS_MAX - 1]]
        reste = liste[ANNOTATIONS_MAX - 1:]
        autres = "\n".join(f"- {r.fichier} ligne {r.ligne}, {r.id} : {r.texte}" for r in reste[1:])
        groupe = Remarque(niveau, reste[0].fichier, reste[0].id,
                          f"{reste[0].texte}\n\nEt {len(reste) - 1} de plus, que GitHub "
                          f"n'afficherait pas une par une :\n{autres}", reste[0].ligne)
        sortie.append(annotation(groupe, f"{niveau} (+{len(reste) - 1})"))
    return sortie


def resume(remarques: list[Remarque], n_fichiers: int) -> str:
    """Le résumé de la vérification (page de la CI), en Markdown : toutes les remarques."""
    erreurs = sum(r.niveau == "ERREUR" for r in remarques)
    lignes = ["## Vérification des traductions", "",
              f"{n_fichiers} fichier(s) vérifié(s) : **{erreurs} erreur(s)**, "
              f"{len(remarques) - erreurs} remarque(s).", ""]
    if remarques:
        lignes += ["| | Fichier | Ligne | Entrée | Remarque |", "|---|---|---:|---|---|"]
        tries = sorted(remarques, key=lambda r: r.niveau != "ERREUR")
        for r in tries[:LIGNES_DU_RESUME]:
            icone = "❌" if r.niveau == "ERREUR" else "⚠️"
            cellule = r.texte.replace("|", "\\|").replace("\n", " ")
            lignes.append(f"| {icone} | `{r.fichier}` | {r.ligne} | `{r.id}` | {cellule} |")
        if len(tries) > LIGNES_DU_RESUME:
            lignes += ["", f"… et {len(tries) - LIGNES_DU_RESUME} de plus : voir le journal de l'étape."]
    return "\n".join(lignes) + "\n"


def _texte(r: Remarque) -> str:
    return f"{r.niveau:9} {r.fichier}:{r.ligne}  {r.id}  {r.texte}"


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
    parser.add_argument("--extraction", action="store_true",
                        help="avec --base : la PR modifie l'outillage, l'extraction peut ajouter, "
                             "retirer ou mettre à jour des entrées")
    args = parser.parse_args()
    fichiers = [f.resolve() for f in args.fichiers] or commun.fichiers_trad()
    largeurs, dico = _charger_largeurs(), lire_dictionnaire(DICTIONNAIRE)
    remarques: list[Remarque] = []
    for f in fichiers:
        if f.name.startswith("_") or f.suffix != ".json":
            continue
        base = _version_de_base(args.base, f) if args.base else None
        remarques += verifier_fichier(f, base=base, largeurs=largeurs, dico=dico,
                                      extraction=args.extraction)
    erreurs = [r for r in remarques if r.niveau == "ERREUR"]
    montrees = erreurs if args.erreurs else remarques
    if args.github:
        for ligne in annotations(montrees):
            print(ligne)
        print("::group::Toutes les remarques")
        for r in montrees:
            print(_texte(r))
        print("::endgroup::")
        if os.environ.get("GITHUB_STEP_SUMMARY"):
            with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as f:
                f.write(resume(montrees, len(fichiers)))
    else:
        for r in montrees:
            print(_texte(r))
    print(f"{len(fichiers)} fichier(s) vérifié(s) : {len(erreurs)} erreur(s), "
          f"{len(remarques) - len(erreurs)} remarque(s).")
    return 1 if erreurs else 0


if __name__ == "__main__":
    sys.exit(main())
