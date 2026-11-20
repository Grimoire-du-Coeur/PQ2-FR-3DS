"""Génère les visuels animés du README : bannière et séparateur.

    python assets/_src/gen_visuels.py        # -> assets/banniere.svg, assets/separateur.svg

Thème : la salle de cinéma de Persona Q2. Rideaux rouges qui s'ouvrent,
enseigne à ampoules qui clignotent en chaîne, faisceaux de projecteurs,
papillon bleu, bande de film qui défile ; palette de la jaquette (rouge
velours, cyan, orange du « 2 ») et ruban tricolore du Grimoire du Cœur.

Le texte est vectorisé (fontTools + polices Windows) : GitHub sert les SVG
du README via <img>, ce qui bloque toute police externe, et un <text>
vivant s'afficherait différemment selon l'OS. Les animations sont en CSS ;
avec « réduire les animations », tout s'affiche à l'arrêt, rideaux ouverts.

Dépendance de développement : fontTools (pip install fonttools).
"""

from __future__ import annotations

import math
import random
from pathlib import Path

from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen
from fontTools.ttLib import TTFont

ASSETS = Path(__file__).resolve().parent.parent
POLICES = Path("C:/Windows/Fonts")

NOIR = "#0D0D0D"
BLANC = "#F5F5F5"
BLEU_GRIMOIRE, ROUGE_GRIMOIRE, BLEU_LISIBLE = "#002654", "#CE1126", "#3C7BE8"
ORANGE, CYAN, OR, OR_PALE = "#FF5A1F", "#36D6D6", "#FFC857", "#FFE9A8"


class Police:
    def __init__(self, fichier: str):
        self.f = TTFont(POLICES / fichier)
        self.glyphes = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.em = self.f["head"].unitsPerEm

    def largeur(self, texte: str, taille: float, espacement: float = 0) -> float:
        k = taille / self.em
        return sum(self.glyphes[self.cmap[ord(c)]].width * k + espacement for c in texte) - espacement

    def chemin(self, texte: str, x: float, y: float, taille: float, espacement: float = 0) -> str:
        """Tracé SVG du texte, ligne de base en (x, y)."""
        k = taille / self.em
        morceaux = []
        for c in texte:
            nom = self.cmap[ord(c)]
            stylo = SVGPathPen(self.glyphes)
            self.glyphes[nom].draw(TransformPen(stylo, (k, 0, 0, -k, x, y)))
            morceaux.append(stylo.getCommands())
            x += self.glyphes[nom].width * k + espacement
        return " ".join(m for m in morceaux if m)

    def centre(self, texte: str, cx: float, y: float, taille: float, espacement: float = 0) -> str:
        return self.chemin(texte, cx - self.largeur(texte, taille, espacement) / 2, y, taille, espacement)


def _num(v: float) -> str:
    return f"{v:.1f}".rstrip("0").rstrip(".")


# ---------------------------------------------------------------- bannière

def banniere() -> str:
    W, H = 1200, 440
    noire = Police("seguibl.ttf")       # Segoe UI Black
    grasse = Police("segoeuib.ttf")     # Segoe UI Bold
    rnd = random.Random(2019)           # sortie européenne de PQ2 : rendu reproductible

    # Enseigne à ampoules
    ex, ey, ew, eh = 205, 58, 790, 250
    ampoules = []
    pas = 26
    perimetre = []
    for i in range(int(ew // pas) + 1):
        perimetre.append((ex + i * pas, ey))
    for i in range(1, int(eh // pas) + 1):
        perimetre.append((ex + ew, ey + i * pas))
    for i in range(1, int(ew // pas) + 1):
        perimetre.append((ex + ew - i * pas, ey + eh))
    for i in range(1, int(eh // pas)):
        perimetre.append((ex, ey + eh - i * pas))
    for i, (x, y) in enumerate(perimetre):
        ampoules.append(f'<circle class="a{i % 3}" cx="{_num(x)}" cy="{_num(y)}" r="4.6" fill="url(#ampoule)"/>')

    # Titre
    titre_taille = 104
    persona = "PERSONA Q"
    l1 = noire.largeur(persona, titre_taille, 2)
    l2 = noire.largeur("2", titre_taille * 1.18)
    x0 = 600 - (l1 + 10 + l2) / 2
    titre = noire.chemin(persona, x0, 178, titre_taille, 2)
    deux = noire.chemin("2", x0 + l1 + 10, 182, titre_taille * 1.18)
    sous_titre = grasse.centre("NEW CINEMA LABYRINTH", 600, 222, 30, 7)
    francais = grasse.centre("TRADUCTION FRANÇAISE  ·  NINTENDO 3DS", 600, 272, 21, 3.2)
    grimoire = grasse.centre("GRIMOIRE DU CŒUR", 600, 358, 15, 5)

    # Rideaux : larges et repliés hors cadre une fois ouverts (150 px visibles de
    # chaque côté) ; fermés, chacun couvre une moitié de la salle.
    def rideau(cote: int) -> str:
        plis = []
        largeur, n, visible = 620, 22, 150
        debut = visible - largeur if cote < 0 else W - visible
        for i in range(n):
            x = debut + i * largeur / n
            plis.append(f'<rect x="{_num(x)}" y="0" width="{_num(largeur / n + 0.5)}" height="{H}" '
                        f'fill="url(#pli)"/>')
        bord = visible - 6 if cote < 0 else W - visible
        return (f'<g class="rideau {"gauche" if cote < 0 else "droite"}">{"".join(plis)}'
                f'<rect x="{bord}" y="0" width="6" height="{H}" fill="#3A030B" opacity=".7"/></g>')

    festons = []
    for i in range(12):
        cx = 50 + i * 100
        festons.append(f'<path d="M{cx - 50} 0 Q{cx} 46 {cx + 50} 0 Z" fill="url(#feston)"/>')
        festons.append(f'<path d="M{cx - 50} 2 Q{cx} 44 {cx + 50} 2" fill="none" stroke="{OR}" '
                       f'stroke-width="1.4" opacity=".55"/>')

    poussiere = []
    for _ in range(26):
        x, y = rnd.uniform(240, 960), rnd.uniform(40, 380)
        poussiere.append(f'<circle class="p{rnd.randrange(3)}" cx="{_num(x)}" cy="{_num(y)}" '
                         f'r="{_num(rnd.uniform(.8, 1.9))}" fill="{OR_PALE}"/>')

    # Bande de film : perforations sur une période de 48 px, qui défile
    perfos = []
    for i in range(-2, 28):
        x = i * 48
        perfos.append(f'<rect x="{x + 8}" y="395" width="18" height="9" rx="2" fill="{BLANC}" opacity=".26"/>')
        perfos.append(f'<rect x="{x + 8}" y="424" width="18" height="9" rx="2" fill="{BLANC}" opacity=".26"/>')
        perfos.append(f'<rect x="{x + 34}" y="408" width="12" height="12" rx="1.5" fill="{CYAN}" opacity=".10"/>')

    papillon = (
        '<g class="papillon"><g transform="translate(872 348) rotate(-14)">'
        f'<g class="ailes"><path d="M0 0 C-22 -26 -38 -8 -26 8 C-18 18 -6 10 0 2 Z" fill="{CYAN}"/>'
        f'<path d="M0 2 C-8 16 -22 26 -14 32 C-6 36 -1 20 0 6 Z" fill="#1E8FA8"/>'
        f'<path d="M0 0 C22 -26 38 -8 26 8 C18 18 6 10 0 2 Z" fill="{CYAN}"/>'
        f'<path d="M0 2 C8 16 22 26 14 32 C6 36 1 20 0 6 Z" fill="#1E8FA8"/></g>'
        f'<rect x="-1.6" y="-8" width="3.2" height="22" rx="1.6" fill="{NOIR}"/></g></g>')

    style = (
        "<style>"
        ".rideau{animation:ouvrir 2.6s cubic-bezier(.22,.8,.25,1) .4s both}"
        ".gauche{--d:-1}.droite{--d:1}"
        "@keyframes ouvrir{from{transform:translateX(calc(var(--d) * -455px))}to{transform:none}}"
        ".a0,.a1,.a2{animation:chaine 1.2s steps(1) infinite}"
        ".a1{animation-delay:-.4s}.a2{animation-delay:-.8s}"
        "@keyframes chaine{0%{opacity:1}33%{opacity:.28}66%{opacity:.6}}"
        ".faisceau{transform-box:fill-box;transform-origin:50% 0;animation:balaie 7s ease-in-out infinite alternate}"
        ".f2{animation-duration:9s;animation-delay:-3s}"
        "@keyframes balaie{from{transform:rotate(-7deg)}to{transform:rotate(7deg)}}"
        ".film{animation:defile 2.4s linear infinite}"
        "@keyframes defile{to{transform:translateX(-48px)}}"
        ".p0,.p1,.p2{animation:scintille 3.2s ease-in-out infinite}.p1{animation-delay:-1.1s}.p2{animation-delay:-2.2s}"
        "@keyframes scintille{50%{opacity:.15}}"
        ".papillon{animation:vole 6s ease-in-out infinite}"
        "@keyframes vole{50%{transform:translate(-14px,10px)}}"
        ".ailes{transform-box:fill-box;transform-origin:50% 50%;animation:bat .5s ease-in-out infinite alternate}"
        "@keyframes bat{to{transform:scaleX(.35)}}"
        ".reflet{animation:reflet 5.5s ease-in-out 1.8s infinite}"
        "@keyframes reflet{0%{transform:translateX(-260px)}45%,100%{transform:translateX(1060px)}}"
        "@media (prefers-reduced-motion:reduce){*{animation:none!important}.reflet{opacity:0}}"
        "</style>")

    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-labelledby="t d">
<title id="t">Persona Q2: New Cinema Labyrinth — traduction française (Nintendo 3DS)</title>
<desc id="d">Bannière : une salle de cinéma dont les rideaux rouges s'ouvrent sur une enseigne lumineuse portant le titre du jeu.</desc>
<defs>
<radialGradient id="salle" cx="50%" cy="42%" r="75%"><stop offset="0" stop-color="#3A0C14"/><stop offset=".55" stop-color="#1A0509"/><stop offset="1" stop-color="#070203"/></radialGradient>
<pattern id="trame" width="6" height="6" patternUnits="userSpaceOnUse"><circle cx="3" cy="3" r=".8" fill="{BLANC}" opacity=".05"/></pattern>
<linearGradient id="pli" x1="0" x2="1"><stop offset="0" stop-color="#5A0711"/><stop offset=".35" stop-color="#B5162B"/><stop offset=".55" stop-color="#D6283F"/><stop offset=".8" stop-color="#8E0E1F"/><stop offset="1" stop-color="#4A050E"/></linearGradient>
<linearGradient id="feston" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#7A0A18"/><stop offset="1" stop-color="#C21A30"/></linearGradient>
<linearGradient id="cone" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{OR_PALE}" stop-opacity=".30"/><stop offset="1" stop-color="{OR_PALE}" stop-opacity="0"/></linearGradient>
<linearGradient id="enseigne" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#1C060B"/><stop offset="1" stop-color="#0B0204"/></linearGradient>
<linearGradient id="deux" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#FF8A3D"/><stop offset="1" stop-color="#E5340F"/></linearGradient>
<radialGradient id="ampoule"><stop offset="0" stop-color="#FFFFFF"/><stop offset=".45" stop-color="{OR_PALE}"/><stop offset="1" stop-color="{OR}"/></radialGradient>
<linearGradient id="balayage" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#fff" stop-opacity=".22"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<filter id="lueur" x="-20%" y="-40%" width="140%" height="180%"><feGaussianBlur stdDeviation="5" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>
<filter id="halo" x="-100%" y="-100%" width="300%" height="300%"><feGaussianBlur stdDeviation="2.6"/></filter>
<clipPath id="cadre"><rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" rx="18"/></clipPath>
</defs>
{style}
<rect width="{W}" height="{H}" fill="url(#salle)"/>
<rect width="{W}" height="{H}" fill="url(#trame)"/>
<polygon class="faisceau" points="330,0 380,0 520,{H} 190,{H}" fill="url(#cone)"/>
<polygon class="faisceau f2" points="820,0 870,0 1010,{H} 680,{H}" fill="url(#cone)"/>
{"".join(poussiere)}
<rect x="{ex}" y="{ey}" width="{ew}" height="{eh}" rx="18" fill="url(#enseigne)" stroke="{OR}" stroke-width="2.5"/>
<rect x="{ex + 14}" y="{ey + 14}" width="{ew - 28}" height="{eh - 28}" rx="10" fill="none" stroke="{OR}" stroke-width="1" opacity=".35"/>
<g filter="url(#halo)" opacity=".85">{"".join(ampoules)}</g>
{"".join(ampoules)}
<path d="{titre}" fill="{BLANC}" filter="url(#lueur)"/>
<path d="{deux}" fill="url(#deux)" filter="url(#lueur)"/>
<path d="{sous_titre}" fill="{CYAN}"/>
<rect x="420" y="240" width="360" height="1.5" fill="{OR}" opacity=".5"/>
<path d="{francais}" fill="{OR_PALE}"/>
<g clip-path="url(#cadre)"><rect class="reflet" x="0" y="{ey}" width="140" height="{eh}" fill="url(#balayage)" transform="skewX(-18)"/></g>
<rect x="531" y="326" width="46" height="8" fill="{BLEU_GRIMOIRE}"/><rect x="577" y="326" width="46" height="8" fill="{BLANC}"/><rect x="623" y="326" width="46" height="8" fill="{ROUGE_GRIMOIRE}"/>
<path d="{grimoire}" fill="{BLANC}" opacity=".9"/>
{papillon}
<rect x="0" y="386" width="{W}" height="54" fill="{NOIR}"/>
<g class="film">{"".join(perfos)}</g>
<rect x="0" y="386" width="{W}" height="2" fill="{OR}" opacity=".45"/>
{rideau(-1)}
{rideau(1)}
{"".join(festons)}
</svg>
'''


# ---------------------------------------------------------------- séparateur

def separateur() -> str:
    W, H = 1200, 40
    trous = "".join(
        f'<circle cx="{_num(600 + 9 * math.cos(a))}" cy="{_num(20 + 9 * math.sin(a))}" r="3.2" fill="{NOIR}" stroke="{OR}" stroke-width=".9"/>'
        for a in (math.radians(90 + 72 * k) for k in range(5)))
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" width="{W}" height="{H}" role="img" aria-label="séparateur">
<defs>
<linearGradient id="g" x1="0" x2="1"><stop offset="0" stop-color="{CYAN}" stop-opacity="0"/><stop offset=".35" stop-color="{CYAN}"/><stop offset=".5" stop-color="{OR}"/><stop offset=".65" stop-color="{ORANGE}"/><stop offset="1" stop-color="{ORANGE}" stop-opacity="0"/></linearGradient>
<linearGradient id="r" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".5" stop-color="#FFF4D6" stop-opacity=".9"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
<clipPath id="c"><rect x="0" y="19" width="{W}" height="2"/></clipPath>
</defs>
<style>.b{{animation:b 4.5s ease-in-out infinite}}@keyframes b{{0%{{transform:translateX(-200px)}}60%,100%{{transform:translateX(1300px)}}}}.bobine{{transform-box:fill-box;transform-origin:50% 50%;animation:tourne 6s linear infinite}}@keyframes tourne{{to{{transform:rotate(360deg)}}}}@media (prefers-reduced-motion:reduce){{*{{animation:none!important}}.b{{opacity:0}}}}</style>
<rect x="0" y="19" width="{W}" height="2" fill="url(#g)"/>
<g clip-path="url(#c)"><rect class="b" x="0" y="19" width="180" height="2" fill="url(#r)"/></g>
<rect x="566" y="17" width="68" height="6" rx="3" fill="{NOIR}"/>
<g class="bobine"><circle cx="600" cy="20" r="15" fill="#5A0711" stroke="{OR}" stroke-width="1.8"/>{trous}<circle cx="600" cy="20" r="2.4" fill="{ORANGE}"/></g>
</svg>
'''


if __name__ == "__main__":
    (ASSETS / "banniere.svg").write_text(banniere(), encoding="utf-8", newline="\n")
    (ASSETS / "separateur.svg").write_text(separateur(), encoding="utf-8", newline="\n")
    print("assets/banniere.svg et assets/separateur.svg générés")
