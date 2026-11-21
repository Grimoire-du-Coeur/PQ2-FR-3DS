"""Fabrique de données de test, sans aucun octet du jeu.

Les tests ont besoin de CPK, d'images 3DS, de scripts MSG1 et FLW0. Ce module
les écrit de toutes pièces, en suivant les dispositions relevées sur le jeu :
assez fidèles pour exercer les outils, assez petites pour tenir dans un test.
"""

from __future__ import annotations

import struct

import crilayla

# ---------------------------------------------------------------- tables @UTF

_TAILLES = {0: 1, 1: 1, 2: 2, 3: 2, 4: 4, 5: 4, 6: 8, 7: 8, 8: 4, 9: 8, 0xA: 4, 0xB: 8}
_FORMATS = {0: ">B", 1: ">b", 2: ">H", 3: ">h", 4: ">I", 5: ">i", 6: ">Q", 7: ">q",
            8: ">f", 9: ">d"}


def ecrire_utf(nom: str, colonnes: list[tuple[str, int, object]], lignes: list[dict]) -> bytes:
    """Table @UTF : ``colonnes`` = (nom, drapeau stockage|type, constante ou None)."""
    chaines = bytearray(b"<NULL>\0")
    index: dict[str, int] = {}

    def chaine(s: str) -> int:
        if s not in index:
            index[s] = len(chaines)
            chaines.extend(s.encode("utf-8") + b"\0")
        return index[s]

    def valeur(t: int, v) -> bytes:
        if t == 0xA:
            return struct.pack(">I", chaine(v))
        return struct.pack(_FORMATS[t], v)

    nom_table = chaine(nom)
    schema = bytearray()
    taille_ligne = 0
    for nom_col, drapeau, constante in colonnes:
        schema += struct.pack(">BI", drapeau, chaine(nom_col))
        if drapeau & 0xF0 == 0x30:
            schema += valeur(drapeau & 0x0F, constante)
        elif drapeau & 0xF0 == 0x50:
            taille_ligne += _TAILLES[drapeau & 0x0F]
    corps_lignes = bytearray()
    for ligne in lignes:
        for nom_col, drapeau, _ in colonnes:
            if drapeau & 0xF0 == 0x50:
                corps_lignes += valeur(drapeau & 0x0F, ligne[nom_col])

    pos_lignes = 0x18 + len(schema)
    pos_chaines = pos_lignes + len(corps_lignes)
    pos_donnees = pos_chaines + len(chaines)
    entete = struct.pack(">HHIIIHHI", 1, pos_lignes, pos_chaines, pos_donnees, nom_table,
                         len(colonnes), taille_ligne, len(lignes))
    corps = entete + schema + corps_lignes + chaines
    return b"@UTF" + struct.pack(">I", len(corps)) + corps


def _paquet(signature: bytes, table: bytes) -> bytes:
    return signature + b"\xff\0\0\0" + struct.pack("<Q", len(table)) + table


def _aligner(n: int, a: int = 2048) -> int:
    return (n + a - 1) // a * a


# ---------------------------------------------------------------- CPK

def fabriquer_cpk(fichiers: dict[str, bytes], compresses: set[str] = frozenset()) -> bytes:
    """CPK minimal : en-tête, TOC à 2 048, fichiers alignés sur 2 048."""
    chemins = sorted(fichiers)
    stockes = {c: crilayla.compresser_litteral(fichiers[c]) if c in compresses else fichiers[c]
               for c in chemins}
    toc_pos = 2048

    def toc(decalages: dict[str, int]) -> bytes:
        lignes = []
        for i, c in enumerate(chemins):
            dossier, _, nom = c.rpartition("/")
            lignes.append({"DirName": dossier, "FileName": nom, "FileSize": len(stockes[c]),
                           "ExtractSize": len(fichiers[c]), "FileOffset": decalages.get(c, 0),
                           "ID": i})
        return _paquet(b"TOC ", ecrire_utf("CpkTocInfo", [
            ("DirName", 0x5A, None), ("FileName", 0x5A, None), ("FileSize", 0x54, None),
            ("ExtractSize", 0x54, None), ("FileOffset", 0x56, None), ("ID", 0x54, None),
            ("UserString", 0x3A, "<NULL>")], lignes))

    taille_toc = len(toc({}))
    contenu_pos = _aligner(toc_pos + taille_toc)
    decalages, pos = {}, contenu_pos
    for c in chemins:
        decalages[c] = pos - toc_pos          # relatif à TocOffset, comme dans le jeu
        pos = _aligner(pos + len(stockes[c]))
    paquet_toc = toc(decalages)

    entete = _paquet(b"CPK ", ecrire_utf("CpkHeader", [
        ("ContentOffset", 0x56, None), ("ContentSize", 0x56, None), ("TocOffset", 0x56, None),
        ("TocSize", 0x56, None), ("Files", 0x54, None), ("Align", 0x52, None)],
        [{"ContentOffset": contenu_pos, "ContentSize": pos - contenu_pos, "TocOffset": toc_pos,
          "TocSize": len(paquet_toc), "Files": len(chemins), "Align": 2048}]))
    sortie = bytearray(pos)
    sortie[:len(entete)] = entete
    sortie[toc_pos:toc_pos + len(paquet_toc)] = paquet_toc
    for c in chemins:
        debut = toc_pos + decalages[c]
        sortie[debut:debut + len(stockes[c])] = stockes[c]
    return bytes(sortie)


# ---------------------------------------------------------------- MSG1

def _a4(n: int) -> int:
    return (n + 3) // 4 * 4


def fabriquer_msg1(table_relocation: bytes | None = None) -> bytes:
    """Script de messages écrit à la main, selon la disposition relevée sur le jeu.

    Deux messages : « dlg_a » (locuteur 0, deux pages) et « sel_b » (un choix à
    trois options), et un locuteur « Yosuke ». Chaque message commence sur un
    multiple de 4, les noms de locuteurs suivent leurs pointeurs, la table de
    relocation ferme le fichier.
    """
    B = 0x20
    pages_a = [b"\xf1\x41Hello there!\n", b"\xf2\x05\xff\xffBye.\x00"]
    options_b = [b"Yes\x00", b"No\x00", b"Maybe\x00"]

    corps = bytearray()
    positions = []                      # emplacements des pointeurs, relatifs à B
    table = bytearray()
    pos = 2 * 8 + 16                    # après la table des messages et l'en-tête des locuteurs

    def message(type_, tete: bytes, morceaux: list[bytes]) -> None:
        nonlocal pos
        pos = _a4(pos)
        corps.extend(bytes(pos - (2 * 8 + 16) - len(corps)))
        positions.append(len(table) + 4)
        table.extend(struct.pack("<II", type_, pos))
        debut_ptr = pos + len(tete)
        texte_pos = debut_ptr + 4 * len(morceaux) + 4
        ptrs, o = b"", texte_pos
        for m in morceaux:
            positions.append(debut_ptr + len(ptrs))
            ptrs += struct.pack("<I", o)
            o += len(m)
        texte = b"".join(morceaux)
        bloc = tete + ptrs + struct.pack("<I", len(texte)) + texte
        corps.extend(bloc)
        pos += len(bloc)

    message(0, b"dlg_a".ljust(24, b"\0") + struct.pack("<HH", 2, 0), pages_a)
    message(1, b"sel_b".ljust(24, b"\0") + struct.pack("<HHHH", 0, 3, 0, 0), options_b)

    pos = _a4(pos)
    corps.extend(bytes(pos - (2 * 8 + 16) - len(corps)))
    loc_ptrs = pos
    positions.append(loc_ptrs)
    nom_pos = loc_ptrs + 4
    corps.extend(struct.pack("<I", nom_pos) + b"Yosuke\0")
    pos = nom_pos + 7

    entete_loc = struct.pack("<IIII", loc_ptrs, 1, 0, 0)
    positions.append(2 * 8)             # pointeur de l'en-tête des locuteurs
    positions.sort()
    if table_relocation is None:
        import msg1
        table_relocation = msg1.encoder_relocation(positions)

    reloc_pos = B + _a4(pos)
    contenu = bytes(table) + entete_loc + bytes(corps)
    contenu += bytes(reloc_pos - B - len(contenu))
    total = reloc_pos + len(table_relocation)
    entete = struct.pack("<BBHI4sIIIIHH", 7, 0, 0, total, b"MSG1", 0, reloc_pos,
                         len(table_relocation), 2, 0, 2)
    return entete + contenu + table_relocation


# ---------------------------------------------------------------- FLW0

def fabriquer_bf(messages: bytes | None, queue: bytes = b"") -> bytes:
    """Script FLW0 à cinq sections contiguës (procédures, étiquettes, code,
    messages, chaînes), comme les 1 632 .bf du jeu. ``queue`` imite les octets
    que certains fichiers portent après la dernière section."""
    procedures = b"proc_main".ljust(32, b"\0") + struct.pack("<I", 0).ljust(24, b"\0")
    code = struct.pack("<4I", 1, 2, 3, 4)
    chaines = b"bonjour\0"
    sections = [(0, 56, 1, procedures), (1, 56, 0, b""), (2, 4, 4, code),
                (3, 1, len(messages or b""), messages or b""), (4, 1, len(chaines), chaines)]
    pos = 0x20 + 16 * len(sections)
    tetes, corps = b"", b""
    debut_chaines = 0
    for type_, taille, nombre, contenu in sections:
        if type_ == 4:
            debut_chaines = pos
        tetes += struct.pack("<IIII", type_, taille, nombre, pos)
        corps += contenu
        pos += len(contenu)
    entete = struct.pack("<BBHI4sIIHHHHI", 0, 0, 0, debut_chaines, b"FLW0", 0, len(sections),
                         2, 0, 0, 0, 0)
    return entete + tetes + corps + queue


# ---------------------------------------------------------------- BCFNT

def fabriquer_bcfnt(largeurs: dict[int, tuple[int, int, int]]) -> bytes:
    """Police CFNT réduite à ses métriques : FINF, une table CWDH, une table CMAP
    « scan » (code Shift-JIS → n° de glyphe). Pas de planches de glyphes."""
    codes = sorted(largeurs)
    entete_taille = 0x14
    finf_pos = entete_taille
    cwdh_pos = finf_pos + 0x20
    cwdh = b"CWDH" + struct.pack("<IHHI", 0x10 + 3 * len(codes), 0, len(codes) - 1, 0)
    for c in codes:
        cwdh += struct.pack("<bBB", *largeurs[c])
    cwdh += bytes(-len(cwdh) % 4)
    cmap_pos = cwdh_pos + len(cwdh)
    cmap = b"CMAP" + struct.pack("<IHHHHI", 0, 0, 0xFFFF, 2, 0, 0) + struct.pack("<H", len(codes))
    for i, c in enumerate(codes):
        cmap += struct.pack("<HH", c, i)
    cmap = cmap[:4] + struct.pack("<I", len(cmap)) + cmap[8:]
    finf = b"FINF" + struct.pack("<IBBHbBBBIIIBBBB", 0x20, 1, 14, 0, 0, 13, 13, 2,
                                 0, cwdh_pos + 8, cmap_pos + 8, 14, 13, 11, 0)
    corps = finf + cwdh + cmap
    return b"CFNT" + struct.pack("<HHIII", 0xFEFF, entete_taille, 0x03000000,
                                 entete_taille + len(corps), 3) + corps


# ---------------------------------------------------------------- image 3DS

MU = 0x200   # « media unit » : les tailles NCSD/NCCH se comptent en blocs de 0x200


def _romfs(nom: str, contenu: bytes) -> bytes:
    """RomFS minimal : en-tête IVFC, puis niveau 3 avec un seul fichier à la racine."""
    nom_utf16 = nom.encode("utf-16-le")
    nom_utf16 += b"\0" * (-len(nom_utf16) % 4)
    meta_dossier = struct.pack("<6I", 0, 0xFFFFFFFF, 0xFFFFFFFF, 0, 0xFFFFFFFF, 0)
    meta_fichier = struct.pack("<IIQQII", 0, 0xFFFFFFFF, 0, len(contenu), 0xFFFFFFFF,
                               len(nom.encode("utf-16-le"))) + nom_utf16
    hachage = struct.pack("<I", 0)
    pos = 0x28
    zones = []
    for bloc in (hachage, meta_dossier, hachage, meta_fichier):
        zones.append((pos, len(bloc)))
        pos += len(bloc)
    donnees_pos = (pos + 15) // 16 * 16
    niveau3 = struct.pack("<10I", 0x28, *[v for z in zones for v in z], donnees_pos)
    niveau3 += hachage + meta_dossier + hachage + meta_fichier
    niveau3 += bytes(donnees_pos - len(niveau3)) + contenu

    taille_maitre = 0x20
    bloc_log2 = 12
    ivfc = b"IVFC" + struct.pack("<II", 0x10000, taille_maitre)
    for i in range(3):
        ivfc += struct.pack("<QQII", 0, len(niveau3) if i == 2 else 0, bloc_log2, 0)
    ivfc += bytes(0x60 - len(ivfc)) + bytes(taille_maitre)
    debut3 = (len(ivfc) + (1 << bloc_log2) - 1) // (1 << bloc_log2) * (1 << bloc_log2)
    return ivfc + bytes(debut3 - len(ivfc)) + niveau3


def fabriquer_3ds(cpk: bytes, title_id: int = 0x00040000001D7600, chiffre: bool = False) -> bytes:
    """Image NCSD décryptée (ou marquée chiffrée) dont le RomFS contient ``data.cpk``."""
    romfs = _romfs("data.cpk", cpk)
    romfs += bytes(-len(romfs) % MU)
    ncch = bytearray(0x400)
    ncch[0x100:0x104] = b"NCCH"
    struct.pack_into("<Q", ncch, 0x118, title_id)
    ncch[0x150:0x15A] = b"CTR-P-AQ2P"
    ncch[0x18F] = 0 if chiffre else 0x04        # bit NoCrypto
    struct.pack_into("<II", ncch, 0x1B0, len(ncch) // MU, len(romfs) // MU)
    partition = bytes(ncch) + romfs
    struct.pack_into("<I", ncch, 0x104, len(partition) // MU)
    partition = bytes(ncch) + romfs

    debut = 0x4000
    ncsd = bytearray(debut)
    ncsd[0x100:0x104] = b"NCSD"
    struct.pack_into("<IQ", ncsd, 0x104, (debut + len(partition)) // MU, title_id)
    struct.pack_into("<II", ncsd, 0x120, debut // MU, len(partition) // MU)
    return bytes(ncsd) + partition


# ---------------------------------------------------------------- PAK (.arc)

def fabriquer_pak(fichiers: list[tuple[str, bytes]]) -> bytes:
    """Archive Atlus PAK : nombre u32, puis (nom sur 32 octets, taille u32, données)."""
    sortie = struct.pack("<I", len(fichiers))
    for nom, donnees in fichiers:
        sortie += nom.encode("ascii").ljust(32, b"\0") + struct.pack("<I", len(donnees)) + donnees
    return sortie


def fabriquer_table_noms(noms: list[str], debuts: bool = True) -> bytes:
    """Table de noms du combat (tables.py) : u16 nombre, u16 positions, noms."""
    codes = [n.encode("cp932") + b"\0" for n in noms]
    positions, p = [], 0
    for c in codes:
        positions.append(p if debuts else p + len(c))
        p += len(c)
    return struct.pack(f"<{len(noms) + 1}H", len(noms), *positions) + b"".join(codes)


def fabriquer_itemtbl(*noms: str) -> bytes:
    """init/itemtbl.bin : 0x065820 octets, puis 3 584 cases de 22 octets (noms.py)."""
    zone = b"".join(n.encode("ascii").ljust(22, b"\0") for n in noms)
    return bytes(0x065820) + zone.ljust(0xE00 * 22, b"\0")


def fabriquer_ctd(textes: list[str] | None = None, nombres: bytes | None = None) -> bytes:
    """Table .ctd : en-tête (taille, nombre, 8 zéros), cases, copie de l'en-tête.

    ``textes`` : une case de 64 octets par texte ; ``nombres`` : une table
    de données (cases de 8 octets).
    """
    if textes is not None:
        cases = b"".join(t.encode("cp932").ljust(64, b"\0") for t in textes)
        nombre = len(textes)
    else:
        cases = nombres or bytes(8)
        nombre = len(cases) // 8
    entete = struct.pack("<II", len(cases), nombre) + bytes(8)
    return entete + cases + entete
