# Contribuer à PQ2-FR-3DS

Merci de vouloir aider à traduire *Persona Q2: New Cinema Labyrinth* ! Ce
guide explique le format des fichiers ; la [méthode de travail](docs/GUIDE.md)
explique comment on traduit, relit et teste. Ce guide tient en trois idées :

1. **On s'organise sur Discord** avant de traduire.
2. **On ne touche qu'aux champs `"fr"`** des fichiers de `trad/`.
3. **Un terme se traduit toujours pareil** : le [Dictionnaire](docs/Dictionnaire.md) fait foi.

---

## 1. Avant de commencer

Rejoins le **[Discord du Grimoire du Cœur](https://discord.gg/personafr)** et
annonce le fichier que tu prends (par exemple `trad/histoire/e100/e100_100.json`).
Ça évite que deux personnes traduisent la même scène, et c'est là qu'on
discute des choix de traduction.

L'ordre conseillé est dans la [feuille de route](docs/FEUILLE_DE_ROUTE.md).

## 2. Le format d'un fichier

Chaque fichier de `trad/` correspond à un fichier du jeu et contient une
liste d'entrées, une par message :

```json
{
  "id": "MSG_001",
  "locuteur": "Nagi",
  "en": "Would the merchandise here be of any{SAUT}use to you?{PAGE}Since the anomaly occurred, the stock{SAUT}here appears to have changed quite{SAUT}a bit...",
  "fr": ""
}
```

| Champ | Rôle | Tu peux le modifier ? |
|---|---|---|
| `id` | repère du message dans le jeu | **non** |
| `locuteur` | qui parle (sa traduction est dans `trad/noms/locuteurs.json`) | **non** |
| `choix` | `true` si le message est un choix proposé au joueur | **non** |
| `en` | le texte anglais du jeu, ta référence | **non** |
| `max` | place du nom dans le jeu, en octets (noms d'objets et de lieux) | **non** |
| `fr` | ta traduction ; vide = l'anglais reste en jeu | **oui** |
| `a_revoir` | l'anglais a changé depuis ta traduction : relis, puis supprime ce champ | oui (le supprimer) |
| `commentaire` | une note libre pour les relecteurs | oui |

Un fichier **peut être traduit à moitié** : une entrée vide garde son
anglais en jeu. Envoie ton travail par petits morceaux plutôt qu'en une fois.

**Une réplique ne se traduit qu'une fois.** Le jeu répète beaucoup (« Arf! »
138 fois, les choix « Yes / No »…) : au build, une entrée vide reprend la
traduction d'un anglais **identique** déjà traduit ailleurs. Si une scène
demande un autre français pour la même réplique, remplis simplement son
`"fr"` : il garde la main. Les répliques traduites de plusieurs façons sont
listées dans le suivi, section « À harmoniser ».

## 3. Les balises

Le texte contient quelques balises entre accolades. **Ce ne sont pas des
mots** : elles disent au jeu quoi faire.

| Balise | Effet | Règle |
|---|---|---|
| `{SAUT}` | retour à la ligne | libre : place-les où la phrase française les demande |
| `{PAGE}` | nouvelle bulle (le joueur appuie sur A) | **autant qu'en anglais** |
| `{OPTION}` | sépare les réponses d'un choix | **autant qu'en anglais** |
| `{f 0 1 2}` … `{f 0 1 0}` | début et fin d'un texte en couleur | toutes gardées |
| `{f 2 4 0}`, `{f 2 5 …}`, `{f 4 4 …}` | le jeu insère un nom, un objet, un nombre | toutes gardées, déplaçables dans la phrase |

Tu peux déplacer le texte autour d'une balise `{f …}` pour que la phrase
sonne bien en français, tant que **toutes** les balises sont là :

```text
en : {f 2 4 0}s have appeared!
fr : Des {f 2 4 0} apparaissent !
```

Le début et la fin de chaque bulle (portrait, voix, attente) sont gérés
automatiquement : ils n'apparaissent pas dans `trad/`.

## 4. Les accents et la ponctuation

**Tous les accents français s'écrivent normalement** : `é è ê ë à â ä î ï ô
ö ù û ü ÿ ç œ`, majuscules comprises (`É À Ç Œ`…). La police du jeu les a
déjà ; rien à faire de spécial.

Deux caractères n'existent pas dans la police et sont remplacés au build :
les guillemets `« »` deviennent `“ ”`, et `æ` devient `ae`. Tu peux donc
écrire en typographie française normale.

- Une **espace avant `! ? ; :`**, comme en français (« Quoi ? »). `!?` et `??` sont permis.
- Les points de suspension s'écrivent `...` ou `…`, au choix, mais pareil dans tout un fichier.

## 5. La longueur des lignes

Une bulle affiche **trois lignes** d'environ **280 pixels**. Le validateur
mesure chaque ligne avec la vraie largeur des lettres du jeu (un `i` fait
3 px, un `m` en fait 10) et prévient si une ligne risque de déborder. En
pratique : **une ligne française pas plus longue que la plus longue ligne
anglaise du message**, et des `{SAUT}` pour couper.

## 6. Les noms et les fiches

- **Noms des personnages qui parlent** : une seule fois, dans
  [`trad/noms/locuteurs.json`](trad/noms/locuteurs.json). Les prénoms restent
  tels quels ; seuls les noms communs se traduisent (« Despondent woman's
  voice » → « Voix d'une femme abattue »).
- **Fiches de présentation** (le texte affiché à côté du grand nom quand un
  personnage arrive) : elles sont dans
  [`trad/histoire/txt/evt_introduction.json`](trad/histoire/txt/evt_introduction.json),
  pas dans la scène. Même texte que la scène, mais sur une seule page.
- **Noms des objets et équipements** : une seule fois chacun, dans
  [`trad/noms/objets.json`](trad/noms/objets.json), dans l'ordre du jeu
  (armes, armures, accessoires, consommables, objets clés, matériaux…).
  Le nom part dans les menus, les boutiques et les dialogues. Il doit tenir
  dans sa case : **21 octets**, où une lettre accentuée compte pour deux
  (« Médicament » = 11). Le validateur refuse un nom trop long. Garder les
  séries cohérentes (« Red Ring / Red Bangle » → même couleur, même ordre),
  et les termes du [Dictionnaire](docs/Dictionnaire.md).
- **Compétences, Personas, ennemis** : dans
  [`trad/noms/competences.json`](trad/noms/competences.json),
  [`personas.json`](trad/noms/personas.json) et
  [`ennemis.json`](trad/noms/ennemis.json). Pas de limite d'octets, mais la
  place à l'écran n'est pas encore mesurée : rester proche de la longueur
  anglaise. Les sorts (Agi, Bufu, Zio…) et les Personas gardent leur nom,
  comme le dit le [Dictionnaire](docs/Dictionnaire.md) ; un fichier peut
  donc contenir beaucoup de `"fr"` identiques à l'anglais, c'est normal.
  Les compétences qui portent le nom d'un objet (« Rudra Ring ») n'y sont
  pas : elles reprennent la traduction de `objets.json`.
- **Lieux** (où l'on croise chaque ennemi : « 1st Ave.~ », « Kamoshida
  Square ») : [`trad/noms/lieux.json`](trad/noms/lieux.json), **19 octets**
  au plus. Garder le `~` final quand l'anglais en a un.

## 7. Envoyer sa traduction

**Depuis le navigateur**, sans rien installer : ouvre le fichier sur GitHub,
clique sur le crayon, remplis les `"fr"`, puis *Propose changes*. GitHub
crée la Pull Request pour toi.

**En local**, si tu préfères :

```powershell
git clone https://github.com/Grimoire-du-Coeur/PQ2-FR-3DS.git
cd PQ2-FR-3DS
python outils/valider.py trad/histoire/e100/e100_100.json
```

Chaque Pull Request est vérifiée automatiquement. Les **erreurs** (balise
oubliée, caractère absent de la police, page en trop) bloquent la fusion ;
les **remarques** (ligne longue, terme du dictionnaire, espace avant `!`)
sont à regarder mais ne bloquent pas. Elles s'affichent directement sur les
lignes concernées.

## 8. Tester en jeu

Si tu as ta propre copie du jeu, tu peux voir ta traduction dans Azahar en
quelques secondes : voir [docs/JOUER.md](docs/JOUER.md). C'est le meilleur
moyen de repérer une ligne trop longue ou un ton qui sonne faux.

## 9. Traduire avec PersonaEditor

Le projet a commencé avec PersonaEditor et Kuriimu2. Si tu as déjà traduit
des fichiers `.bmd`/`.bf` de cette façon, ils s'importent dans `trad/` sans
rien perdre :

```powershell
python outils/importer.py "Persona Q2 (Europe).3ds" "mon_dossier_traduit" --table "ma_table.txt"
```

Une entrée qui a déjà un français n'est jamais écrasée.
