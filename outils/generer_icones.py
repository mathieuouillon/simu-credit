"""Génère le logo et les icônes de l'application à partir d'un seul dessin vectoriel.

    uv run python outils/generer_icones.py

Produit :
- simu_credit/assets/logo.svg et logo.png : logo affiché dans la fenêtre et l'en-tête ;
- icones/icone.icns : icône macOS (avec la marge prévue par la grille d'Apple) ;
- icones/icone.ico  : icône Windows (16 à 256 px).
"""

from __future__ import annotations

import os
import struct
import subprocess
import sys
import tempfile
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, Qt  # noqa: E402
from PySide6.QtGui import QGuiApplication, QImage, QPainter  # noqa: E402
from PySide6.QtSvg import QSvgRenderer  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def dessin(marge: int) -> str:
    """Logo sur une grille de 1024 : fond arrondi bleu, barres croissantes et flèche de tendance.

    `marge` : espace autour du carré arrondi (macOS : 100, comme la grille d'Apple ; Windows : 24).
    """
    cote = 1024 - 2 * marge
    rayon = cote * 0.225
    # Contenu placé dans le carré arrondi, en coordonnées relatives (0 à 1)
    def x(v): return marge + v * cote
    def y(v): return marge + v * cote
    def l(v): return v * cote

    barres = "".join(
        f'<rect x="{x(gauche):.1f}" y="{y(haut):.1f}" width="{l(0.17):.1f}" height="{y(0.80) - y(haut):.1f}" '
        f'rx="{l(0.035):.1f}" fill="white" fill-opacity="{opacite}"/>'
        for gauche, haut, opacite in ((0.17, 0.62, 0.70), (0.415, 0.50, 0.85), (0.66, 0.38, 1.0))
    )
    epaisseur = l(0.075)
    fleche = (
        f'<polyline points="{x(0.17):.1f},{y(0.45):.1f} {x(0.40):.1f},{y(0.30):.1f} '
        f'{x(0.55):.1f},{y(0.36):.1f} {x(0.78):.1f},{y(0.17):.1f}" fill="none" stroke="white" '
        f'stroke-width="{epaisseur:.1f}" stroke-linecap="round" stroke-linejoin="round"/>'
        f'<polygon points="{x(0.85):.1f},{y(0.11):.1f} {x(0.83):.1f},{y(0.29):.1f} {x(0.67):.1f},{y(0.13):.1f}" '
        f'fill="white" stroke="white" stroke-width="{l(0.02):.1f}" stroke-linejoin="round"/>'
    )
    # Liseré sombre sous la flèche pour la détacher des barres
    contour = fleche.replace('stroke="white"', 'stroke="#1e40af"').replace(
        f'stroke-width="{epaisseur:.1f}"', f'stroke-width="{epaisseur * 1.9:.1f}"'
    ).replace('fill="white"', 'fill="#1e40af"')
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="1024" height="1024">
  <defs>
    <linearGradient id="fond" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0" stop-color="#3b82f6"/>
      <stop offset="1" stop-color="#1d4ed8"/>
    </linearGradient>
  </defs>
  <rect x="{marge}" y="{marge}" width="{cote}" height="{cote}" rx="{rayon:.1f}" fill="url(#fond)"/>
  {barres}
  <g opacity="0.55">{contour}</g>
  {fleche}
</svg>
'''


def rendu(svg: str, taille: int) -> QImage:
    image = QImage(taille, taille, QImage.Format.Format_ARGB32_Premultiplied)
    image.fill(Qt.GlobalColor.transparent)
    peintre = QPainter(image)
    peintre.setRenderHint(QPainter.RenderHint.Antialiasing)
    QSvgRenderer(QByteArray(svg.encode())).render(peintre)
    peintre.end()
    return image


def png(image: QImage) -> bytes:
    tampon = QBuffer()
    tampon.open(QIODevice.OpenModeFlag.WriteOnly)
    image.save(tampon, "PNG")
    return bytes(tampon.data())


def ecrire_ico(svg: str, chemin: Path, tailles=(16, 24, 32, 48, 64, 128, 256)) -> None:
    """Fichier .ico multi-tailles (images PNG intégrées, format accepté depuis Windows Vista)."""
    images = [png(rendu(svg, t)) for t in tailles]
    entete = struct.pack("<HHH", 0, 1, len(images))
    decalage = len(entete) + 16 * len(images)
    repertoire, donnees = b"", b""
    for t, contenu in zip(tailles, images):
        repertoire += struct.pack("<BBBBHHII", t % 256, t % 256, 0, 0, 1, 32, len(contenu), decalage)
        decalage += len(contenu)
        donnees += contenu
    chemin.write_bytes(entete + repertoire + donnees)


def ecrire_icns(svg: str, chemin: Path) -> None:
    """Icône macOS via l'outil système iconutil (uniquement sur macOS)."""
    if sys.platform != "darwin":
        print("iconutil indisponible hors macOS : icone.icns non régénéré")
        return
    with tempfile.TemporaryDirectory() as dossier:
        jeu = Path(dossier) / "icone.iconset"
        jeu.mkdir()
        for t in (16, 32, 128, 256, 512):
            rendu(svg, t).save(str(jeu / f"icon_{t}x{t}.png"))
            rendu(svg, 2 * t).save(str(jeu / f"icon_{t}x{t}@2x.png"))
        subprocess.run(["iconutil", "-c", "icns", str(jeu), "-o", str(chemin)], check=True)


def main() -> None:
    QGuiApplication(sys.argv)
    assets = RACINE / "simu_credit" / "assets"
    serre, apple = dessin(marge=24), dessin(marge=100)
    (assets / "logo.svg").write_text(serre, encoding="utf-8")
    rendu(serre, 256).save(str(assets / "logo.png"))
    (RACINE / "icones").mkdir(exist_ok=True)
    ecrire_ico(serre, RACINE / "icones" / "icone.ico")
    ecrire_icns(apple, RACINE / "icones" / "icone.icns")
    if len(sys.argv) > 1:  # aperçu : python outils/generer_icones.py dossier
        for t in (1024, 128, 64, 32, 16):
            rendu(apple if t == 1024 else serre, t).save(str(Path(sys.argv[1]) / f"apercu_{t}.png"))
    print("Logo et icônes générés.")


if __name__ == "__main__":
    main()
