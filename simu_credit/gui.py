"""Interface graphique (PySide6) du simulateur de crédit."""

from __future__ import annotations

import csv
import sys
from pathlib import Path

from PySide6.QtCharts import (
    QBarCategoryAxis,
    QBarSet,
    QChart,
    QChartView,
    QHorizontalStackedBarSeries,
    QLegend,
    QPieSeries,
    QStackedBarSeries,
    QValueAxis,
)
from PySide6.QtCore import QAbstractTableModel, QLocale, QMargins, QModelIndex, QSettings, QSize, Qt, QTimer, Signal
from PySide6.QtGui import QBrush, QColor, QFont, QIcon, QPainter, QPalette, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLayout,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QSplitter,
    QStackedWidget,
    QTableView,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from simu_credit import scenarios
from simu_credit.calcul import Budget, ResultatCredit, mois_bascule
from simu_credit.scenarios import (
    COULEUR_ALERTE,
    COULEUR_OK,
    ENDETTEMENT_MAX,
    POSTES_BUDGET,
    PROFILS,
    TAUX_NOTAIRE,
    Parametres,
    Scenario,
)
from simu_credit.formats import duree_texte, eur, pct
from simu_credit.pedagogie import LEXIQUE, expliquer

ACCENT = "#2563eb"
COULEUR_CAPITAL = QColor("#3b82f6")
COULEUR_INTERETS = QColor("#f59e0b")
COULEUR_ASSURANCE = QColor("#10b981")
COULEUR_FRAIS = QColor("#8b5cf6")
COULEUR_DEPENSES = QColor("#a3acb9")
TEXTE = QColor("#111827")
TEXTE_SECONDAIRE = QColor("#6b7280")
GRILLE = QColor("#eef0f3")


# --------------------------------------------------------------------------- champs


def _preparer(s: QAbstractSpinBox) -> None:
    """Marge intérieure du texte (le padding de la feuille de style ne s'applique pas au texte)."""
    s.lineEdit().setTextMargins(4, 0, 4, 0)


def champ_montant(defaut: float, maxi: float = 5_000_000, pas: float = 500) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(0, maxi)
    s.setDecimals(0)
    s.setSingleStep(pas)
    s.setGroupSeparatorShown(True)
    s.setSuffix(" €")
    _preparer(s)
    s.setValue(defaut)
    return s


def champ_taux(defaut: float, maxi: float = 25, pas: float = 0.05) -> QDoubleSpinBox:
    s = QDoubleSpinBox()
    s.setRange(0, maxi)
    s.setDecimals(2)
    s.setSingleStep(pas)
    s.setSuffix(" %")
    _preparer(s)
    s.setValue(defaut)
    return s


def champ_duree(defaut: int, mini: int, maxi: int, suffixe: str) -> QSpinBox:
    s = QSpinBox()
    s.setRange(mini, maxi)
    s.setSuffix(suffixe)
    _preparer(s)
    s.setValue(defaut)
    return s


class Segmente(QFrame):
    """Boutons segmentés synchronisés avec un QComboBox, qui reste la source de vérité."""

    def __init__(self, combo: QComboBox):
        super().__init__()
        self.setObjectName("segmente")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(3, 3, 3, 3)
        layout.setSpacing(2)
        self.groupe = QButtonGroup(self)
        for i in range(combo.count()):
            bouton = QPushButton(combo.itemText(i))
            bouton.setObjectName("segment")
            bouton.setCheckable(True)
            bouton.setCursor(Qt.CursorShape.PointingHandCursor)
            self.groupe.addButton(bouton, i)
            layout.addWidget(bouton)
        self.groupe.idClicked.connect(combo.setCurrentIndex)
        combo.currentIndexChanged.connect(lambda i: self.groupe.button(i).setChecked(True))
        self.groupe.button(max(combo.currentIndex(), 0)).setChecked(True)


def nouveau_graphique(titre: str) -> QChart:
    """Graphique au style de l'application : fond blanc, titre sobre, légende à pastilles."""
    chart = QChart()
    chart.setTitle(titre)
    chart.setAnimationOptions(QChart.AnimationOption.NoAnimation)
    chart.setBackgroundBrush(QBrush(QColor("white")))
    chart.setBackgroundPen(QPen(Qt.PenStyle.NoPen))
    chart.setBackgroundRoundness(0)
    police_titre = QFont(chart.titleFont())
    police_titre.setPointSizeF(police_titre.pointSizeF() * 1.05)
    police_titre.setWeight(QFont.Weight.DemiBold)
    chart.setTitleFont(police_titre)
    chart.setTitleBrush(TEXTE)
    chart.legend().setLabelColor(QColor("#374151"))
    chart.legend().setMarkerShape(QLegend.MarkerShape.MarkerShapeCircle)
    chart.setMargins(QMargins(4, 4, 16, 4))
    return chart


def styliser(chart: QChart) -> None:
    """Axes discrets : libellés gris, grille très claire, sans cadre."""
    for axe in chart.axes():
        axe.setLabelsColor(TEXTE_SECONDAIRE)
        axe.setTitleBrush(TEXTE_SECONDAIRE)
        axe.setGridLineColor(GRILLE)
        axe.setLinePen(QPen(QColor("#d1d5db")))
        axe.setShadesVisible(False)


# --------------------------------------------------------------------------- résultats


class CarteValeur(QFrame):
    def __init__(self, titre: str, mise_en_avant: bool = False):
        super().__init__()
        self.setObjectName("carteMiseEnAvant" if mise_en_avant else "carte")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 10, 14, 10)
        layout.setSpacing(4)
        self.titre = QLabel(titre)
        self.titre.setObjectName("carteTitre")
        self.valeur = QLabel("—")
        self.valeur.setObjectName("carteValeurGrande" if mise_en_avant else "carteValeur")
        layout.addWidget(self.titre)
        layout.addWidget(self.valeur)


class LibelleSouple(QLabel):
    """Libellé qui garde sa largeur naturelle mais n'impose aucune largeur minimale à la fenêtre."""

    def minimumSizeHint(self) -> QSize:
        return QSize(0, super().minimumSizeHint().height())


class GrilleCartes(QWidget):
    """Cartes réparties sur autant de colonnes que la largeur le permet.

    Les cartes clés (en grand) passent de 3 à 2 puis 1 par ligne, les cartes de détail de 4 à 1.
    Une ligne incomplète partage toute la largeur entre ses cartes.
    """

    def __init__(self, cles: list[QWidget], details: list[QWidget], largeur_min: int = 190):
        super().__init__()
        self.cles, self.details, self.largeur_min = cles, details, largeur_min
        self.grille = QGridLayout(self)
        self.grille.setContentsMargins(0, 0, 0, 0)
        self.grille.setSpacing(10)
        # La largeur minimale est gérée ici, pas par la grille : sinon elle bloquerait le rétrécissement
        self.grille.setSizeConstraint(QLayout.SizeConstraint.SetNoConstraint)
        for c in range(12):
            self.grille.setColumnStretch(c, 1)
        self._disposition: tuple[int, int] | None = None
        self._disposer(4 * largeur_min)

    def _disposer(self, largeur: int) -> None:
        par_ligne = max(1, largeur // self.largeur_min)
        disposition = (min(len(self.cles), par_ligne) or 1, min(4, par_ligne))
        if disposition == self._disposition:
            return
        self._disposition = disposition
        while self.grille.count():
            self.grille.takeAt(0)
        ligne = 0
        for cartes, colonnes in ((self.cles, disposition[0]), (self.details, disposition[1])):
            for debut in range(0, len(cartes), colonnes):
                rangee = cartes[debut:debut + colonnes]
                portee = 12 // len(rangee)
                for k, carte in enumerate(rangee):
                    self.grille.addWidget(carte, ligne, k * portee, 1, portee)
                ligne += 1
        self.updateGeometry()

    def minimumSizeHint(self) -> QSize:
        return QSize(self.largeur_min, self.grille.minimumSize().height())

    def sizeHint(self) -> QSize:
        return QSize(4 * self.largeur_min, self.grille.sizeHint().height())

    def resizeEvent(self, event) -> None:
        self._disposer(event.size().width())
        super().resizeEvent(event)


class SeparateurResultats(QSplitter):
    """Cartes de résultats en haut, onglets en bas, séparés par une poignée réglable.

    Tant que la poignée n'a pas été déplacée, le haut prend la hauteur de son contenu sans priver
    les onglets de HAUTEUR_ONGLETS pixels ; s'il manque de la place, les cartes défilent.
    """

    HAUTEUR_ONGLETS = 280

    def __init__(self, contenu: QWidget, onglets: QWidget):
        super().__init__(Qt.Orientation.Vertical)
        self.setHandleWidth(14)
        self.contenu = contenu
        contenu.setObjectName("contenuCartes")
        self.zone = QScrollArea()
        self.zone.setObjectName("zoneCartes")
        self.zone.setWidget(contenu)
        self.zone.setWidgetResizable(True)
        self.zone.setFrameShape(QFrame.Shape.NoFrame)
        self.zone.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.addWidget(self.zone)
        self.addWidget(onglets)
        self.setCollapsible(1, False)
        self.setStretchFactor(1, 1)
        onglets.setMinimumHeight(160)
        self.setToolTip("Faites glisser pour agrandir ou masquer les cartes de résultats")
        self._manuel = False
        self.splitterMoved.connect(self._deplace)

    def _deplace(self, *_) -> None:
        self._manuel = True

    def ajuster(self) -> None:
        if self._manuel:
            return
        total = self.height() - self.handleWidth()
        if total <= 0:
            return
        disposition = self.contenu.layout()
        largeur = self.zone.viewport().width()
        if disposition.hasHeightForWidth():
            besoin = disposition.totalHeightForWidth(largeur)
        else:
            besoin = self.contenu.sizeHint().height()
        haut = max(0, min(besoin + 2, total - self.HAUTEUR_ONGLETS))
        self.setSizes([haut, total - haut])

    def ajuster_plus_tard(self) -> None:
        QTimer.singleShot(0, self.ajuster)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.ajuster()


class ModeleAmortissement(QAbstractTableModel):
    COLONNES = ["N°", "Mensualité", "Intérêts", "Capital", "Assurance", "Capital restant"]

    def __init__(self):
        super().__init__()
        self.resultat: ResultatCredit | None = None
        self.bascule: int | None = None

    def definir(self, resultat: ResultatCredit) -> None:
        self.beginResetModel()
        self.resultat = resultat
        self.bascule = mois_bascule(resultat.tableau)
        self.endResetModel()

    def rowCount(self, parent=QModelIndex()) -> int:
        return 0 if self.resultat is None or parent.isValid() else len(self.resultat.tableau)

    def columnCount(self, parent=QModelIndex()) -> int:
        return len(self.COLONNES)

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if self.resultat is None or not index.isValid():
            return None
        e = self.resultat.tableau[index.row()]
        if role == Qt.ItemDataRole.DisplayRole:
            if index.column() == 0:
                return f"{e.numero} (an {(e.numero - 1) // 12 + 1})"
            valeurs = [e.mensualite, e.interets, e.capital, e.assurance, e.capital_restant]
            return eur(valeurs[index.column() - 1])
        if e.numero == self.bascule:
            if role == Qt.ItemDataRole.BackgroundRole:
                return QBrush(QColor("#fef3c7"))
            if role == Qt.ItemDataRole.ToolTipRole:
                return "Point de bascule : à partir de cette échéance, la part de capital dépasse celle des intérêts."
        if role == Qt.ItemDataRole.TextAlignmentRole:
            if index.column() == 0:
                return Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
            return Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
        return None

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            return self.COLONNES[section]
        return None


class PanneauResultats(QWidget):
    duree_choisie = Signal(int)  # double-clic sur une ligne de la comparaison (en mois)

    # Carte -> entrée du lexique affichée en infobulle
    AIDE_CARTES = {
        "mensualite": "Mensualité",
        "taeg": "TAEG",
        "cout": "Coût total du crédit",
        "mensualite_ha": "Amortissement",
        "assurance_m": "Assurance emprunteur",
        "assurance": "Assurance emprunteur",
        "frais": "Frais de dossier et de garantie",
        "taux": "Taux nominal (ou taux débiteur)",
    }

    CARTES = [
        ("mensualite", "Mensualité (assurance incluse)", True),
        ("taeg", "TAEG", True),
        ("cout", "Coût total du crédit", True),
        ("capital", "Montant emprunté", False),
        ("mensualite_ha", "Mensualité hors assurance", False),
        ("assurance_m", "Assurance / mois", False),
        ("interets", "Total des intérêts", False),
        ("assurance", "Total assurance", False),
        ("frais", "Frais (dossier, garantie…)", False),
        ("total_du", "Montant total dû", False),
    ]

    def __init__(self):
        super().__init__()
        self.resultat: ResultatCredit | None = None
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        # Chiffres clés en grand, puis les détails ; le nombre de colonnes suit la largeur
        self.cartes: dict[str, CarteValeur] = {}
        for cle, titre, avant in self.CARTES:
            carte = CarteValeur(titre, avant)
            if cle in self.AIDE_CARTES:
                carte.setToolTip(LEXIQUE[self.AIDE_CARTES[cle]])
            self.cartes[cle] = carte
        grille = GrilleCartes(
            [self.cartes[c[0]] for c in self.CARTES if c[2]],
            [self.cartes[c[0]] for c in self.CARTES if not c[2]],
        )
        haut = QWidget()
        h = QVBoxLayout(haut)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        h.addWidget(grille)

        self.zone_indicateurs = QLabel()
        self.zone_indicateurs.setObjectName("indicateurs")
        self.zone_indicateurs.setWordWrap(True)
        self.zone_indicateurs.setTextFormat(Qt.TextFormat.RichText)
        h.addWidget(self.zone_indicateurs)

        # Séparateur réglable : on peut agrandir les onglets (explications, tableau) en réduisant les cartes
        self.onglets = QTabWidget()
        self.separateur = SeparateurResultats(haut, self.onglets)
        layout.addWidget(self.separateur, stretch=1)

        # Graphiques
        graphiques = QWidget()
        g = QHBoxLayout(graphiques)
        g.setContentsMargins(8, 8, 8, 8)
        self.vue_camembert = QChartView()
        self.vue_barres = QChartView()
        for vue in (self.vue_camembert, self.vue_barres):
            vue.setRenderHint(QPainter.RenderHint.Antialiasing)
            vue.setMinimumHeight(180)
        g.addWidget(self.vue_camembert, 2)
        g.addWidget(self.vue_barres, 3)
        self.onglets.addTab(graphiques, "Graphiques")

        # Explications pas à pas
        self.explication = QTextBrowser()
        self.explication.setOpenLinks(False)
        self.explication.setFrameShape(QFrame.Shape.NoFrame)
        self.explication.document().setDocumentMargin(16)
        self.onglets.addTab(self.explication, "Comment c'est calculé")

        # Budget du foyer
        budget = QWidget()
        b = QVBoxLayout(budget)
        b.setContentsMargins(14, 14, 14, 14)
        b.setSpacing(10)
        self.cartes_budget: dict[str, CarteValeur] = {}
        for cle, titre in [
            ("part_revenu", "Part du crédit dans le revenu"),
            ("part_sorties", "Part du crédit dans les dépenses"),
            ("endettement", "Endettement (tous crédits)"),
            ("solde", "Solde du mois"),
        ]:
            self.cartes_budget[cle] = CarteValeur(titre)
        b.addWidget(GrilleCartes([], list(self.cartes_budget.values())))
        self.resume_budget = QLabel()
        self.resume_budget.setObjectName("note")
        self.resume_budget.setWordWrap(True)
        b.addWidget(self.resume_budget)
        self.vue_budget = QChartView()
        self.vue_budget.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.vue_budget.setMinimumHeight(200)
        b.addWidget(self.vue_budget, 1)
        self.onglets.addTab(budget, "Budget")

        # Comparaison de durées
        comparaison = QWidget()
        c = QVBoxLayout(comparaison)
        c.setContentsMargins(0, 0, 0, 10)
        self.table_comparaison = QTableWidget()
        self.table_comparaison.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table_comparaison.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table_comparaison.verticalHeader().setVisible(False)
        self.table_comparaison.setShowGrid(False)
        self.table_comparaison.verticalHeader().setDefaultSectionSize(36)
        self.table_comparaison.setFrameShape(QFrame.Shape.NoFrame)
        self.table_comparaison.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table_comparaison.cellDoubleClicked.connect(
            lambda ligne, _: self.duree_choisie.emit(self._durees_comparaison[ligne])
        )
        self._durees_comparaison: list[int] = []
        c.addWidget(self.table_comparaison)
        aide = QLabel("Double-cliquez sur une ligne pour retenir cette durée. La ligne en gras est la simulation en cours.")
        aide.setObjectName("note")
        aide.setWordWrap(True)
        aide.setContentsMargins(14, 0, 14, 0)
        c.addWidget(aide)
        self.onglets.addTab(comparaison, "Comparer les durées")

        # Tableau d'amortissement
        tableau = QWidget()
        t = QVBoxLayout(tableau)
        t.setContentsMargins(0, 0, 0, 10)
        self.modele = ModeleAmortissement()
        self.vue_tableau = QTableView()
        self.vue_tableau.setModel(self.modele)
        self.vue_tableau.setAlternatingRowColors(True)
        self.vue_tableau.verticalHeader().setVisible(False)
        self.vue_tableau.setShowGrid(False)
        self.vue_tableau.verticalHeader().setDefaultSectionSize(32)
        self.vue_tableau.setFrameShape(QFrame.Shape.NoFrame)
        self.vue_tableau.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.addWidget(self.vue_tableau)
        legende_bascule = QLabel(
            "Ligne surlignée en jaune : point de bascule, première échéance où l'on rembourse "
            "plus de capital que d'intérêts."
        )
        legende_bascule.setObjectName("note")
        legende_bascule.setWordWrap(True)
        bouton_export = QPushButton("Exporter en CSV…")
        bouton_export.setCursor(Qt.CursorShape.PointingHandCursor)
        bouton_export.clicked.connect(self.exporter_csv)
        pied = QHBoxLayout()
        pied.setContentsMargins(14, 0, 14, 0)
        pied.addWidget(legende_bascule, 1)
        pied.addWidget(bouton_export)
        t.addLayout(pied)
        self.onglets.addTab(tableau, "Tableau d'amortissement")

    def afficher(self, scenario: Scenario, comparaison: list[Scenario]) -> None:
        r = scenario.resultat
        indicateurs = scenario.indicateurs
        self.resultat = r
        crd = r.assurance_sur_crd and r.taux_assurance > 0
        self.cartes["mensualite"].titre.setText(
            "Mensualité max. (1re échéance)" if crd else "Mensualité (assurance incluse)"
        )
        self.cartes["assurance_m"].titre.setText(
            "Assurance 1er mois (puis décroissante)" if crd else "Assurance / mois"
        )
        valeurs = {
            "mensualite": eur(r.mensualite_totale),
            "taeg": pct(r.taeg),
            "cout": eur(r.cout_total),
            "capital": eur(r.capital),
            "mensualite_ha": eur(r.mensualite_hors_assurance),
            "assurance_m": eur(r.assurance_mensuelle),
            "interets": eur(r.cout_interets),
            "assurance": eur(r.cout_assurance),
            "frais": eur(r.frais),
            "total_du": eur(r.montant_total_du),
        }
        for cle, texte in valeurs.items():
            self.cartes[cle].valeur.setText(texte)

        lignes = []
        for ind in indicateurs:
            valeur = f"<b>{ind.valeur}</b>"
            if ind.couleur:
                valeur = f"<b style='color:{ind.couleur}'>{ind.valeur}</b>"
            lignes.append(f"{ind.libelle} : {valeur}")
        self.zone_indicateurs.setText("<br>".join(lignes))
        self.zone_indicateurs.setVisible(bool(lignes))
        self.separateur.ajuster_plus_tard()  # le nombre de lignes d'indicateurs varie selon le crédit

        self.modele.definir(r)
        self._dessiner_camembert(r)
        self._dessiner_barres(r)
        self._remplir_comparaison(r, comparaison)
        self._afficher_budget(scenario.budget)
        defilement = self.explication.verticalScrollBar().value()
        self.explication.setHtml(expliquer(
            r,
            etapes_montant=scenario.etapes_montant,
            mensualite_cible=scenario.mensualite_cible,
            budget=scenario.budget,
            endettement_max=ENDETTEMENT_MAX,
            comparaison=[s.resultat for s in comparaison],
        ))
        self.explication.verticalScrollBar().setValue(defilement)

    def _afficher_budget(self, b: Budget | None) -> None:
        if b is None or b.revenus <= 0:
            for carte in self.cartes_budget.values():
                carte.valeur.setText("—")
            self.resume_budget.setText("Renseignez les revenus du foyer pour voir la place du crédit dans le budget.")
            self.vue_budget.setChart(self._nouveau_graphique(""))
            return
        couleur_solde = COULEUR_OK if b.solde >= 0 else COULEUR_ALERTE
        couleur_endettement = COULEUR_OK if b.endettement <= ENDETTEMENT_MAX else COULEUR_ALERTE
        valeurs = {
            "part_revenu": (pct(b.part_credit_revenu), None),
            "part_sorties": (pct(b.part_credit_sorties), None),
            "endettement": (pct(b.endettement), couleur_endettement),
            "solde": (eur(b.solde, 0), couleur_solde),
        }
        for cle, (texte, couleur) in valeurs.items():
            label = self.cartes_budget[cle].valeur
            label.setText(texte)
            label.setStyleSheet(f"color: {couleur};" if couleur else "")
        self.resume_budget.setText(
            f"Revenus {eur(b.revenus, 0)} · crédits {eur(b.total_credits, 0)} · "
            f"dépenses courantes {eur(b.total_depenses, 0)} · total des sorties {eur(b.total_sorties, 0)}"
        )
        self._dessiner_budget(b)

    def _dessiner_budget(self, b: Budget) -> None:
        lignes = [("Crédit simulé", b.mensualite_credit, "credit")]
        if b.autres_credits > 0:
            lignes.append(("Autres crédits", b.autres_credits, "autres"))
        lignes += [(nom, v, "depense") for nom, v in b.depenses.items() if v > 0]
        if b.solde >= 0:
            lignes.append(("Reste disponible", b.solde, "reste"))
        else:
            lignes.append(("Déficit", -b.solde, "deficit"))
        lignes.reverse()  # un graphique horizontal dessine la 1re catégorie en bas
        groupes = [
            ("Crédit simulé", "credit", COULEUR_CAPITAL),
            ("Autres crédits", "autres", COULEUR_INTERETS),
            ("Dépenses courantes", "depense", COULEUR_DEPENSES),
            ("Reste disponible", "reste", COULEUR_ASSURANCE),
            ("Déficit", "deficit", QColor(COULEUR_ALERTE)),
        ]
        serie = QHorizontalStackedBarSeries()
        serie.setBarWidth(0.65)
        for nom, groupe, couleur in groupes:
            if not any(l[2] == groupe for l in lignes):
                continue
            jeu = QBarSet(nom)
            jeu.setColor(couleur)
            jeu.setBorderColor(couleur)
            for _, valeur, g in lignes:
                jeu.append(valeur if g == groupe else 0)
            serie.append(jeu)
        chart = self._nouveau_graphique("Où va le revenu chaque mois (en % du revenu)")
        chart.addSeries(serie)
        axe_y = QBarCategoryAxis()
        axe_y.append([f"{nom}  {b.part_du_revenu(v):.0f} %" for nom, v, _ in lignes])
        axe_y.setTruncateLabels(False)
        axe_x = QValueAxis()
        axe_x.setRange(0, max(v for _, v, _ in lignes) * 1.05)
        axe_x.setLabelFormat("%.0f")
        axe_x.setTitleText("€ par mois")
        axe_x.applyNiceNumbers()
        chart.addAxis(axe_y, Qt.AlignmentFlag.AlignLeft)
        chart.addAxis(axe_x, Qt.AlignmentFlag.AlignBottom)
        serie.attachAxis(axe_y)
        serie.attachAxis(axe_x)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        self._styliser(chart)
        self.vue_budget.setChart(chart)

    def _remplir_comparaison(self, courant: ResultatCredit, comparaison: list[Scenario]) -> None:
        avec_endettement = any(s.endettement is not None for s in comparaison)
        colonnes = ["Durée", "Taux", "Montant emprunté", "Mensualité", "Coût total", "TAEG"]
        if avec_endettement:
            colonnes.append("Endettement")
        t = self.table_comparaison
        t.clear()
        t.setColumnCount(len(colonnes))
        t.setHorizontalHeaderLabels(colonnes)
        t.setRowCount(len(comparaison))
        self._durees_comparaison = [s.resultat.duree_mois for s in comparaison]
        gras = QFont(t.font())
        gras.setBold(True)
        surlignage = QBrush(QColor("#eaf1fe"))
        for ligne, s in enumerate(comparaison):
            r = s.resultat
            cellules = [
                duree_texte(r.duree_mois),
                pct(r.taux_annuel),
                eur(r.capital, 0),
                eur(r.mensualite_totale),
                eur(r.cout_total, 0),
                pct(r.taeg),
            ]
            if avec_endettement:
                cellules.append(pct(s.endettement) if s.endettement is not None else "—")
            courante = r.duree_mois == courant.duree_mois
            for col, texte in enumerate(cellules):
                item = QTableWidgetItem(texte)
                item.setTextAlignment(
                    (Qt.AlignmentFlag.AlignLeft if col == 0 else Qt.AlignmentFlag.AlignRight)
                    | Qt.AlignmentFlag.AlignVCenter
                )
                if courante:
                    item.setFont(gras)
                    item.setBackground(surlignage)
                if col == 6 and s.endettement is not None and s.endettement > ENDETTEMENT_MAX:
                    item.setForeground(QBrush(QColor(COULEUR_ALERTE)))
                t.setItem(ligne, col, item)

    def _dessiner_camembert(self, r: ResultatCredit) -> None:
        serie = QPieSeries()
        serie.setHoleSize(0.55)
        serie.setPieSize(0.82)
        parts = [
            ("Capital", r.capital, COULEUR_CAPITAL),
            ("Intérêts", r.cout_interets, COULEUR_INTERETS),
            ("Assurance", r.cout_assurance, COULEUR_ASSURANCE),
            ("Frais", r.frais, COULEUR_FRAIS),
        ]
        total = sum(v for _, v, _ in parts) or 1
        for nom, valeur, couleur in parts:
            if valeur <= 0:
                continue
            tranche = serie.append(f"{nom} {valeur / total * 100:.0f} %", valeur)
            tranche.setColor(couleur)
            tranche.setBorderColor(QColor("white"))
            tranche.setBorderWidth(2)
        chart = self._nouveau_graphique("Répartition du montant total dû")
        chart.addSeries(serie)
        legende = chart.legend()
        legende.setAlignment(Qt.AlignmentFlag.AlignRight)
        police = QFont(legende.font())
        police.setPointSizeF(police.pointSizeF() * 0.85)
        legende.setFont(police)
        self._styliser(chart)
        self.vue_camembert.setChart(chart)

    def _dessiner_barres(self, r: ResultatCredit) -> None:
        annuel = r.par_annee()
        jeux = [
            ("Capital", COULEUR_CAPITAL, 1),
            ("Intérêts", COULEUR_INTERETS, 2),
            ("Assurance", COULEUR_ASSURANCE, 3),
        ]
        serie = QStackedBarSeries()
        for nom, couleur, col in jeux:
            if col == 3 and r.cout_assurance <= 0:
                continue
            jeu = QBarSet(nom)
            jeu.setColor(couleur)
            jeu.setBorderColor(couleur)
            for ligne in annuel:
                jeu.append(ligne[col])
            serie.append(jeu)
        maximum = max((a[1] + a[2] + a[3] for a in annuel), default=0)
        chart = self._nouveau_graphique("Remboursements par année (en €)")
        chart.addSeries(serie)
        axe_x = QBarCategoryAxis()
        # Au-delà de 12 ans, une étiquette sur cinq (les catégories doivent rester uniques).
        axe_x.append([
            str(an) if len(annuel) <= 12 or an == 1 or an % 5 == 0 else " " * an
            for an, *_ in annuel
        ])
        axe_x.setTitleText("Année")
        axe_x.setTruncateLabels(False)
        axe_y = QValueAxis()
        axe_y.setRange(0, maximum * 1.08 or 1)
        axe_y.setLabelFormat("%.0f")
        axe_y.applyNiceNumbers()
        chart.addAxis(axe_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axe_y, Qt.AlignmentFlag.AlignLeft)
        serie.attachAxis(axe_x)
        serie.attachAxis(axe_y)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        serie.setBarWidth(0.6)
        self._styliser(chart)
        self.vue_barres.setChart(chart)

    def _nouveau_graphique(self, titre: str) -> QChart:
        return nouveau_graphique(titre)

    @staticmethod
    def _styliser(chart: QChart) -> None:
        styliser(chart)

    def exporter_csv(self) -> None:
        if self.resultat is None:
            return
        chemin, _ = QFileDialog.getSaveFileName(
            self, "Exporter le tableau d'amortissement", "amortissement.csv", "CSV (*.csv)"
        )
        if not chemin:
            return

        def num(v: float) -> str:  # format compatible Excel français
            return f"{v:.2f}".replace(".", ",")

        try:
            with open(chemin, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f, delimiter=";")
                w.writerow(ModeleAmortissement.COLONNES)
                for e in self.resultat.tableau:
                    w.writerow(
                        [e.numero, num(e.mensualite), num(e.interets), num(e.capital),
                         num(e.assurance), num(e.capital_restant)]
                    )
        except OSError as err:
            QMessageBox.critical(self, "Export impossible", str(err))


# --------------------------------------------------------------------------- écran


MODE_MONTANT, MODE_MENSUALITE = 0, 1


class EcranSimulation(QWidget):
    """Formulaire à gauche (adapté au type de crédit choisi), résultats à droite."""

    def __init__(self):
        super().__init__()
        self._chargement = False
        self.formulaire = self._nouveau_formulaire()

        # Les QComboBox restent la source de vérité ; ils sont affichés sous forme de boutons segmentés.
        self.type_credit = QComboBox(self)
        for cle, profil in PROFILS.items():
            self.type_credit.addItem(profil.libelle, cle)
        self.type_credit.hide()
        self.mode = QComboBox(self)
        self.mode.addItems(["Le montant", "La mensualité"])
        self.mode.hide()

        self.section(self.formulaire, "Projet")
        self.ajouter("Je pars de", Segmente(self.mode))

        self.montant = self.ajouter("Montant", champ_montant(0))
        self.mensualite_souhaitee = self.ajouter(
            "Mensualité souhaitée", champ_montant(0, 100_000, 10), "Assurance comprise"
        )
        self.type_bien = QComboBox()
        self.type_bien.addItems(list(TAUX_NOTAIRE))
        self.ajouter("Type de bien", self.type_bien)
        self.notaire = self.ajouter(
            "Frais de notaire", champ_taux(7.5, 15, 0.1), "En % du prix ; ajusté selon le type de bien"
        )
        self.type_bien.currentTextChanged.connect(lambda t: self.notaire.setValue(TAUX_NOTAIRE[t]))
        self.travaux = self.ajouter("Travaux", champ_montant(0, 5_000_000, 1_000))
        self.apport = self.ajouter("Apport personnel", champ_montant(0, 10_000_000, 500))
        self.reprise = self.ajouter(
            "Reprise ancien véhicule", champ_montant(0, 500_000, 500), "Valeur de reprise déduite du prix"
        )
        self.section(self.formulaire, "Durée et taux")
        self.duree_mois = self.ajouter("Durée", champ_duree(48, 3, 120, " mois"))
        self.duree_ans = self.ajouter("Durée", champ_duree(20, 5, 30, " ans"))

        self.taux = champ_taux(0, 25, 0.05)
        self.taux_reference = QCheckBox("Réf.")
        self.taux_reference.setChecked(True)
        ligne_taux = QWidget()
        lt = QHBoxLayout(ligne_taux)
        lt.setContentsMargins(0, 0, 0, 0)
        lt.addWidget(self.taux, 1)
        lt.addWidget(self.taux_reference)
        self.ajouter("Taux nominal annuel", ligne_taux)

        self.section(self.formulaire, "Assurance et frais")
        self.assurance = self.ajouter(
            "Assurance emprunteur", champ_taux(0, 5, 0.01), "Taux annuel de l'assurance"
        )
        self.base_assurance = QComboBox()
        self.base_assurance.addItems(["Capital initial", "Capital restant dû"])
        self.base_assurance.setToolTip(
            "Capital initial : même montant chaque mois (assurance groupe des banques).\n"
            "Capital restant dû : montant qui baisse au fil du remboursement (souvent en délégation)."
        )
        self.ajouter("Assurance calculée sur", self.base_assurance)
        self.frais_dossier = self.ajouter("Frais de dossier", champ_montant(0, 20_000, 50))
        self.garantie = self.ajouter(
            "Garantie", champ_taux(1.0, 5, 0.1), "Caution ou hypothèque, en % du capital emprunté"
        )
        self.specifiques: dict[str, QWidget] = {
            "type_bien": self.type_bien,
            "notaire": self.notaire,
            "travaux": self.travaux,
            "apport": self.apport,
            "reprise": self.reprise,
            "duree_mois": self.duree_mois,
            "duree_ans": self.duree_ans,
            "garantie": self.garantie,
        }

        self.boite = QWidget()
        self.boite.setLayout(self.formulaire)

        form_budget = self._nouveau_formulaire()
        self.section(form_budget, "Budget du foyer (par mois)")
        self.revenus = champ_montant(4_500, 1_000_000, 100)
        form_budget.addRow("Revenus nets du foyer", self.revenus)
        self.charges = champ_montant(0, 1_000_000, 50)
        form_budget.addRow("Autres crédits en cours", self.charges)
        self.section(form_budget, "Dépenses courantes")
        self.postes: dict[str, QDoubleSpinBox] = {}
        for libelle, defaut in POSTES_BUDGET:
            self.postes[libelle] = champ_montant(defaut, 1_000_000, 10)
            form_budget.addRow(libelle, self.postes[libelle])
        self.boite_budget = QWidget()
        self.boite_budget.setLayout(form_budget)
        self.note_budget = QLabel(
            "Achat de résidence principale : retirez le loyer actuel du poste Logement "
            "(gardez les charges, la taxe foncière…)."
        )
        self.note_budget.setObjectName("note")
        self.note_budget.setWordWrap(True)
        self.note_taux = QLabel()
        self.note_taux.setObjectName("note")
        self.note_taux.setWordWrap(True)
        self.message = QLabel()
        self.message.setWordWrap(True)
        self.message.setObjectName("message")
        self.message.hide()
        gauche = QWidget()
        gauche.setObjectName("contenuLateral")
        g = QVBoxLayout(gauche)
        g.setContentsMargins(20, 8, 20, 20)
        g.setSpacing(10)
        g.addWidget(self.boite)
        g.addWidget(self.note_taux)
        g.addWidget(self.message)
        g.addWidget(self.boite_budget)
        g.addWidget(self.note_budget)
        g.addStretch()
        defilement = QScrollArea()
        defilement.setObjectName("barreLaterale")
        defilement.setWidget(gauche)
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QFrame.Shape.NoFrame)
        defilement.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        defilement.setMinimumWidth(300)

        self.resultats = PanneauResultats()
        self.resultats.duree_choisie.connect(self.choisir_duree)
        separateur = QSplitter()
        separateur.setHandleWidth(1)
        separateur.setChildrenCollapsible(False)
        self.separateur_principal = separateur
        separateur.addWidget(defilement)
        separateur.addWidget(self.resultats)
        separateur.setStretchFactor(1, 1)
        separateur.setSizes([440, 960])
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(separateur)
        self._aligner_libelles(self.formulaire, form_budget)

        for type_champ in (QDoubleSpinBox, QSpinBox):
            for champ in self.findChildren(type_champ):
                champ.valueChanged.connect(self.recalculer)
        for combo in (self.type_bien, self.base_assurance):
            combo.currentIndexChanged.connect(self.recalculer)
        self.mode.currentIndexChanged.connect(self.maj_visibilite)
        self.mode.currentIndexChanged.connect(self.recalculer)
        self.taux_reference.toggled.connect(self.recalculer)
        self.type_credit.currentIndexChanged.connect(lambda: self.appliquer_profil(self.cle))
        self.appliquer_profil(self.cle)

    @property
    def cle(self) -> str:
        return self.type_credit.currentData()

    @property
    def par_mensualite(self) -> bool:
        return self.mode.currentIndex() == MODE_MENSUALITE

    @staticmethod
    def _nouveau_formulaire() -> QFormLayout:
        f = QFormLayout()
        f.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.AllNonFixedFieldsGrow)
        f.setLabelAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # Panneau étroit : le libellé passe au-dessus du champ plutôt que de l'écraser
        f.setRowWrapPolicy(QFormLayout.RowWrapPolicy.WrapLongRows)
        f.setHorizontalSpacing(14)
        f.setVerticalSpacing(10)
        f.setContentsMargins(0, 0, 0, 0)
        return f

    @staticmethod
    def _aligner_libelles(*formulaires: QFormLayout) -> None:
        """Même largeur de colonne de libellés pour toutes les sections du panneau latéral."""
        libelles = [
            item.widget()
            for f in formulaires
            for ligne in range(f.rowCount())
            if (item := f.itemAt(ligne, QFormLayout.ItemRole.LabelRole)) and item.widget()
        ]
        largeur = max(l.sizeHint().width() for l in libelles)
        for l in libelles:
            l.setFixedWidth(largeur)

    @staticmethod
    def section(formulaire: QFormLayout, titre: str) -> None:
        """Intertitre de section dans le panneau latéral."""
        label = QLabel(titre.upper())
        label.setObjectName("titreSection")
        formulaire.addRow(label)

    def ajouter(self, libelle: str, champ: QWidget, aide: str | None = None) -> QWidget:
        if aide:
            champ.setToolTip(aide)
        self.formulaire.addRow(libelle, champ)
        return champ

    def maj_visibilite(self) -> None:
        champs = PROFILS[self.cle].champs
        for nom, champ in self.specifiques.items():
            self.formulaire.setRowVisible(champ, nom in champs)
        self.formulaire.setRowVisible(self.montant, not self.par_mensualite)
        self.formulaire.setRowVisible(self.mensualite_souhaitee, self.par_mensualite)
        self.note_budget.setVisible(self.cle == "immo")

    def appliquer_profil(self, cle: str) -> None:
        """Affiche les champs du type choisi et remplit ses valeurs par défaut."""
        p = PROFILS[cle]
        self._chargement = True
        try:
            self.maj_visibilite()
            self.formulaire.labelForField(self.montant).setText(p.libelle_montant)
            self.montant.setRange(0, p.montant_max)
            self.montant.setSingleStep(p.pas_montant)
            self.montant.setValue(p.montant)
            self.mensualite_souhaitee.setValue(p.mensualite)
            self.apport.setValue(p.apport)
            (self.duree_ans if cle == "immo" else self.duree_mois).setValue(p.duree)
            self.assurance.setValue(p.assurance)
            self.frais_dossier.setValue(p.frais_dossier)
            self.taux_reference.setChecked(True)
            self.taux_reference.setToolTip(f"Utiliser le taux de référence du marché\nSource : {p.source_taux}")
        finally:
            self._chargement = False
        self.recalculer()

    def choisir_duree(self, duree_mois: int) -> None:
        if self.cle == "immo":
            self.duree_ans.setValue(duree_mois // 12)
        else:
            self.duree_mois.setValue(duree_mois)

    def duree_courante(self) -> int:
        return self.duree_ans.value() * 12 if self.cle == "immo" else self.duree_mois.value()

    def taux_pour(self, duree_mois: int) -> float:
        """Taux de la grille de référence (arrondi comme à l'affichage) ou taux saisi."""
        return scenarios.taux_pour(self.cle, duree_mois, self.taux.value(), self.taux_reference.isChecked())

    def recalculer(self) -> None:
        if self._chargement:
            return
        profil = PROFILS[self.cle]
        duree = self.duree_courante()
        reference = self.taux_reference.isChecked()
        self.taux.setEnabled(not reference)
        if reference:
            self.taux.blockSignals(True)
            self.taux.setValue(self.taux_pour(duree))
            self.taux.blockSignals(False)
            self.note_taux.setText(f"Taux de référence (case « Réf. ») : {profil.source_taux}. Décochez pour saisir votre propre taux.")
        else:
            self.note_taux.setText("Taux saisi, appliqué à toutes les durées de la comparaison.")

        try:
            scenario = self.calculer(duree, self.taux_pour(duree))
        except ValueError as err:
            self.message.setText(str(err))
            self.message.show()
            return
        comparaison = scenarios.comparer_durees(
            self.cle, self.parametres(), duree, self.taux.value(), self.taux_reference.isChecked()
        )
        self.message.setText("<br>".join(f"⚠ {a}" for a in scenario.avertissements))
        self.message.setVisible(bool(scenario.avertissements))
        self.resultats.afficher(scenario, comparaison)

    # ----------------------------------------------------------------- calculs (module scenarios)

    def parametres(self) -> Parametres:
        return Parametres(
            par_mensualite=self.par_mensualite,
            montant=self.montant.value(),
            mensualite_souhaitee=self.mensualite_souhaitee.value(),
            apport=self.apport.value(),
            reprise=self.reprise.value(),
            travaux=self.travaux.value(),
            notaire=self.notaire.value(),
            assurance=self.assurance.value(),
            assurance_sur_crd=self.base_assurance.currentIndex() == 1,
            frais_dossier=self.frais_dossier.value(),
            garantie=self.garantie.value(),
            revenus=self.revenus.value(),
            charges=self.charges.value(),
            depenses={libelle: champ.value() for libelle, champ in self.postes.items()},
        )

    def calculer(self, duree_mois: int, taux: float) -> Scenario:
        return scenarios.calculer(self.cle, self.parametres(), duree_mois, taux)


# --------------------------------------------------------------------------- fenêtre

CHEVRON = (Path(__file__).parent / "assets" / "chevron-down.svg").as_posix()
LOGO = (Path(__file__).parent / "assets" / "logo.png").as_posix()  # généré par outils/generer_icones.py

STYLE = """
QMainWindow, QWidget#central { background: #f5f6f8; }
QWidget { color: #111827; font-size: 13px; }
QToolTip {
    background: #111827; color: white; border: none; padding: 6px 8px; border-radius: 6px;
}

/* En-tête */
QFrame#entete { background: white; border-bottom: 1px solid #e6e8ec; }
QLabel#titreApp { font-size: 15px; font-weight: 600; }
QLabel#badge {
    background: #eff6ff; color: #1d4ed8; border-radius: 9px; padding: 2px 9px;
    font-size: 11px; font-weight: 600;
}
QLabel#avertissement { color: #6b7280; font-size: 11px; }

/* Boutons segmentés */
QFrame#segmente { background: #eef0f3; border-radius: 8px; }
QPushButton#segment {
    background: transparent; border: none; border-radius: 6px;
    padding: 6px 14px; color: #4b5563; font-weight: 500;
}
QPushButton#segment:hover { color: #111827; }
QPushButton#segment:checked { background: white; color: #111827; border: 1px solid #e3e6ea; }

/* Panneau latéral */
QScrollArea#barreLaterale, QWidget#contenuLateral { background: white; border: none; }
QLabel#titreSection {
    color: #6b7280; font-size: 11px; font-weight: 600; letter-spacing: 0.6px;
    padding-top: 14px; padding-bottom: 2px;
}
QLabel#note { color: #6b7280; font-size: 12px; }
QLabel#message {
    background: #fef2f2; color: #991b1b; border: 1px solid #fecaca;
    border-radius: 8px; padding: 8px 10px; font-size: 12px;
}
QSplitter::handle { background: #e6e8ec; }
QSplitter::handle:vertical { background: transparent; }

QScrollArea#zoneCartes, QWidget#contenuCartes,
QScrollArea#zoneCartes > QWidget#qt_scrollarea_viewport { background: transparent; border: none; }

/* Champs */
QAbstractSpinBox, QComboBox {
    background: white; border: 1px solid #d6d9df; border-radius: 6px;
    padding: 4px 8px; min-height: 24px; max-height: 24px; selection-background-color: #bfdbfe; selection-color: #111827;
}
QAbstractSpinBox:hover, QComboBox:hover { border-color: #b8bec7; }
QAbstractSpinBox:focus, QComboBox:focus { border: 1px solid #2563eb; }
QAbstractSpinBox:disabled { background: #f3f4f6; color: #9ca3af; border-color: #e5e7eb; }
/* Flèches masquées par la feuille de style : avec NoButtons, Qt réduit le texte à 1 px de large */
QAbstractSpinBox::up-button, QAbstractSpinBox::down-button { width: 0; border: none; image: none; }
QComboBox::drop-down { border: none; width: 24px; }
QComboBox::down-arrow { image: url({CHEVRON}); width: 12px; height: 12px; }
QComboBox QAbstractItemView {
    background: white; border: 1px solid #e6e8ec; border-radius: 6px; padding: 4px;
    selection-background-color: #eff6ff; selection-color: #111827; outline: none;
}
QCheckBox { spacing: 6px; color: #374151; }

QPushButton {
    background: white; border: 1px solid #d6d9df; border-radius: 6px; padding: 6px 12px; color: #111827;
}
QPushButton:hover { background: #f9fafb; border-color: #b8bec7; }
QPushButton:pressed { background: #f3f4f6; }

/* Cartes de résultats */
QFrame#carte, QFrame#carteMiseEnAvant {
    background: white; border: 1px solid #e6e8ec; border-radius: 10px;
}
QLabel#carteTitre { color: #6b7280; font-size: 12px; }
QLabel#carteValeur { font-size: 16px; font-weight: 600; }
QLabel#carteValeurGrande { font-size: 23px; font-weight: 700; color: #2563eb; }
QLabel#indicateurs {
    background: white; border: 1px solid #e6e8ec; border-radius: 10px;
    padding: 10px 14px; line-height: 150%;
}

/* Onglets soulignés */
QTabWidget::pane {
    background: white; border: 1px solid #e6e8ec; border-radius: 10px; top: -1px;
}
QTabWidget::tab-bar { alignment: left; }
QTabBar::tab {
    background: transparent; border: none; border-bottom: 2px solid transparent;
    padding: 8px 4px; margin-right: 18px; color: #6b7280; font-weight: 500;
}
QTabBar::tab:hover { color: #374151; }
QTabBar::tab:selected { color: #111827; border-bottom: 2px solid #2563eb; }

/* Tableaux */
QTableView {
    background: white; border: none; alternate-background-color: #fafbfc;
    selection-background-color: #eaf1fe; selection-color: #111827;
}
QTableView::item { padding: 0 10px; }
QHeaderView::section {
    background: white; border: none; border-bottom: 1px solid #e6e8ec;
    padding: 8px 10px; color: #6b7280; font-weight: 600; font-size: 12px;
}
QTextBrowser { background: white; border: none; }
QChartView { background: white; border: none; }

/* Barres de défilement fines */
QScrollBar:vertical { background: transparent; width: 10px; margin: 2px; }
QScrollBar:horizontal { background: transparent; height: 10px; margin: 2px; }
QScrollBar::handle { background: #cfd4da; border-radius: 3px; }
QScrollBar::handle:vertical { min-height: 32px; }
QScrollBar::handle:horizontal { min-width: 32px; }
QScrollBar::handle:hover { background: #b0b7c0; }
QScrollBar::add-line, QScrollBar::sub-line { width: 0; height: 0; }
QScrollBar::add-page, QScrollBar::sub-page { background: none; }
""".replace("{CHEVRON}", CHEVRON)


def palette_claire() -> QPalette:
    p = QPalette()
    couleurs = {
        QPalette.ColorRole.Window: "#f5f6f8",
        QPalette.ColorRole.WindowText: "#111827",
        QPalette.ColorRole.Base: "#ffffff",
        QPalette.ColorRole.AlternateBase: "#fafbfc",
        QPalette.ColorRole.Text: "#111827",
        QPalette.ColorRole.Button: "#ffffff",
        QPalette.ColorRole.ButtonText: "#111827",
        QPalette.ColorRole.Highlight: ACCENT,
        QPalette.ColorRole.HighlightedText: "#ffffff",
        QPalette.ColorRole.ToolTipBase: "#111827",
        QPalette.ColorRole.ToolTipText: "#ffffff",
        QPalette.ColorRole.PlaceholderText: "#9ca3af",
        QPalette.ColorRole.Mid: "#e6e8ec",
    }
    for role, couleur in couleurs.items():
        p.setColor(role, QColor(couleur))
    return p


class FenetrePrincipale(QMainWindow):
    def __init__(self):
        super().__init__()
        from simu_credit import __version__
        from simu_credit.ecran_epargne import EcranEpargne  # import local : ecran_epargne importe ce module

        self.setWindowTitle("Simulateur de crédit et d'épargne — outil pédagogique")
        self.ecran = EcranSimulation()
        self.ecran_epargne = EcranEpargne()
        for ecran in (self.ecran, self.ecran_epargne):
            separateur = ecran.separateur_principal
            separateur.splitterMoved.connect(lambda *_, s=separateur: s.setProperty("manuel", True))
        self.pages = QStackedWidget()
        self.pages.addWidget(self.ecran)
        self.pages.addWidget(self.ecran_epargne)
        self.activite = QComboBox(self)
        self.activite.addItems(["Crédit", "Épargne"])
        self.activite.hide()

        entete = QFrame()
        entete.setObjectName("entete")
        e = QHBoxLayout(entete)
        e.setContentsMargins(20, 12, 20, 12)
        e.setSpacing(10)
        logo = QLabel()
        logo.setPixmap(QIcon(LOGO).pixmap(QSize(32, 32), self.devicePixelRatioF()))
        logo.setToolTip("Simulateur de crédit et d'épargne")
        titre = LibelleSouple("Simulateur de crédit et d'épargne")
        titre.setObjectName("titreApp")
        badge = LibelleSouple("Outil pédagogique")
        badge.setObjectName("badge")
        avertissement = LibelleSouple(f"Outil d'enseignement · ni offre, ni conseil financier · v{__version__}")
        avertissement.setObjectName("avertissement")
        avertissement.setToolTip(
            "Les résultats ne constituent ni une offre de prêt ou de placement, ni un conseil financier ; "
            "les taux de référence sont des exemples datés."
        )
        # Textes secondaires masqués, dans cet ordre, quand la fenêtre est étroite (voir resizeEvent)
        self._facultatifs = [titre, badge, avertissement]
        self._entete = e
        e.addWidget(logo)
        e.addWidget(titre)
        e.addWidget(badge)
        e.addStretch(1)
        e.addWidget(Segmente(self.activite))
        types_credit = Segmente(self.ecran.type_credit)
        e.addWidget(types_credit)
        e.addStretch(1)
        self.activite.currentIndexChanged.connect(self.pages.setCurrentIndex)
        self.activite.currentIndexChanged.connect(lambda i: types_credit.setVisible(i == 0))
        e.addWidget(avertissement)

        central = QWidget()
        central.setObjectName("central")
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(entete)
        layout.addWidget(self.pages, 1)
        self.setCentralWidget(central)
        self.setMinimumSize(900, 580)
        self.reglages = QSettings("SimuCredit", "Simulateur")
        self._memoriser = False  # seule la fenêtre ouverte par afficher() enregistre sa taille

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self._adapter_entete()
        # Panneau latéral ≈ 30 % de la largeur (entre 320 et 440 px), tant qu'on ne l'a pas réglé à la main
        laterale = min(440, max(320, int(self.width() * 0.30)))
        for ecran in (self.ecran, self.ecran_epargne):
            separateur = ecran.separateur_principal
            if not separateur.property("manuel"):
                separateur.setSizes([laterale, max(self.width() - laterale, 1)])

    def _adapter_entete(self) -> None:
        """Affiche titre, badge puis avertissement tant qu'ils tiennent dans la largeur."""
        e = self._entete
        marges = e.contentsMargins()
        visibles = [e.itemAt(k).widget() for k in range(e.count()) if e.itemAt(k).widget()]
        obligatoires = [w for w in visibles if w not in self._facultatifs]
        place = self.width() - marges.left() - marges.right() - 40  # 40 : marge entre les blocs
        place -= sum(w.sizeHint().width() + e.spacing() for w in obligatoires)
        for texte in self._facultatifs:
            besoin = texte.sizeHint().width() + e.spacing()
            texte.setVisible(place >= besoin)
            if place >= besoin:
                place -= besoin

    def afficher(self) -> None:
        """Ouvre la fenêtre à une taille adaptée à l'écran (ou à la dernière taille utilisée)."""
        self._memoriser = True
        geometrie = self.reglages.value("geometrie")
        if geometrie is not None and self.restoreGeometry(geometrie):
            self.show()
            return
        ecran = self.screen().availableGeometry()
        if ecran.width() < 1280 or ecran.height() < 760:
            self.showMaximized()  # petit écran : toute la place est utile
            return
        largeur = min(max(int(ecran.width() * 0.85), 1100), 1800)
        hauteur = min(max(int(ecran.height() * 0.88), 680), 1100)
        largeur, hauteur = min(largeur, ecran.width()), min(hauteur, ecran.height())
        self.resize(largeur, hauteur)
        self.move(ecran.center().x() - largeur // 2, ecran.center().y() - hauteur // 2)
        self.show()

    def closeEvent(self, event) -> None:
        if self._memoriser:
            self.reglages.setValue("geometrie", self.saveGeometry())
        super().closeEvent(event)


def appliquer_theme(app: QApplication) -> None:
    """Thème clair unique, rendu identique quel que soit le système (style Fusion + feuille de style)."""
    app.styleHints().setColorScheme(Qt.ColorScheme.Light)
    app.setStyle("Fusion")
    app.setPalette(palette_claire())
    app.setStyleSheet(STYLE)
    app.setWindowIcon(QIcon(LOGO))  # icône de la fenêtre et du Dock / de la barre des tâches


def main() -> None:
    QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France))
    app = QApplication(sys.argv)
    app.setApplicationName("Simulateur de crédit")
    appliquer_theme(app)
    fenetre = FenetrePrincipale()
    fenetre.afficher()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
