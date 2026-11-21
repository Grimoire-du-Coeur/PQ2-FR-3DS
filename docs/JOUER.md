# Jouer en français

> [!IMPORTANT]
> Il n'y a pas encore de version publique du patch. Ce guide sert aujourd'hui à
> **tester la traduction en cours** à partir de ce dépôt. Il faut posséder le jeu :
> aucune donnée du jeu n'est fournie ici.

## Ce qu'il faut

- *Persona Q2: New Cinema Labyrinth* en **version européenne**
  (`CTR-P-AQ2P`, title ID `00040000001D7600`), sous forme d'image **décryptée**.
  Depuis sa propre console, **GodMode9** permet d'extraire la cartouche ou le
  jeu installé en `.3ds` décrypté.
- **Python 3.10** ou plus récent.
- **Azahar** sur PC, ou une 3DS avec **Luma3DS**.

> Citra n'est plus maintenu depuis 2024 ; Azahar est son successeur direct, et
> le chargement des mods fonctionne de la même façon.

## Construire le texte français

```powershell
git clone https://github.com/Grimoire-du-Coeur/PQ2-FR-3DS.git
cd PQ2-FR-3DS
python outils/injecter.py "C:\chemin\vers\Persona Q2 (Europe).3ds" --azahar
```

Le premier lancement copie l'archive du jeu (`data.cpk`, 2,8 Go) une seule
fois ; ensuite, chaque build ne prend que quelques secondes. Seuls les
fichiers qui ont du français sont réécrits, à la fin de l'archive.

## Sur PC, avec Azahar

`--azahar` écrit directement l'archive à l'endroit où Azahar charge les mods :

```text
%APPDATA%\Azahar\load\mods\00040000001D7600\romfs\data.cpk
%APPDATA%\Azahar\load\mods\00040000001D7600\code.ips
```

`code.ips` porte les boîtes système traduites (sauvegarde, carte SD,
« Is this name acceptable? »…). Il n'est écrit que si l'une d'elles a du
français, et il faut pour cela l'image complète (`.3ds`), pas `data.cpk` seul.

Lance ensuite le jeu normalement. Pour revenir à l'anglais, supprime ce dossier.

## Sur 3DS, avec Luma3DS

```powershell
python outils/injecter.py "…\Persona Q2 (Europe).3ds" --sortie "E:\luma\titles\00040000001D7600\romfs\data.cpk"
```

(`E:` étant la carte SD.) Le `code.ips` des boîtes système est écrit à côté,
dans `E:\luma\titles\00040000001D7600\code.ips`. Puis, dans la configuration
de Luma3DS (maintenir SELECT au démarrage), active **« Enable game patching »**.

## En cas de souci

- **« l'image est chiffrée »** : l'image n'est pas décryptée ; repasser par GodMode9.
- **« cette image a le title ID … »** : ce n'est pas la version européenne ; le
  patch ne vise que celle-ci pour l'instant.
- **Texte coupé, caractère bizarre, plantage** : ouvrir une issue
  [« Bug en jeu »](../../../issues/new/choose) avec une capture.
