"""Réinjecte trad/ dans le jeu et produit le data.cpk français.

    python outils/injecter.py "chemin/vers/Persona Q2 (Europe).3ds"            # -> build/romfs/data.cpk
    python outils/injecter.py "…" --azahar                                    # directement dans Azahar
    python outils/injecter.py "…" --sortie "E:/luma/titles/00040000001D7600/romfs/data.cpk"

Pour chaque script du jeu qui a au moins un champ "fr" rempli (ou un
locuteur traduit), les pages françaises remplacent les pages anglaises.
Le début et la fin cachés de chaque page (codes d'affichage, portrait,
attente) sont repris de la page d'origine. Une entrée sans français reprend
la traduction d'un anglais identique déjà traduit ailleurs (memoire.py), et
sinon garde son anglais : le jeu reste jouable de bout en bout à chaque étape.

Le CPK d'origine est copié une seule fois depuis l'image ; les builds
suivants ne réécrivent que la fin du fichier (quelques secondes).

Accents : la police du jeu a déjà les lettres accentuées françaises (voir
police/caracteres.json). Les rares caractères qu'elle n'a pas sont
remplacés au build : « » deviennent “ ”, æ devient ae, etc. Le texte de
trad/ garde toujours la typographie française.
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from pathlib import Path

import commun
import flw0
import memoire
import msg1
import texte
from catalogue import Script, chemin_trad, identifiants, lire_scripts
from cpk import Cpk, patcher_cpk
from extraire import LOCUTEURS
from rom3ds import TITLE_ID_EU, ErreurImage, localiser_data_cpk

SORTIE = commun.BUILD / "romfs" / "data.cpk"
adapter = texte.adapter


class ErreurInjection(ValueError):
    """Traduction impossible à injecter ; le message nomme le fichier et l'entrée."""


def dossier_azahar() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return appdata / "Azahar" / "load" / "mods" / f"{TITLE_ID_EU:016X}" / "romfs"


def _locuteurs(trad: Path) -> dict[str, str]:
    p = trad / LOCUTEURS
    if not p.exists():
        return {}
    return {e["en"]: e["fr"] for e in commun.lire_json(p) if e.get("fr")}


def _pages(rel: str, ident: str, m: msg1.Message, fr: str) -> list[bytes]:
    separateur, autre = (texte.OPTION, texte.PAGE) if m.choix else (texte.PAGE, texte.OPTION)
    if autre in fr:
        raise ErreurInjection(f"{rel} {ident} : {autre} n'a pas sa place ici, utiliser {separateur}")
    morceaux = fr.split(separateur)
    if len(morceaux) != len(m.pages):
        raise ErreurInjection(f"{rel} {ident} : {len(morceaux)} morceau(x) en français pour "
                              f"{len(m.pages)} dans le jeu (séparateur {separateur})")
    pages = []
    for k, (page, morceau) in enumerate(zip(m.pages, morceaux), 1):
        prefixe, anglais, suffixe = texte.decouper_page(page)
        if not morceau.strip() and anglais.strip():
            raise ErreurInjection(f"{rel} {ident} : la page {k} est vide en français")
        try:
            corps = texte.encoder_texte(adapter(morceau))
        except texte.ErreurTexte as e:
            raise ErreurInjection(f"{rel} {ident} : {e}") from None
        pages.append(prefixe + corps + suffixe)
    return pages


def _injecter(scripts: list[Script], trad: Path) -> tuple[dict[str, bytes], int]:
    locuteurs = _locuteurs(trad)
    reprises = memoire.construire(trad)
    sortie: dict[str, bytes] = {}
    traduits = 0
    for s in scripts:
        rel = chemin_trad(s.chemin)
        p = trad / rel
        entrees = {}
        for e in commun.lire_json(p) if p.exists() else []:
            # Une entrée sans français reprend celui d'un anglais identique déjà
            # traduit ailleurs (memoire.py) ; son propre « fr » garde la main.
            fr = e.get("fr") or reprises.proposer(e["en"])
            if fr:
                entrees[e["id"]] = {**e, "fr": fr}
        script = copy.deepcopy(s.messages)
        touche = False
        for i, nom in enumerate(script.locuteurs):
            fr = locuteurs.get(texte.decoder_texte(nom))
            if fr:
                try:
                    script.locuteurs[i] = texte.encoder_texte(adapter(fr))
                except texte.ErreurTexte as e:
                    raise ErreurInjection(f"{LOCUTEURS} {fr} : {e}") from None
                touche = True
        for ident, m in zip(identifiants(script.messages), script.messages):
            if ident in entrees:
                m.pages = _pages(rel, ident, m, entrees[ident]["fr"])
                traduits += 1
                touche = True
        if not touche:
            continue
        nouveau = msg1.ecrire_msg1(script)
        if s.chemin.endswith(".bf"):
            nouveau = flw0.remplacer_messages(s.brut, nouveau)
        if nouveau != s.brut:
            sortie[s.chemin] = nouveau
    return sortie, traduits


def remplacements(scripts: list[Script], trad: Path) -> dict[str, bytes]:
    """Chemin dans le CPK → fichier reconstruit, pour les seuls scripts qui changent."""
    return _injecter(scripts, trad)[0]


def _copie_valide(image: Path, position: int, taille: int, sortie: Path) -> bool:
    if not sortie.exists():
        return False
    try:
        patcher_cpk(sortie, taille, {})           # remet la copie dans son état d'origine
        with open(image, "rb") as a, open(sortie, "rb") as b:
            origine, copie = Cpk(a, base=position), Cpk(b)
            return (origine.entete_brut, origine.toc_brut) == (copie.entete_brut, copie.toc_brut)
    except (ValueError, OSError):
        return False


def _copier_cpk(image: Path, position: int, taille: int, sortie: Path) -> None:
    sortie.parent.mkdir(parents=True, exist_ok=True)
    print(f"Copie du CPK d'origine ({taille / 1e9:.1f} Go), une seule fois…")
    with open(image, "rb") as a, open(sortie, "wb") as b:
        a.seek(position)
        restant = taille
        while restant:
            bloc = a.read(min(restant, 64 * 1024 * 1024))
            b.write(bloc)
            restant -= len(bloc)


def construire(image: Path, trad: Path, sortie: Path) -> tuple[int, int]:
    """Écrit le data.cpk français ; rend (fichiers modifiés, messages traduits)."""
    scripts = lire_scripts(image)
    nouveaux, traduits = _injecter(scripts, trad)
    position, taille = localiser_data_cpk(image)
    if not _copie_valide(image, position, taille, sortie):
        _copier_cpk(image, position, taille, sortie)
    patcher_cpk(sortie, taille, nouveaux)
    return len(nouveaux), traduits


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("image", type=Path, help="image .3ds décryptée, ou data.cpk")
    cible = parser.add_mutually_exclusive_group()
    cible.add_argument("--sortie", type=Path, default=SORTIE, help="data.cpk à écrire")
    cible.add_argument("--azahar", action="store_true",
                       help="écrire dans le dossier mods d'Azahar")
    parser.add_argument("--trad", type=Path, default=commun.TRAD, help=argparse.SUPPRESS)
    args = parser.parse_args()
    sortie = dossier_azahar() / "data.cpk" if args.azahar else args.sortie
    try:
        fichiers, messages = construire(args.image, args.trad, sortie)
    except (ErreurImage, ErreurInjection) as e:
        print(f"Erreur : {e}", file=sys.stderr)
        return 2
    print(f"{messages} message(s) traduit(s) dans {fichiers} fichier(s).")
    print(f"→ {sortie}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
