# Sources des visuels

Les SVG animés du README sont générés, pas écrits à la main :

```sh
python assets/_src/gen_visuels.py     # -> assets/banniere.svg, assets/separateur.svg
```

Le texte est vectorisé à partir des polices Windows *Segoe UI Black* et
*Segoe UI Bold* (fontTools : `pip install fonttools`). GitHub sert ces
fichiers via `<img>`, ce qui bloque toute police externe ; un `<text>`
vivant s'afficherait différemment selon l'OS.

Les animations sont en CSS. Avec « réduire les animations », tout
s'affiche à l'arrêt : rideaux ouverts, ampoules allumées.

La jaquette (`assets/jaquette.jpg`) est celle de l'édition européenne.
