"""Tables de noms à cases fixes : objets, lieux.

    init/itemtbl.bin     → trad/noms/objets.json
    camp/dictionary.tbl  → trad/noms/lieux.json

Chaque nom occupe une case de taille fixe, terminé par un zéro et complété
de zéros. Un même nom revient souvent dans plusieurs cases (« Medicine »,
« 1st Ave.~ ») : il se traduit une seule fois et part dans toutes ses
cases. Le fichier ne change pas de taille : chaque nom a une place limitée,
rappelée par le champ « max » du JSON, où une lettre accentuée compte pour
deux octets (voir police/caracteres.json).

- itemtbl.bin finit par 3 584 cases de 22 octets, une par numéro d'objet
  (0x000 à 0xDFF). Les menus, les boutiques et les dialogues y lisent le
  nom d'un objet.
- dictionary.tbl : 152 fiches de 60 octets, les lieux où l'on croise
  chaque ennemi. Le nom est à +8 ; des drapeaux suivent à +30 et +32, le
  nom garde donc 20 octets, zéro final compris.

Relevé sur la version européenne le 21/11/2026.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import texte


@dataclass(frozen=True)
class TableFixe:
    chemin: str         # dans le CPK
    trad: str           # dans trad/
    debut: int          # position de la première case
    nombre: int         # nombre de cases
    case: int           # taille d'une case
    decalage: int       # position du nom dans la case
    place: int          # octets réservés au nom, zéro final compris

    @property
    def fin(self) -> int:
        return self.debut + self.nombre * self.case

    @property
    def max(self) -> int:
        return self.place - 1


OBJETS = TableFixe("init/itemtbl.bin", "noms/objets.json", 0x065820, 0xE00, 22, 0, 22)
LIEUX = TableFixe("camp/dictionary.tbl", "noms/lieux.json", 0, 152, 60, 8, 20)
TABLES_FIXES = (OBJETS, LIEUX)

# Cases sans vrai nom, jamais affichées : « NULL », « Reserved », numéros
# génériques (« Weapon 0x1F4 », « 0x623 »), noms provisoires, et les
# marqueurs qui ouvrent chaque catégorie d'objets (« Armor Start »…).
_FACTICE = re.compile(r"^(NULL|Reserved|Not Used.*|(.+ )?0x[0-9A-F]+|\(prov\).*|.+ (start|from here))$",
                      re.IGNORECASE)


class ErreurNom(ValueError):
    pass


def _positions(brut: bytes, table: TableFixe) -> range:
    if len(brut) != table.fin:          # les deux tables finissent leur fichier
        raise ErreurNom(f"{table.chemin} : {len(brut)} octets au lieu de {table.fin} "
                        "(une autre version du jeu ?)")
    return range(table.debut + table.decalage, table.fin, table.case)


def lire_noms(brut: bytes, table: TableFixe = OBJETS) -> list[str]:
    """Le nom de chaque case, dans l'ordre de la table."""
    return [texte.decoder_texte(brut[p:p + table.place].split(b"\0")[0]) for p in _positions(brut, table)]


def noms_a_traduire(brut: bytes, table: TableFixe = OBJETS) -> list[str]:
    """Les noms à traduire, sans doublon, dans l'ordre de la table (armes, armures…)."""
    return list(dict.fromkeys(n for n in lire_noms(brut, table)
                              if texte.est_a_traduire(n) and not _FACTICE.match(n)))


def longueur(fr: str) -> int:
    """Place prise dans une case, en octets (sans le zéro final)."""
    return len(texte.encoder_texte(texte.adapter(fr)))


def ecrire_noms(brut: bytes, traductions: dict[str, str], table: TableFixe = OBJETS) -> bytes:
    """La table avec chaque nom anglais de ``traductions`` remplacé dans toutes ses cases."""
    nouveau = bytearray(brut)
    for p, nom in zip(_positions(brut, table), lire_noms(brut, table)):
        fr = traductions.get(nom)
        if not fr:
            continue
        code = texte.encoder_texte(texte.adapter(fr))
        if len(code) > table.max:
            raise ErreurNom(f"{table.trad} « {fr} » : {len(code)} octets, la case en tient {table.max}")
        nouveau[p:p + table.place] = code.ljust(table.place, b"\0")
    return bytes(nouveau)
