# 🎬 Méthode de travail — traduire Persona Q2

Le [guide de contribution](../CONTRIBUTING.md) explique le **format** des fichiers.
Ce guide-ci explique **comment on travaille** : de la scène choisie à la ligne
qui s'affiche en jeu, et ce qui fait une bonne traduction de *Persona Q2*.

---

## 1. Le parcours d'une traduction

```text
 Réserver      Traduire       Vérifier        Relire          Fusionner      Tester
 (Discord) ──▶ (trad/*.json) ──▶ (automatique) ──▶ (une 2ᵉ personne) ──▶ (main) ──▶ (en jeu)
                                    ▲                │
                                    └── corrections ◀┘
```

1. **Réserver** — annonce sur le [Discord](https://discord.gg/personafr) le fichier
   (ou le dossier) que tu prends. Une scène = une personne à la fois.
2. **Traduire** — remplis les champs `"fr"`. Une Pull Request par scène ou par
   petit groupe de fichiers : plus elle est courte, plus vite elle est relue.
3. **Vérifier** — la CI contrôle chaque proposition (balises, police, largeur des
   lignes, dictionnaire, typographie) et pose ses remarques sur les lignes.
4. **Relire** — **une autre personne** relit et approuve. C'est obligatoire :
   la branche `main` refuse une proposition qui n'a pas été approuvée.
5. **Fusionner** — un membre de l'équipe fusionne ; l'avancement se met à jour
   tout seul.
6. **Tester** — dès qu'on peut, on regarde la scène en jeu (voir
   [JOUER.md](JOUER.md)) : c'est là qu'on voit une ligne qui déborde ou un ton
   qui sonne faux. Les corrections repartent en Pull Request.

## 2. Avant de traduire une scène

- **Lis toute la scène en anglais** avant d'écrire une ligne : qui parle, à
  qui, où, ce qui vient de se passer. Une réplique isolée se traduit mal.
- **Situe-la dans le jeu.** Les dossiers suivent l'ordre de l'histoire
  (`histoire/e100` → `e700`) ; un let's play en anglais aide beaucoup.
- **Ouvre le [Dictionnaire](Dictionnaire.md).** Si un terme manque, propose-le
  sur Discord *avant* de l'utiliser partout.
- **Regarde comment les scènes voisines ont été traduites** : le ton d'un
  personnage doit rester le même d'un fichier à l'autre.

## 3. Ce qu'on cherche

**Le sens et le ton, pas le mot à mot.** Une réplique doit sonner comme une
vraie phrase française dite par ce personnage-là. On peut réorganiser une
phrase, couper autrement les lignes, changer une image qui ne marche pas en
français, tant que le sens et l'intention restent.

**Les jeux de mots s'adaptent.** Teddie fait des calembours sur les ours, les
films ont des titres parodiques : on cherche l'équivalent français, et on
laisse un `"commentaire"` pour expliquer le choix au relecteur.

**Ce qui reste japonais reste japonais** : noms, lieux, nourriture, fêtes.
On n'adapte pas la culture, on la rend compréhensible.

### La voix des personnages

Trois jeux se croisent : chaque groupe a sa façon de parler, et le dialogue
entre eux fait le sel du jeu. Repères de départ, à affiner ensemble :

| Qui | Ton | Exemple de piège |
|---|---|---|
| **Voleurs Fantômes** (P5) | lycéens d'aujourd'hui, familiers entre eux | Ryuji parle cash, sans être vulgaire à chaque ligne |
| **Brigade d'investigation** (P4) | bande de copains de petite ville | Yosuke vanne, Kanji bougonne, Naoto reste posé |
| **SEES** (P3) | plus réservés, Mitsuru très soutenue | Mitsuru ne dit pas « ouais » |
| **Morgana, Teddie, Koromaru** | mascottes, chacune sa marque | Teddie et ses calembours d'ours |
| **Velvet Room** | soutenu, un peu théâtral | Elizabeth, Margaret, Theodore, Marie : quatre styles différents |
| **Hikari, Nagi, Doe…** | personnages propres à PQ2 | Nagi est polie et un peu solennelle |

**Tu ou vous ?** Les membres d'un même groupe se tutoient. Entre groupes, au
premier contact, c'est selon l'âge et le caractère : à décider scène par
scène, puis à garder. Les résidents de la Velvet Room vouvoient le héros.

**Les suffixes japonais** (-senpai, -kun, -chan) : à décider ensemble
(voir le Dictionnaire) ; en attendant, garde ceux qui portent du sens.

## 4. La mise en page

- **Trois lignes par bulle**, environ 280 pixels par ligne. Le validateur
  mesure avec la vraie largeur des lettres et prévient en cas de risque.
- **Autant de `{PAGE}` qu'en anglais** : si ça ne tient pas, resserre la
  phrase plutôt que de la couper au milieu d'une idée.
- **Les choix sont courts** : une option tient sur une ligne, comme en anglais.
- **Les fiches de présentation** (à côté du grand nom d'un personnage) font
  cinq lignes au plus.

## 5. La typographie

| Règle | Exemple |
|---|---|
| Espace avant `! ? ; :` | « Quoi ? Non ! » |
| `!?` et `??` permis | « Tu plaisantes !? » |
| Guillemets français | « Joker » — ils s'affichent “Joker” en jeu, c'est automatique |
| Majuscules accentuées | « École », « À plus tard » |
| Points de suspension | `...` ou `…`, mais pareil dans tout un fichier |
| Nombres | « 3 objets », « 10 000 yens » |

## 6. Relire une proposition

Le relecteur ouvre l'onglet **Files changed** de la Pull Request et lit chaque
ligne française **à côté de l'anglais**. Pour proposer une correction, le
bouton **« Suggest changes »** de GitHub permet à l'auteur de l'accepter d'un clic.

Ce que le relecteur vérifie :

- [ ] le sens : rien d'ajouté, rien d'oublié, pas de contresens ;
- [ ] le ton du personnage, et la cohérence avec les scènes voisines ;
- [ ] les termes du Dictionnaire ;
- [ ] l'orthographe, la grammaire, la typographie ;
- [ ] les remarques du validateur (lignes longues, termes) : traitées ou expliquées.

Quand tout est bon : **Approve**. Une discussion ouverte doit être résolue
avant la fusion.

## 7. Les règles de la branche `main`

`main` est **protégée** :

- on n'y écrit **que par Pull Request** — personne ne pousse directement ;
- les **trois vérifications automatiques** doivent passer ;
- il faut **une approbation**, et toutes les discussions résolues ;
- on ne réécrit pas son historique, et on ne peut pas la supprimer.

L'avancement (SUIVI.md, badges, carte du README) n'est pas dans `main` : un
robot le recalcule à chaque fusion et le publie sur la branche
[`suivi`](https://github.com/Grimoire-du-Coeur/PQ2-FR-3DS/tree/suivi).

## 8. En cas de doute

- **Un terme** : le Dictionnaire, puis Discord.
- **Le contexte d'une réplique** : Discord, ou un `"commentaire"` dans l'entrée
  pour que le relecteur tranche.
- **Un bug, un texte qui déborde en jeu** : une issue « Bug en jeu » ou
  « Erreur de traduction », avec une capture.
