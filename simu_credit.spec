# Construction de l'application autonome, sans installation :
#   uv run pyinstaller simu_credit.spec --noconfirm
# À lancer sur chaque système cible (PyInstaller ne sait pas compiler pour un autre système) :
#   - macOS   -> dist/Simulateur de credit.app (affiché « Simulateur de crédit »)
#   - Windows -> dist/SimulateurCredit.exe (un seul fichier)
import re
import sys

NOM = "Simulateur de credit"  # nom de fichier sans accent : codesign échoue sinon sur macOS
NOM_AFFICHE = "Simulateur de crédit"
# Version lue dans simu_credit/__init__.py (source unique)
VERSION = re.search(r'__version__ = "(.+?)"', open("simu_credit/__init__.py", encoding="utf-8").read()).group(1)

# Modules Qt inutiles ici : les exclure allège nettement l'application
EXCLUS = [
    "tkinter",
    "PySide6.QtWebEngineCore", "PySide6.QtWebEngineWidgets", "PySide6.QtWebEngineQuick",
    "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtQuick3D", "PySide6.Qt3DCore",
    "PySide6.QtMultimedia", "PySide6.QtPdf", "PySide6.QtNetwork", "PySide6.QtBluetooth",
    "PySide6.QtSql", "PySide6.QtTest", "PySide6.QtDesigner",
]

a = Analysis(
    ["lanceur.py"],
    datas=[("simu_credit/assets", "simu_credit/assets")],
    excludes=EXCLUS,
)
pyz = PYZ(a.pure)

if sys.platform == "darwin":
    exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name=NOM, console=False)
    coll = COLLECT(exe, a.binaries, a.datas, name=NOM)
    app = BUNDLE(
        coll,
        name=f"{NOM}.app",
        bundle_identifier="fr.enseignement.simulateur-credit",
        version=VERSION,
        info_plist={
            "CFBundleDisplayName": NOM_AFFICHE,
            "CFBundleName": NOM_AFFICHE,
            "CFBundleShortVersionString": VERSION,
            "NSHighResolutionCapable": True,
            "NSRequiresAquaSystemAppearance": True,  # thème clair
        },
    )
else:
    # Windows / Linux : un seul exécutable, sans fenêtre de console
    exe = EXE(pyz, a.scripts, a.binaries, a.datas, name="SimulateurCredit", console=False)
