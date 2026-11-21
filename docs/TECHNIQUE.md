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

## Les archives .arc

Des scripts vivent aussi dans des archives Atlus « PAK » (`outils/pak.py` :
nombre d'entrées, puis nom sur 32 octets, taille et données, contigus).
40 archives sur 323 en portent (`catalogue.ARCHIVES`, 8,6 Mo) : boutique,
fusion, camp, donjons, ennemis. 40 de leurs 47 scripts sont des copies
identiques de fichiers isolés : ils partagent le même JSON, et la
réinjection écrit la traduction aux deux endroits, quelle que soit la copie
que le jeu lit. Les 7 autres ont leur propre JSON
(`facility/pack/shop.arc/x.bmd` → `systeme/facility/pack/shop/x.json`).
`aller_retour.py` balaie toutes les archives et signale une archive à
scripts absente de la liste.

Les `.pac` ne contiennent pas de texte (portraits, modèles 3D).

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

Voir la [feuille de route](FEUILLE_DE_ROUTE.md) : messages de combat `.mbm`
(MSG2), tables de noms `.tbl`, textures `.ctpk`.
