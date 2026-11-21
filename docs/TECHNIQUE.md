# Notes techniques

Comment le texte sort du jeu, et comment il y retourne. Tout a été relevé
sur la version européenne (`CTR-P-AQ2P`, title ID `00040000001D7600`).

## La chaîne

```text
image .3ds décryptée
  └─ partition 0 (NCCH) ─ RomFS ─ data.cpk          outils/rom3ds.py
       └─ 8 923 fichiers, 7 816 compressés          outils/cpk.py, outils/crilayla.py
            ├─ .bmd  : scripts de messages MSG1      outils/msg1.py
            └─ .bf   : scripts FLW0, section 3 = MSG1 outils/flw0.py
                 └─ pages ↔ texte lisible            outils/texte.py
                      └─ trad/**.json                outils/extraire.py
```

Dans l'autre sens, `outils/injecter.py` reprend chaque page d'origine,
remplace son texte lisible par le français, réécrit le script, puis patche
`data.cpk`.

| Commande | Rôle |
|---|---|
| `python outils/extraire.py IMAGE` | crée ou met à jour `trad/` sans jamais perdre un `fr` (`a_revoir`, `_orphelins.json`) |
| `python outils/extraire.py IMAGE --verifier` | échoue si `trad/` n'est pas à jour |
| `python outils/injecter.py IMAGE [--azahar \| --sortie CHEMIN]` | produit le `data.cpk` français |
| `python outils/aller_retour.py IMAGE` | relit puis réécrit **tous** les scripts sans traduire : doit redonner les mêmes octets |
| `python outils/valider.py [fichiers]` | vérifie les traductions (aussi lancé par la CI) |
| `python outils/stats.py [--sortie DOSSIER]` | `SUIVI.md`, badges et carte d'avancement (publiés sur la branche `suivi` par la CI) |
| `python outils/memoire.py` | mémoire de traduction : entrées couvertes par propagation, répliques traduites de plusieurs façons |
| `python outils/mesurer.py IMAGE` | régénère `police/largeurs.json` |
| `python outils/importer.py IMAGE DOSSIER --table TABLE` | importe des fichiers traduits avec PersonaEditor |
| `python -m pytest tests` | tests, sur des données fabriquées (aucun fichier du jeu) |

`aller_retour.py` est le garde-fou de tout l'outillage : sur le jeu
complet, 1 776 scripts, 36 500 messages et 43 338 pages ressortent
identiques. Deux scripts (`btlEvent614.bf`, `e813_040.bf`) ont un message
déclaré deux fois et un ancien message devenu inaccessible : ils ressortent
« équivalents » (mêmes messages, sans les octets morts).

## Le CPK

Archive CRI : en-tête et TOC au format @UTF (gros-boutiste, colonnes typées,
lignes de taille fixe). Les fichiers sont pour la plupart compressés en
CRILAYLA (flux lu à rebours, 0x100 octets d'en-tête bruts).

On ne reconstruit pas l'archive : les fichiers modifiés sont **ajoutés à la
fin**, non compressés et alignés sur 2 048 octets, et leurs lignes de TOC
(`FileSize`, `ExtractSize`, `FileOffset`) sont réécrites sur place. Une copie
de l'en-tête et de la TOC d'origine est rangée tout au bout, suivie de la
signature `PQ2FR-ORIGINE` : le build suivant s'en sert pour repartir de
l'original au lieu d'empiler les ajouts.

## Les messages (MSG1)

En-tête de 0x20 octets ; table `(type, position)` ; en-tête des locuteurs ;
messages alignés sur 4 (nom sur 24 octets, nombre de pages, locuteur,
positions des pages, texte) ; noms des locuteurs ; table de relocation.
Toutes les positions sont relatives à 0x20.

Table de relocation, relevée sur les 144 `.bmd` du jeu : octet pair `b` →
pointeur suivant à `2b` ; octet impair avec `b & 7 == 7` → `(b >> 3) + 2`
pointeurs espacés de 4 ; autre octet impair → valeur 16 bits `v`, écart
`v - 1`.

Dans un `.bf` (FLW0), cinq sections contiguës : procédures, étiquettes,
code, messages, chaînes. Le code désigne les messages par leur numéro : on
peut changer la taille de la section 3 en décalant la 4 et le champ +0x04.

## Les archives PAK

Des scripts vivent aussi dans des archives Atlus « PAK » (`outils/pak.py` :
nombre d'entrées, puis nom sur 32 octets, taille et données, contigus).
L'extension ne dit rien : le jeu en a 1 021, en `.arc`, `.gsd`, `.bin`,
`.pac` et `.tpc` (`catalogue.CONTENEURS`). Celles qui portent des scripts à
traduire sont dans `catalogue.ARCHIVES` :

| Archives | Scripts | Contenu |
|---|---|---|
| 40 `.arc` sur 323 | 47, dont 40 copies de fichiers isolés | boutique, fusion, camp, donjons, ennemis |
| 93 `.gsd` sur 100 (`dungeon/script/`, `init/`, `quest/`) | un `.bf` chacun | remarques d'étage, missions, quêtes |
| `init/cmptable.bin` | 3 `.bmd` (89 messages) | menus du camp : Personas, statut, présentation |
| `title/nameentry.bin` | `nameentry.bmd` (12 messages) | saisie du nom |
| `init/gsobserver.bin` | une copie d'un fichier isolé | — |

Une copie identique d'un fichier isolé partage son JSON, et la réinjection
écrit la traduction aux deux endroits, quelle que soit la copie que le jeu
lit. Les autres ont leur propre JSON, sous le nom de l'archive
(`dungeon/script/dungeon01f.gsd/dungeon01f.bf` →
`donjons/script/dungeon01f/dungeon01f.json`). `aller_retour.py` balaie
toutes les archives et signale celle dont un script porte du texte latin
sans être dans la liste. Les scripts restés en japonais
(`battle/result/persona_get.bin`, `attraction/sch_walk.gsd`) n'y sont pas,
pas plus que les `.pac` et `.tpc` (portraits, modèles 3D, scènes).

## Les tables .ctd des menus du camp

`init/cmptable.bin` porte aussi 37 tables `.ctd` (`outils/ctd.py`). En-tête
de 16 octets (u32 taille des données, u32 nombre de cases, 8 zéros), les
cases, puis une copie de l'en-tête, parfois tronquée. 18 tables sont du
texte en cases de 64 octets (un texte terminé par un zéro, complété de
zéros) ; les autres sont des nombres. Seules les cases de texte sont
réécrites, à leur place : la table garde sa taille, un texte tient 63
octets. Trois tables figurent deux fois à l'identique (`cmpSkillHelp`…) :
les deux copies sont réécrites.

16 tables, 94 textes, dans `systeme/init/cmptable/<table>.json` (id = numéro
de case) : options, aides et libellés des menus du camp, catégories
d'objets, difficultés. Ne sont pas extraits : les restes japonais
(`cmpDifficultHelp`, « SAFTYのヘルプ ») et « Not used. (If this appears, it
is a bug. ». La description des difficultés affichée en début de partie
vient donc d'ailleurs : à localiser.

## Les noms à cases fixes : objets et lieux

`outils/noms.py`, une description `TableFixe` par fichier.

### Objets

`init/itemtbl.bin` (494 624 octets) finit par une table de 3 584 cases de
22 octets, de 0x065820 à la fin du fichier : une par numéro d'objet
(0x000-0xDFF), nom ASCII terminé par un zéro et complété de zéros
(`outils/noms.py`). Plages : armes (0x000), armures (0x300), accessoires
(0x400), consommables (0x500), objets clés (0x600), matériaux (0x700),
accessoires bis (0xA00), objets à expertiser (0xD00). Plus de la moitié des
cases sont des numéros génériques (« Weapon 0x1F4 »), des « Reserved »,
« (prov) … » ou des marqueurs (« Armor Start ») : ils ne sont pas extraits.
Restent 1 733 noms distincts ; un nom présent dans plusieurs cases est écrit
dans toutes. La table ne change pas de taille : 21 octets au plus par nom,
vérifiés par `valider.py` (champ `max`) et à l'injection.

Les menus et les boutiques lisent cette table ; les dialogues qui citent un
objet passent sans doute par un code d'insertion (`{f 2 4 …}`), à confirmer
en jeu. 98 de ces noms existent aussi dans
`battle/table/skillnametable.tbl` : ces compétences reprennent la
traduction de l'objet (voir plus bas).

Police : la police des menus n'est pas encore identifiée. Si c'est
`seurapro_13_13`, il lui manque é, É, œ… : à vérifier en jeu avec un
premier nom accentué.

### Lieux

`camp/dictionary.tbl` (9 120 octets) : 152 fiches de 60 octets, une par
apparition d'un ennemi. +4 : u16, numéro de l'ennemi ; +8 : nom du lieu
(« 1st Ave.~ », « Kamoshida Square ») ; +30 et +32 : drapeaux ; +36 : six
flottants. Le nom garde 20 octets, zéro final compris : les octets +28 et
+29 valent zéro dans toutes les fiches, la place réelle est peut-être de
22. 33 lieux distincts, dans `noms/lieux.json` (`max` 19).

## Les tables de noms du combat

`outils/tables.py`. Format commun : un u16, le nombre de noms ; autant de
positions u16 ; puis les noms à la suite, terminés par un zéro.
`skillnametable.tbl` donne la position du **début** de chaque nom, les
autres celle de sa **fin**. Les positions comptent depuis le premier nom :
la zone tient 65 535 octets, et un nom peut s'allonger sans rien déplacer
d'autre (la table est réécrite en entier).

| Table | Noms | Extraits | Fichier |
|---|---|---|---|
| `battle/table/skillnametable.tbl` | 1 501 | 778 | `noms/competences.json` |
| `battle/table/personanametable.tbl` | 401 | 310 | `noms/personas.json` |
| `battle/table/enemynametable.tbl` | 501 | 356 | `noms/ennemis.json` |

Ne sont pas extraits : les cases vides (`BLANK`, `blank`, `RESERVE SKILL`),
les restes japonais, les doublons, et les 98 compétences au nom d'objet,
qui prennent la traduction de `noms/objets.json` au build. Le même format
sert à une dizaine d'autres tables (`Item/*nametable.tbl`,
`quest/table/questnametable.tbl`, `battle/message/*.tbl`…), toutes en
japonais : le jeu européen ne les affiche pas.

## Le texte d'une page

Codes de fonction : `0xF0 + (arguments + 1)`, puis `table << 5 | numéro`,
puis deux octets par argument (valeur + 1). Notés `{f table numéro args…}`,
comme dans Atlus Script Tools.

Chaque page commence par des codes d'affichage (`f 0 5`, `f 2 1`), souvent le
portrait et la voix (`f 4 6`, `f 3 1`, `f 6 1`), et finit par l'attente
(`f 1 1`, `f 1 3`…) et un octet nul. Ces codes **structurels** (liste
`STRUCTURELS` dans `texte.py`) sont cachés au traducteur et repris de la
page d'origine. Les codes de **contenu** restent visibles : couleur
(`f 0 1`), nom ou nombre inséré (`f 2 4`), objet inséré (`f 2 5`, `f 4 4`).

Un message n'entre dans `trad/` que s'il contient un vrai mot latin : les
restes japonais du développement et les fiches d'aide factices
(`アクセサリー２ 0xC10 １行目`) restent tels quels dans le jeu.

## La police et les accents

Les lettres latines sont dessinées avec les cases « pleine largeur » de
`font/seurapro_12_12.bcfnt` (Ａ, ｂ…), qui portent des largeurs
proportionnelles. Dans cette police, la localisation anglaise a déjà
redessiné une rangée de symboles Shift-JIS (`0x819A`–`0x81DA`) en lettres
accentuées : è ê à â î ù û ô ç Ç ë ï É é À ä ö ü ÿ œ Â Ä È Ê Ë Î Ï Ô Ö Ù Û
Ü Ÿ Œ. La table est dans [`police/caracteres.json`](../police/caracteres.json) ;
aucune police n'est modifiée. Vérifié en jeu, dans les dialogues et les choix.

`font/seurapro_13_13.bcfnt` n'a que è ê à â î ù û ô ç Ç ë ï ; elle ne sert
ni aux dialogues ni aux choix.

Pistes écartées : les octets simples `A1`–`DF` s'affichent tous « û », et la
table Shift-JIS → Unicode de l'exécutable (à `0x4934A0` du `code.bin`
décompressé) ne commande pas le rendu du texte.

## Ce qui n'est pas encore extrait

Voir la [feuille de route](FEUILLE_DE_ROUTE.md) : textes de l'exécutable,
saisie du nom et difficultés (`.bin`), noms des étages, textures `.ctpk`.
Les `.mbm` (MSG2) sont tous en japonais : la version européenne ne les
affiche pas.
