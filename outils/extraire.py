"""Crée ou met à jour trad/**.json à partir de l'image du jeu.

    python outils/extraire.py "chemin/vers/Persona Q2 (Europe).3ds"
    python outils/extraire.py "…" --verifier    # n'écrit rien, échoue si trad/ est en retard

Une entrée par message à traduire :

    {"id": "MSG_012", "locuteur": "Yosuke", "en": "…{PAGE}…", "fr": ""}

Les choix portent ``"choix": true`` et séparent leurs options par
``{OPTION}``. Les messages sans aucun mot latin (restes japonais du
développement, fiches d'aide factices) ne sont pas extraits : le jeu les
garde tels quels. Les noms de locuteurs se traduisent une seule fois, dans
trad/noms/locuteurs.json, et ceux des objets dans trad/noms/objets.json
(voir noms.py).

Aucune traduction n'est jamais perdue :

- une entrée dont l'anglais a changé garde son français et reçoit
  ``"a_revoir"`` avec l'ancien anglais, pour qu'un humain tranche ;
- une entrée disparue qui avait un français part dans
  ``trad/_orphelins.json`` au lieu d'être effacée.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import commun
import msg1
import noms
import texte
from catalogue import Script, identifiants, lire_scripts
from msg1 import AUCUN_LOCUTEUR
from rom3ds import ErreurImage

LOCUTEURS = "noms/locuteurs.json"
ORPHELINS = "_orphelins.json"
_CONSERVES = ("a_revoir", "commentaire")

# Marqueurs laissés par les développeurs à la place d'un vrai texte (cases
# vides, aides jamais écrites, écrans de test) : relevés sur le jeu le
# 21/11/2026, ~690 entrées. Personne ne doit les traduire. « None » et
# « Reserve » n'y sont pas : ils peuvent s'afficher dans un menu, comme
# « Learned all skills dummy MSG. », que Tyron26 a vu et traduit.
_FACTICES = {"dummy", "not used", "unused", "reserved", "reserve myth", "blank"}
_FACTICE = re.compile(r"^(test( \d+| [A-Z]+)|.+ skill help text not used\.)$", re.I)


def est_factice(lisible: str) -> bool:
    """Vrai si toutes les pages du message ne sont que des marqueurs de développement."""
    pages = re.split(r"\{PAGE\}|\{OPTION\}", lisible)
    nues = [" ".join(re.sub(r"\{[^{}]*\}", " ", p).split()) for p in pages]
    return all(n.lower() in _FACTICES or _FACTICE.match(n) for n in nues if n) and any(nues)


def _entrees_script(script: Script) -> list[dict]:
    noms = [texte.decoder_texte(n) for n in script.messages.locuteurs]
    entrees = []
    for ident, m in zip(identifiants(script.messages.messages), script.messages.messages):
        lisibles = [texte.decouper_page(p)[1] for p in m.pages]
        if not any(texte.est_a_traduire(t) for t in lisibles):
            continue
        if est_factice(texte.PAGE.join(lisibles)):
            continue
        e: dict = {"id": ident}
        if not m.choix and m.locuteur != AUCUN_LOCUTEUR and m.locuteur < len(noms):
            e["locuteur"] = noms[m.locuteur]
        if m.choix:
            e["choix"] = True
        e["en"] = (texte.OPTION if m.choix else texte.PAGE).join(lisibles)
        e["fr"] = ""
        entrees.append(e)
    return entrees


def _fusionner(rel: str, e: dict, anciennes: dict, revoir: list[str]) -> dict:
    old = anciennes.get((rel, e["id"]), {})
    e["fr"] = old.get("fr", "")
    if e["fr"] and old.get("en") not in (None, e["en"]):
        e["a_revoir"] = old["en"]
        revoir.append(f"{rel} {e['id']}")
    for champ in _CONSERVES:
        if champ in old and champ not in e:
            e[champ] = old[champ]
    return e


def construire(scripts: list[Script], anciennes: dict, objets: list[str] | None = None
               ) -> tuple[dict[str, list[dict]], list[dict], list[str]]:
    """(fichiers de trad/, orphelins, entrées à revoir).

    ``objets`` : les noms d'objets à traduire (noms.noms_a_traduire).
    """
    fichiers: dict[str, list[dict]] = {}
    origine: dict[str, str] = {}
    revoir: list[str] = []
    locuteurs: set[str] = set()
    partages: dict[str, bytes] = {}
    for s in scripts:
        rel = s.trad
        contenu = msg1.ecrire_msg1(s.messages)
        if rel in origine:
            # Une copie identique (fichier isolé et son double dans une archive)
            # partage le JSON ; deux scripts différents, jamais.
            if partages[rel] == contenu:
                continue
            raise ValueError(f"{rel} : deux fichiers du jeu y mènent ({origine[rel]}, {s.chemin})")
        origine[rel] = s.chemin
        partages[rel] = contenu
        locuteurs.update(texte.decoder_texte(n) for n in s.messages.locuteurs)
        entrees = [_fusionner(rel, e, anciennes, revoir) for e in _entrees_script(s)]
        if entrees:
            fichiers[rel] = entrees
    fichiers[LOCUTEURS] = [_fusionner(LOCUTEURS, {"id": n, "en": n, "fr": ""}, anciennes, revoir)
                           for n in sorted(locuteurs, key=lambda n: (n.casefold(), n))]
    if objets is not None:
        fichiers[noms.TRAD] = [_fusionner(noms.TRAD, {"id": n, "en": n, "max": noms.CASE - 1, "fr": ""},
                                          anciennes, revoir) for n in objets]

    presents = {(rel, e["id"]) for rel, entrees in fichiers.items() for e in entrees}
    orphelins = [{"fichier": rel, **e} for (rel, ident), e in sorted(anciennes.items())
                 if (rel, ident) not in presents and e.get("fr")]
    return fichiers, orphelins, revoir


def _attendu(fichiers: dict[str, list[dict]], orphelins: list[dict]) -> dict[str, str]:
    contenu = {rel: commun.texte_json(entrees) for rel, entrees in fichiers.items()}
    if orphelins:
        contenu[ORPHELINS] = commun.texte_json(orphelins)
    return contenu


def _presents(racine: Path) -> set[str]:
    if not racine.exists():
        return set()
    return {p.relative_to(racine).as_posix() for p in racine.rglob("*.json")}


def differences(fichiers: dict[str, list[dict]], orphelins: list[dict], racine: Path) -> list[str]:
    """Fichiers de ``racine`` qui ne correspondent pas à ce que l'extraction écrirait."""
    attendu = _attendu(fichiers, orphelins)
    ecarts = []
    for rel in sorted(attendu.keys() | _presents(racine)):
        p = racine / rel
        actuel = p.read_text(encoding="utf-8") if p.exists() else None
        if actuel != attendu.get(rel):
            ecarts.append(rel)
    return ecarts


def ecrire(fichiers: dict[str, list[dict]], orphelins: list[dict], racine: Path) -> None:
    attendu = _attendu(fichiers, orphelins)
    for rel in _presents(racine) - attendu.keys():
        (racine / rel).unlink()
    for rel, contenu in attendu.items():
        p = racine / rel
        if not p.exists() or p.read_text(encoding="utf-8") != contenu:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(contenu, encoding="utf-8", newline="\n")
    for dossier in sorted((d for d in racine.rglob("*") if d.is_dir()), reverse=True):
        if not any(dossier.iterdir()):
            dossier.rmdir()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("image", type=Path, help="image .3ds décryptée, ou data.cpk")
    parser.add_argument("--verifier", action="store_true",
                        help="n'écrit rien ; code 1 si trad/ n'est pas à jour")
    parser.add_argument("--trad", type=Path, default=commun.TRAD, help=argparse.SUPPRESS)
    args = parser.parse_args()
    try:
        scripts = lire_scripts(args.image)
        objets = noms.noms_a_traduire(noms.lire_table(args.image))
    except (ErreurImage, noms.ErreurNom) as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2

    anciennes = commun.charger_traductions(args.trad)
    fichiers, orphelins, revoir = construire(scripts, anciennes, objets)
    fichier_orphelins = args.trad / ORPHELINS
    if fichier_orphelins.exists():
        deja = commun.lire_json(fichier_orphelins)
        nouveaux = {(o["fichier"], o["id"]) for o in orphelins}
        orphelins += [o for o in deja if (o["fichier"], o["id"]) not in nouveaux]

    if args.verifier:
        ecarts = differences(fichiers, orphelins, args.trad)
        for rel in ecarts[:20]:
            print(f"pas à jour : trad/{rel}")
        print("trad/ est à jour." if not ecarts else f"{len(ecarts)} fichier(s) à régénérer.")
        return 1 if ecarts else 0

    ecrire(fichiers, orphelins, args.trad)
    entrees = [e for rel, es in fichiers.items() if not rel.startswith("noms/") for e in es]
    mots = sum(len(re.findall(r"[A-Za-z][A-Za-z'’-]*", re.sub(r"\{[^}]*\}", " ", e["en"])))
               for e in entrees)
    print(f"{len(fichiers) - 2} fichiers, {len(entrees)} messages ({mots} mots anglais), "
          f"{len(fichiers[LOCUTEURS])} locuteurs, {len(fichiers[noms.TRAD])} noms d'objets.")
    print(f"À revoir : {len(revoir)}. Orphelins : {len(orphelins)}.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
