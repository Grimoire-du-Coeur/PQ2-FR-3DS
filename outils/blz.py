"""Décompression « BLZ » : le LZ à rebours du code des jeux 3DS (ExeFS .code).

Le fichier se lit de la fin vers le début. Ses 8 derniers octets disent où
commence la partie compressée et de combien le fichier grossit :

    u32 haut_bas   octets 0-23 : taille de la partie compressée (pied compris)
                   octets 24-31 : taille du pied, à sauter
    u32 en_plus    taille décompressée - taille compressée

Puis, en remontant : un octet de contrôle pour huit éléments, bit fort
d'abord ; 0 = un octet copié tel quel ; 1 = une référence sur deux octets
(longueur sur 4 bits + 3, distance sur 12 bits + 3) vers ce qui vient d'être
écrit, plus loin dans le fichier. Le début du fichier n'est pas compressé.

Même algorithme que ctrtool (lzss_decompress) ; seul le sens « décompresser »
sert ici : Azahar et Luma3DS appliquent code.ips au code décompressé.
"""

from __future__ import annotations

import struct


class ErreurBlz(ValueError):
    pass


def decompresser(donnees: bytes) -> bytes:
    if len(donnees) < 8:
        raise ErreurBlz("code compressé trop court")
    haut_bas, en_plus = struct.unpack_from("<II", donnees, len(donnees) - 8)
    taille = len(donnees) + en_plus
    lecture = len(donnees) - (haut_bas >> 24)
    arret = len(donnees) - (haut_bas & 0xFFFFFF)
    if not 0 <= arret <= lecture <= len(donnees):
        raise ErreurBlz("pied de compression incohérent")
    sortie = bytearray(taille)
    sortie[:len(donnees)] = donnees
    ecriture = taille
    while lecture > arret:
        lecture -= 1
        controle = donnees[lecture]
        for _ in range(8):
            if lecture <= arret:
                break
            if controle & 0x80:
                if lecture < 2:
                    raise ErreurBlz("référence hors du fichier")
                lecture -= 2
                valeur = donnees[lecture] | donnees[lecture + 1] << 8
                longueur = (valeur >> 12) + 3
                distance = (valeur & 0x0FFF) + 2
                if ecriture < longueur or ecriture + distance + 1 > taille:
                    raise ErreurBlz("référence hors du fichier")
                for _ in range(longueur):
                    octet = sortie[ecriture + distance]
                    ecriture -= 1
                    sortie[ecriture] = octet
            else:
                if ecriture < 1:
                    raise ErreurBlz("code décompressé trop long")
                lecture -= 1
                ecriture -= 1
                sortie[ecriture] = donnees[lecture]
            controle = (controle << 1) & 0xFF
    return bytes(sortie)
