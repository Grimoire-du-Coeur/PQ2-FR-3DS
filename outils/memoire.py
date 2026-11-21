"""Mémoire de traduction : une réplique traduite une fois l'est partout.

    python outils/memoire.py               # couverture et divergences

Persona Q2 répète beaucoup : 3 149 entrées de trad/ ont exactement le même
anglais qu'une autre (« Arf! » 138 fois, les choix « Yes / No »…). Plutôt
que de recopier le français dans chaque doublon, le build reprend la
traduction déjà faite pour un anglais identique : il suffit de traduire une
réplique une fois. Remplir le champ « fr » d'une entrée garde la main sur
elle (un même anglais peut demander un autre français selon la scène).

Quand un même anglais a été traduit de plusieurs façons, la plus fréquente
gagne, et la divergence est listée dans le suivi pour être harmonisée.
"""

from __future__ import annotations

import sys
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

import commun


@dataclass
class Memoire:
    variantes: dict[str, Counter] = field(default_factory=dict)   # anglais -> {français: nombre}

    def proposer(self, en: str) -> str | None:
        """La traduction retenue pour cet anglais, ou None."""
        v = self.variantes.get(en)
        return v.most_common(1)[0][0] if v else None

    def couvre(self, entree: dict) -> bool:
        """Vrai si l'entrée n'a pas de français mais en recevra un par propagation."""
        return not entree.get("fr") and entree.get("en") in self.variantes

    def divergences(self) -> list[tuple[str, dict[str, int]]]:
        """Anglais traduits de plusieurs façons, du plus au moins disputé."""
        sortie = [(en, dict(v.most_common())) for en, v in self.variantes.items() if len(v) > 1]
        return sorted(sortie, key=lambda x: (-sum(x[1].values()), x[0]))


def construire(trad: Path = commun.TRAD) -> Memoire:
    m = Memoire()
    for p in commun.fichiers_trad(trad):
        if p.relative_to(trad).parts[0] == "noms":
            continue
        for e in commun.lire_json(p):
            if e.get("fr"):
                # Counter garde l'ordre de première apparition : à égalité, le
                # premier fichier dans l'ordre alphabétique l'emporte.
                m.variantes.setdefault(e["en"], Counter())[e["fr"]] += 1
    return m


def main() -> int:
    m = construire()
    couverts = sum(1 for p in commun.fichiers_trad() if p.relative_to(commun.TRAD).parts[0] != "noms"
                   for e in commun.lire_json(p) if m.couvre(e))
    print(f"{len(m.variantes)} répliques anglaises traduites ; {couverts} entrée(s) de plus "
          "en reçoivent la traduction par propagation.")
    div = m.divergences()
    print(f"{len(div)} réplique(s) traduite(s) de plusieurs façons.")
    for en, variantes in div[:20]:
        print(f"  {en!r}")
        for fr, n in variantes.items():
            print(f"      {n:3} × {fr!r}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
