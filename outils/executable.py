"""Textes de l'exécutable : les boîtes système (sauvegarde, carte SD, StreetPass, nom).

    code du jeu (ExeFS .code, décompressé) → trad/systeme/executable.json → code.ips

113 messages vus par le joueur vivent dans le segment .data du code, collés
les uns aux autres de 0x48BE14 à 0x48DCB5, sans un octet libre. Juste
après, à 0x48DCB8, une table de 113 entrées de 8 octets les désigne :
pointeur absolu (le code est chargé à 0x100000), puis deux u16 (type de
boîte, choix par défaut) qu'on ne touche pas. Chaque message a la forme
d'une page de script : f2 05 ff ff f1 41, le texte, 0a, un zéro
(texte.decouper_page).

Pour traduire, tout le bloc est réécrit à la suite et la table pointe sur
les nouvelles places. Si le français déborde, la suite part dans les marges
libres des segments rodata puis text (fins de page jamais utilisées). Rien
d'autre ne bouge. Le résultat est un patch IPS du code décompressé : Azahar
le lit dans load/mods/<title ID>/code.ips, Luma3DS dans
/luma/titles/<title ID>/code.ips.

Relevé sur la version européenne le 21/11/2026.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass

import texte

TRAD = "systeme/executable.json"
BASE = 0x100000
_ENTREE = 8


@dataclass(frozen=True)
class Disposition:
    bloc: tuple[int, int]                   # messages collés, [début, fin)
    table: int                              # table des pointeurs
    nombre: int                             # entrées de la table
    marges: tuple[tuple[int, int], ...]     # zones libres où déborder, dans l'ordre
    taille: int                             # taille du code décompressé


EU = Disposition(bloc=(0x48BE14, 0x48DCB5), table=0x48DCB8, nombre=113,
                 marges=((0x450DF8, 0x451000), (0x405880, 0x406000)), taille=0x4DB000)


class ErreurExecutable(ValueError):
    pass


@dataclass
class Message:
    index: int          # numéro dans la table
    position: int       # dans le code
    octets: bytes       # sans le zéro final

    @property
    def ident(self) -> str:
        return f"{self.index:03d}"


def lire_messages(code: bytes, d: Disposition | None = None) -> list[Message]:
    """Les messages, dans l'ordre du bloc ; refuse un code d'une autre version."""
    def refus(raison: str) -> ErreurExecutable:
        return ErreurExecutable(f"exécutable inattendu ({raison}) : une autre version du jeu ?")

    d = d or EU
    if len(code) != d.taille:
        raise refus(f"{len(code)} octets au lieu de {d.taille}")
    messages = []
    for k in range(d.nombre):
        (pointeur,) = struct.unpack_from("<I", code, d.table + _ENTREE * k)
        position = pointeur - BASE
        if not d.bloc[0] <= position < d.bloc[1]:
            raise refus(f"l'entrée {k} pointe hors du bloc")
        fin = code.index(b"\0", position)
        messages.append(Message(k, position, code[position:fin]))
    messages.sort(key=lambda m: m.position)
    attendu = d.bloc[0]
    for m in messages:
        if m.position != attendu:
            raise refus(f"messages non contigus à 0x{m.position:X}")
        attendu = m.position + len(m.octets) + 1
    if attendu != d.bloc[1]:
        raise refus("le bloc ne finit pas où prévu")
    if any(any(code[a:b]) for a, b in d.marges):
        raise refus("les marges ne sont pas libres")
    return messages


def entrees(code: bytes, d: Disposition | None = None) -> list[dict]:
    """Entrées de trad/systeme/executable.json, dans l'ordre de la table."""
    sortie = []
    for m in sorted(lire_messages(code, d), key=lambda m: m.index):
        lisible = texte.decouper_page(m.octets)[1]
        if texte.est_a_traduire(lisible):
            sortie.append({"id": m.ident, "en": lisible})
    return sortie


def traduire(code: bytes, traductions: dict[str, str], d: Disposition | None = None) -> bytes:
    """Le code avec les messages traduits (id → français), bloc réécrit et table à jour."""
    d = d or EU
    messages = lire_messages(code, d)
    nouveaux = []
    for m in messages:
        fr = traductions.get(m.ident)
        if fr:
            prefixe, _, suffixe = texte.decouper_page(m.octets)
            nouveaux.append((m, prefixe + texte.encoder_texte(texte.adapter(fr)) + suffixe))
        else:
            nouveaux.append((m, m.octets))
    sortie = bytearray(code)
    zones = [d.bloc, *d.marges]
    for a, b in zones:
        sortie[a:b] = bytes(b - a)
    z, curseur = 0, zones[0][0]
    for m, octets in nouveaux:
        besoin = len(octets) + 1
        while curseur + besoin > zones[z][1]:
            z += 1
            if z == len(zones):
                total = sum(len(o) + 1 for _, o in nouveaux)
                place = sum(b - a for a, b in zones)
                raise ErreurExecutable(f"{TRAD} : {total - place} octets de trop "
                                       f"({total} pour {place} disponibles) ; raccourcir des messages")
            curseur = zones[z][0]
        sortie[curseur:curseur + len(octets)] = octets
        struct.pack_into("<I", sortie, d.table + _ENTREE * m.index, BASE + curseur)
        curseur += besoin
    return bytes(sortie)


def ips(avant: bytes, apres: bytes) -> bytes:
    """Patch IPS qui fait passer de ``avant`` à ``apres`` (même taille)."""
    if len(avant) != len(apres):
        raise ValueError("un patch IPS ne change pas la taille du code ici")
    sortie = bytearray(b"PATCH")
    k, n = 0, len(avant)
    while k < n:
        if avant[k] == apres[k]:
            k += 1
            continue
        debut = k
        # On fusionne les écarts séparés de moins de 8 octets identiques.
        fin, egaux = k, 0
        while fin < n and fin - debut < 0xFFFF and egaux < 8:
            egaux = egaux + 1 if avant[fin] == apres[fin] else 0
            fin += 1
        fin -= egaux
        if debut == 0x454F46:               # « EOF » : on commence un octet plus tôt
            debut -= 1
        sortie += debut.to_bytes(3, "big") + (fin - debut).to_bytes(2, "big") + apres[debut:fin]
        k = fin
    return bytes(sortie + b"EOF")


def appliquer_ips(code: bytes, patch: bytes) -> bytes:
    """Applique un patch IPS (pour les tests et l'aller-retour)."""
    if patch[:5] != b"PATCH" or patch[-3:] != b"EOF":
        raise ValueError("patch IPS invalide")
    sortie = bytearray(code)
    k = 5
    while k < len(patch) - 3:
        debut = int.from_bytes(patch[k:k + 3], "big")
        taille = int.from_bytes(patch[k + 3:k + 5], "big")
        k += 5
        if taille == 0:                     # répétition d'un octet (RLE)
            n = int.from_bytes(patch[k:k + 2], "big")
            sortie[debut:debut + n] = patch[k + 2:k + 3] * n
            k += 3
        else:
            sortie[debut:debut + taille] = patch[k:k + taille]
            k += taille
    return bytes(sortie)
