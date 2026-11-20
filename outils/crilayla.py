"""Compression CRILAYLA (CRI Middleware), utilisée par les fichiers du CPK.

Un bloc CRILAYLA se présente ainsi :

    +0x00  "CRILAYLA"
    +0x08  u32 LE  taille décompressée de la partie compressée
    +0x0C  u32 LE  taille du flux compressé (l'en-tête brut le suit)
    +0x10  flux compressé
    ...    0x100 octets bruts : le début du fichier, jamais compressé

Le flux se lit **à rebours**, depuis son dernier octet, bit de poids fort
d'abord, et le résultat s'écrit lui aussi de la fin vers le début. Un bit 0
annonce un octet littéral sur 8 bits ; un bit 1, une référence arrière :
distance sur 13 bits (+3), longueur 3 + paliers de 2, 3, 5 puis 8 bits,
prolongée d'octets de 8 bits tant qu'ils valent 255.

On n'a besoin que de décompresser : le build réécrit les fichiers modifiés
sans compression, ce que le CPK accepte. ``compresser_litteral`` existe pour
les tests, qui doivent fabriquer des blocs sans donnée du jeu.
"""

from __future__ import annotations

import struct

SIGNATURE = b"CRILAYLA"
TAILLE_ENTETE_BRUT = 0x100
_PALIERS = (2, 3, 5, 8)


def decompresser(donnees: bytes) -> bytes:
    """Rend le fichier d'origine : 0x100 octets bruts, puis la partie décompressée."""
    if donnees[:8] != SIGNATURE:
        raise ValueError("bloc sans signature CRILAYLA")
    taille, pos_brut = struct.unpack_from("<II", donnees, 8)
    sortie = bytearray(TAILLE_ENTETE_BRUT + taille)
    sortie[:TAILLE_ENTETE_BRUT] = donnees[0x10 + pos_brut:0x10 + pos_brut + TAILLE_ENTETE_BRUT]

    lecture = len(donnees) - TAILLE_ENTETE_BRUT - 1
    reserve = 0
    restants = 0

    def bits(n: int) -> int:
        nonlocal lecture, reserve, restants
        valeur = 0
        produits = 0
        while produits < n:
            if restants == 0:
                reserve = donnees[lecture]
                restants = 8
                lecture -= 1
            pris = min(restants, n - produits)
            valeur = (valeur << pris) | ((reserve >> (restants - pris)) & ((1 << pris) - 1))
            restants -= pris
            produits += pris
        return valeur

    fin = TAILLE_ENTETE_BRUT + taille - 1
    ecrits = 0
    while ecrits < taille:
        if bits(1):
            source = fin - ecrits + bits(13) + 3
            longueur = 3
            for palier in _PALIERS:
                v = bits(palier)
                longueur += v
                if v != (1 << palier) - 1:
                    break
            else:
                while True:
                    v = bits(8)
                    longueur += v
                    if v != 255:
                        break
            for _ in range(longueur):
                sortie[fin - ecrits] = sortie[source]
                source -= 1
                ecrits += 1
        else:
            sortie[fin - ecrits] = bits(8)
            ecrits += 1
    return bytes(sortie)


def compresser_litteral(donnees: bytes) -> bytes:
    """Bloc CRILAYLA valide, sans aucune référence arrière (pour les tests)."""
    if len(donnees) < TAILLE_ENTETE_BRUT:
        raise ValueError(f"il faut au moins {TAILLE_ENTETE_BRUT} octets")
    corps = donnees[TAILLE_ENTETE_BRUT:]
    # Le décompresseur produit le dernier octet en premier.
    flux_bits = "".join("0" + format(o, "08b") for o in reversed(corps))
    flux_bits += "0" * (-len(flux_bits) % 8)
    octets = bytes(int(flux_bits[i:i + 8], 2) for i in range(0, len(flux_bits), 8))
    flux = octets[::-1]          # lu à rebours : le premier octet consommé est le dernier
    return (SIGNATURE + struct.pack("<II", len(corps), len(flux)) + flux
            + donnees[:TAILLE_ENTETE_BRUT])
