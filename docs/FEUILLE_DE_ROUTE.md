# Feuille de route

Ce qui reste à faire, dans l'ordre où ça débloque le plus de monde.

## 1. Traduction — par ordre d'utilité

| Priorité | Fichiers | Pourquoi |
|---|---|---|
| ✅ commencé | `histoire/e000` | les premières scènes (travail de Tyron26) |
| 1 | `noms/locuteurs.json`, `histoire/txt/evt_introduction.json` | visibles partout ; ils fixent les noms et le ton des personnages |
| 2 | `systeme/init` (aides des objets, compétences, accessoires), `noms/` (objets, compétences, ennemis) | lus en permanence dans les menus et en combat |
| 3 | `systeme/facility` | le cinéma : hall, boutique, salle de fusion |
| 4 | `histoire/e100` → `histoire/e700`, dans l'ordre | l'histoire principale |
| 5 | `histoire/e800` | le plus gros bloc (86 000 mots) : quêtes et scènes annexes |
| 6 | `donjons/`, `combat/` | remarques du groupe, dialogues de combat |

Après chaque bloc : **relecture** par une autre personne, puis test en jeu.

## 2. Textes encore hors de `trad/`

Repérés pendant les premiers tests en jeu, ils ne sont pas dans les fichiers
`.bmd`/`.bf` extraits aujourd'hui :

| Où | Contenu | À faire |
|---|---|---|
| ~~archives PAK (`.arc`, `.gsd`, `.bin`)~~ | ✅ fait : 40 `.arc`, 93 `.gsd`, 3 `.bin` ; 100 scripts propres ajoutés à `trad/` (saisie du nom, menus du camp, étages, missions, quêtes) | — |
| exécutable (`code.bin`) | boîtes « Information » (carte SD, « Is this name acceptable? »…) | patch de l'exécutable (`code.ips`, accepté par Azahar et Luma3DS) |
| tables `.ctd` (dans `init/cmptable.bin`) | aides des menus du camp (« Which skill will you use? »…), description des difficultés | décoder ces tables (cases de 64 octets) |
| ~~`battle/message/*.mbm`~~ | vérifié : tout en japonais (format MSG2), la version européenne ne les affiche pas | — |
| ~~`init/itemtbl.bin`~~ | ✅ fait : 1 733 noms d'objets dans `trad/noms/objets.json` | — |
| ~~`battle/table/*nametable.tbl`~~ | ✅ fait : 778 compétences, 310 Personas, 356 ennemis dans `trad/noms/` | — |
| ~~`camp/dictionary.tbl`~~ | ✅ fait : 33 lieux dans `trad/noms/lieux.json` | — |
| noms des étages sur la carte | à localiser | chercher hors des `.tbl` |
| textures `.ctpk` | menu titre (NEW GAME…), difficulté, OK / YES / NO, boutons Log / FFWD | redessiner les images (l'aide a été proposée à Tyron26) |

## 3. Technique

- [ ] Autoriser un nombre de pages différent de l'anglais (aujourd'hui fixe).
- [ ] Vérifier où s'affiche la police `seurapro_13_13`, à qui il manque é, É, œ… ; si un écran s'en sert, y composer les lettres manquantes au build. Premier test : un nom d'objet accentué dans un menu.
- [ ] Prévoir une issue « Lignes à corriger » tenue à jour par le robot, comme sur P1.

## 4. Publication

- [ ] Patch `xdelta` du `data.cpk` (petit : seule la fin de l'archive change).
- [ ] Un patcher simple pour les joueurs (web, comme pour Persona 2 et Jack Bros.).
- [ ] Page du projet sur le site du Grimoire, annonce sur le Discord et sur le profil de l'organisation.

## 5. Questions ouvertes pour l'équipe

Les termes 💬 du [Dictionnaire](Dictionnaire.md), à commencer par le **genre
de « Persona »** : le Grimoire a choisi *la* Persona pour P1 et P2.
