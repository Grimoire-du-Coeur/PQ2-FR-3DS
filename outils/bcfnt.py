"""Métriques d'une police CFNT (.bcfnt) de la 3DS : quel code a quelle largeur.

On ne lit que deux tables :

- CMAP : code du caractère (ici Shift-JIS) → numéro de glyphe, en trois
  variantes (plage directe, table, liste de paires) ;
- CWDH : pour chaque glyphe, (marge gauche, largeur du dessin, avance).

Les dessins eux-mêmes (planches TGLP) ne servent pas : les accents français
existent déjà dans la police du jeu (voir police/caracteres.json).
"""

from __future__ import annotations

import struct


def lire_metriques(police: bytes) -> dict[int, tuple[int, int, int]]:
    """{code: (marge gauche, largeur du dessin, avance)} pour chaque code de la police."""
    if police[:4] != b"CFNT":
        raise ValueError("police CFNT attendue")
    (finf,) = struct.unpack_from("<H", police, 6)
    ptr_largeurs, ptr_codes = struct.unpack_from("<II", police, finf + 20)

    largeurs: dict[int, tuple[int, int, int]] = {}
    p = ptr_largeurs
    while p:
        debut, fin, suivant = struct.unpack_from("<HHI", police, p)
        for i in range(debut, fin + 1):
            largeurs[i] = struct.unpack_from("<bBB", police, p + 8 + 3 * (i - debut))
        p = suivant

    glyphes: dict[int, int] = {}
    p = ptr_codes
    while p:
        premier, dernier, methode, _, suivant = struct.unpack_from("<HHHHI", police, p)
        q = p + 12
        if methode == 0:                    # plage directe
            (decalage,) = struct.unpack_from("<H", police, q)
            for c in range(premier, dernier + 1):
                glyphes[c] = c - premier + decalage
        elif methode == 1:                  # table
            for k, c in enumerate(range(premier, dernier + 1)):
                (g,) = struct.unpack_from("<H", police, q + 2 * k)
                if g != 0xFFFF:
                    glyphes[c] = g
        else:                               # liste de paires
            (n,) = struct.unpack_from("<H", police, q)
            for k in range(n):
                c, g = struct.unpack_from("<HH", police, q + 2 + 4 * k)
                glyphes[c] = g
        p = suivant
    return {c: largeurs[g] for c, g in glyphes.items() if g in largeurs}
