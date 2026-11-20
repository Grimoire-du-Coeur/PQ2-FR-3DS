"""Le texte d'une page de message, tel que le traducteur le voit.

Dans le jeu, une page mêle du texte (ASCII et Shift-JIS) et des codes de
fonction : un octet 0xF0 + (nombre d'arguments + 1), un octet
« table << 5 | numéro », puis deux octets par argument. Presque toutes les
pages commencent par les mêmes codes (affichage, portrait, voix) et finissent
par d'autres (attente, fin de page, octet 0).

Ces débuts et ces fins sont **cachés** au traducteur : ``decouper_page`` les
met de côté, et le build les reprend de la page d'origine. Il ne reste dans
le texte lisible que ce qui se traduit, plus quelques balises :

    {SAUT}            retour à la ligne (octet 0x0A)
    {f T I a b ...}   tout autre code, en notation d'Atlus Script Tools :
                      table, numéro, puis les arguments en décimal
    {0xHH}            un octet isolé qui n'est ni du texte ni un code

Les séparateurs ``{PAGE}`` et ``{OPTION}`` relient les pages d'un message
dans trad/ ; ils n'existent pas à l'intérieur d'une page.
"""

from __future__ import annotations

import re

SAUT = "{SAUT}"
PAGE = "{PAGE}"
OPTION = "{OPTION}"

_ESPACE_JAPONAISE = b"\x81\x40"
_BALISE = re.compile(r"\{([^{}]*)\}")


class ErreurTexte(ValueError):
    """Texte impossible à écrire dans le jeu ; le message dit pourquoi."""


def _est_premier_octet_sjis(b: int) -> bool:
    return 0x81 <= b <= 0x9F or 0xE0 <= b <= 0xEF


def _jetons(octets: bytes) -> list[tuple[str, bytes]]:
    """Découpe en jetons : code (F), saut (N), caractère (C), octet isolé (X)."""
    jetons = []
    i = 0
    while i < len(octets):
        b = octets[i]
        if b >= 0xF0:
            n = 2 + 2 * ((b & 0x0F) - 1)
            jetons.append(("F", octets[i:i + n]))
            i += n
        elif _est_premier_octet_sjis(b) and i + 1 < len(octets):
            jetons.append(("C", octets[i:i + 2]))
            i += 2
        elif b == 0x0A:
            jetons.append(("N", octets[i:i + 1]))
            i += 1
        elif 0x20 <= b <= 0x7E and b not in (0x7B, 0x7D):
            jetons.append(("C", octets[i:i + 1]))
            i += 1
        else:
            jetons.append(("X", octets[i:i + 1]))
            i += 1
    return jetons


def _technique(jeton: tuple[str, bytes], en_fin: bool) -> bool:
    """Jeton qui peut appartenir au début (ou à la fin) caché d'une page."""
    sorte, brut = jeton
    if sorte in ("F", "N") or brut == _ESPACE_JAPONAISE:
        return True
    return en_fin and brut == b"\0"


def decouper_page(page: bytes) -> tuple[bytes, str, bytes]:
    """(préfixe caché, texte lisible, suffixe caché)."""
    jetons = _jetons(page)
    debut = 0
    while debut < len(jetons) and _technique(jetons[debut], en_fin=False):
        debut += 1
    fin = len(jetons)
    while fin > debut and _technique(jetons[fin - 1], en_fin=True):
        fin -= 1
    prefixe = b"".join(b for _, b in jetons[:debut])
    milieu = b"".join(b for _, b in jetons[debut:fin])
    suffixe = b"".join(b for _, b in jetons[fin:])
    return prefixe, decoder_texte(milieu), suffixe


def _code_vers_balise(code: bytes) -> str:
    table, numero = code[1] >> 5, code[1] & 0x1F
    args = [((code[k] - 1) & 0xFF) | (((code[k + 1] - 1) & 0xFF) << 8)
            for k in range(2, len(code), 2)]
    return "{f " + " ".join(str(v) for v in (table, numero, *args)) + "}"


def decoder_texte(octets: bytes) -> str:
    morceaux = []
    for sorte, brut in _jetons(octets):
        if sorte == "F":
            morceaux.append(_code_vers_balise(brut))
        elif sorte == "N":
            morceaux.append(SAUT)
        elif sorte == "C":
            morceaux.append(brut.decode("cp932"))
        else:
            morceaux.append(f"{{0x{brut[0]:02X}}}")
    return "".join(morceaux)


def _balise_vers_octets(contenu: str) -> bytes:
    if contenu == "SAUT":
        return b"\n"
    if re.fullmatch(r"0x[0-9A-Fa-f]{2}", contenu):
        return bytes([int(contenu, 16)])
    parties = contenu.split()
    if len(parties) >= 3 and parties[0] == "f" and all(p.isdigit() for p in parties[1:]):
        table, numero, *args = (int(p) for p in parties[1:])
        if table > 7 or numero > 31 or len(args) > 14 or any(a > 0xFFFF for a in args):
            raise ErreurTexte(f"balise de code hors limites : {{{contenu}}}")
        code = bytearray([0xF0 + len(args) + 1, table << 5 | numero])
        for a in args:
            code += bytes([((a & 0xFF) + 1) & 0xFF, ((a >> 8) + 1) & 0xFF])
        return bytes(code)
    if contenu in ("PAGE", "OPTION"):
        raise ErreurTexte(f"{{{contenu}}} sépare les pages d'un message, pas le texte d'une page")
    raise ErreurTexte(f"balise inconnue : {{{contenu}}}")


def encoder_texte(lisible: str) -> bytes:
    sortie = bytearray()
    pos = 0
    for m in _BALISE.finditer(lisible):
        sortie += _encoder_caracteres(lisible[pos:m.start()])
        sortie += _balise_vers_octets(m.group(1))
        pos = m.end()
    sortie += _encoder_caracteres(lisible[pos:])
    return bytes(sortie)


def _encoder_caracteres(morceau: str) -> bytes:
    sortie = bytearray()
    for ch in morceau:
        if ch in "{}":
            raise ErreurTexte(f"accolade isolée « {ch} » : une balise s'écrit {{SAUT}}, {{f …}}")
        if " " <= ch <= "~":
            sortie.append(ord(ch))
            continue
        try:
            code = ch.encode("cp932")
        except UnicodeEncodeError:
            code = b""
        if len(code) != 2 or not _est_premier_octet_sjis(code[0]):
            raise ErreurTexte(f"caractère « {ch} » absent de la police du jeu")
        sortie += code
    return bytes(sortie)


def est_a_traduire(lisible: str) -> bool:
    """Vrai si le texte contient un vrai mot latin (pas un numéro 0x…)."""
    nu = _BALISE.sub(" ", lisible)
    nu = re.sub(r"0x[0-9A-Fa-f]+", " ", nu)
    return re.search(r"[A-Za-z]{2,}", nu) is not None
