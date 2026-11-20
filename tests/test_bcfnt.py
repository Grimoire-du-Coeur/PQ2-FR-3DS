"""Métriques des polices CFNT, et largeur des lignes."""

import bcfnt
import mesurer
from fabrique import fabriquer_bcfnt

POLICE = fabriquer_bcfnt({
    0x20: (0, 4, 4),          # espace ASCII
    0x41: (1, 9, 12),         # « A » ASCII : case de remplacement, pas la vraie largeur
    0x8260: (0, 8, 8),        # Ａ pleine largeur : la vraie lettre
    0x8281: (0, 7, 7),        # ａ
    0x8285: (1, 6, 7),        # ｅ
    0x8289: (-1, 5, 3),       # ｉ
    0x8163: (1, 10, 12),      # …
    0x81A7: (3, 6, 12),       # é (case de symbole redessinée)
})


def test_lire_metriques():
    m = bcfnt.lire_metriques(POLICE)
    assert m[0x8281] == (0, 7, 7)
    assert m[0x8289] == (-1, 5, 3)
    assert len(m) == 8


def test_largeurs_des_caracteres():
    l = mesurer.largeurs_caracteres(bcfnt.lire_metriques(POLICE))
    assert l["A"] == 8            # prise sur Ａ, pas sur la case ASCII
    assert l["a"] == 7 and l["i"] == 3 and l[" "] == 4
    assert l["é"] == 7            # comme « e »
    assert l["…"] == 12


def test_largeur_ligne():
    l = {"a": 7, "i": 3, " ": 4}
    assert mesurer.largeur_ligne("ai a", l) == 7 + 3 + 4 + 7
    assert mesurer.largeur_ligne("a{f 0 1 2}a{f 0 1 0}", l) == 14     # les balises ne comptent pas
    assert mesurer.largeur_ligne("z", l) == mesurer.LARGEUR_INCONNUE
