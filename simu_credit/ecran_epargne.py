"""Écran « Épargne » : versements réguliers, intérêts composés, fiscalité et inflation."""

from __future__ import annotations

from dataclasses import dataclass

from PySide6.QtCharts import QBarCategoryAxis, QBarSet, QChartView, QLineSeries, QStackedBarSeries, QValueAxis
from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from simu_credit.epargne import (
    ResultatEpargne,
    annee_depassement,
    simuler_epargne,
    versement_pour_objectif,
)
from simu_credit.formats import eur, pct
from simu_credit.gui import (
    COULEUR_ALERTE,
    COULEUR_ASSURANCE,
    COULEUR_CAPITAL,
    COULEUR_OK,
    CarteValeur,
    EcranSimulation,
    GrilleCartes,
    SeparateurResultats,
    Segmente,
    champ_duree,
    champ_montant,
    champ_taux,
    nouveau_graphique,
    styliser,
)
from simu_credit.pedagogie import LEXIQUE_EPARGNE, expliquer_epargne


@dataclass(frozen=True)
class Placement:
    nom: str
    taux: float  # taux annuel brut, en %
    prelevements: float  # impôt + prélèvements sociaux sur les intérêts, en %
    plafond: float | None  # plafond de versements, en €
    source: str
    note: str = ""


# Taux relevés en octobre 2026 ; à mettre à jour périodiquement.
PLACEMENTS = [
    Placement("Livret A", 1.7, 0.0, 22_950, "taux en vigueur depuis le 1er août 2026",
              "Exonéré d'impôt et de prélèvements sociaux."),
    Placement("LDDS", 1.7, 0.0, 12_000, "taux en vigueur depuis le 1er août 2026 (aligné sur le Livret A)",
              "Exonéré d'impôt et de prélèvements sociaux."),
    Placement("LEP", 2.5, 0.0, 10_000, "taux en vigueur depuis le 1er août 2026",
              "Réservé aux foyers aux revenus modestes. Exonéré d'impôt et de prélèvements sociaux."),
    Placement("PEL (ouvert en 2026)", 2.0, 30.0, 61_200, "taux des PEL ouverts depuis le 1er janvier 2026",
              "Intérêts soumis au prélèvement forfaitaire unique de 30 %. Versements limités à 10 ans ; "
              "un PEL dure 15 ans au plus."),
    Placement("Assurance vie, fonds €", 2.63, 17.2, None,
              "rendement moyen 2025 publié par l'ACPR en juin 2026, déjà net des frais de gestion",
              "Prélèvements sociaux de 17,2 % retenus chaque année ; l'impôt sur le revenu, dû seulement "
              "lors d'un retrait, n'est pas simulé."),
    Placement("Personnalisé", 3.0, 30.0, None, "taux et prélèvements saisis librement"),
]
PERSONNALISE = len(PLACEMENTS) - 1
MODE_VERSEMENTS, MODE_OBJECTIF = 0, 1


class EcranEpargne(QWidget):
    """Formulaire à gauche, résultats à droite (même organisation que l'écran crédit)."""

    def __init__(self):
        super().__init__()
        self._chargement = False
        form = EcranSimulation._nouveau_formulaire()

        self.placement = QComboBox()
        for p in PLACEMENTS:
            self.placement.addItem(p.nom)
        self.mode = QComboBox(self)
        self.mode.addItems(["Mes versements", "Mon objectif"])
        self.mode.hide()

        EcranSimulation.section(form, "Placement")
        form.addRow("Placement", self.placement)
        form.addRow("Je pars de", Segmente(self.mode))

        EcranSimulation.section(form, "Versements")
        self.capital_initial = champ_montant(1_000, 10_000_000, 100)
        form.addRow("Capital de départ", self.capital_initial)
        self.versement = champ_montant(100, 100_000, 10)
        form.addRow("Versement mensuel", self.versement)
        self.objectif = champ_montant(20_000, 100_000_000, 1_000)
        form.addRow("Objectif à atteindre", self.objectif)
        self.duree = champ_duree(10, 1, 50, " ans")
        form.addRow("Durée", self.duree)

        EcranSimulation.section(form, "Rendement")
        self.taux = champ_taux(1.7, 20, 0.05)
        form.addRow("Taux annuel brut", self.taux)
        self.prelevements = champ_taux(0, 100, 0.1)
        self.prelevements.setToolTip("Impôt et prélèvements sociaux retenus sur les intérêts")
        form.addRow("Impôt et prélèvements", self.prelevements)
        self.inflation = champ_taux(2.0, 20, 0.1)
        self.inflation.setToolTip(
            "Hausse annuelle des prix supposée sur toute la durée.\n"
            "2 % = objectif de long terme de la BCE ; l'inflation était de 3,1 % sur un an "
            "en septembre 2026 (Insee)."
        )
        form.addRow("Inflation annuelle", self.inflation)
        self.formulaire = form
        EcranSimulation._aligner_libelles(form)

        boite = QWidget()
        boite.setLayout(form)
        self.note = QLabel()
        self.note.setObjectName("note")
        self.note.setWordWrap(True)
        self.message = QLabel()
        self.message.setObjectName("message")
        self.message.setWordWrap(True)
        self.message.hide()
        gauche = QWidget()
        gauche.setObjectName("contenuLateral")
        g = QVBoxLayout(gauche)
        g.setContentsMargins(20, 8, 20, 20)
        g.setSpacing(10)
        g.addWidget(boite)
        g.addWidget(self.note)
        g.addWidget(self.message)
        g.addStretch()
        defilement = QScrollArea()
        defilement.setObjectName("barreLaterale")
        defilement.setWidget(gauche)
        defilement.setWidgetResizable(True)
        defilement.setFrameShape(QFrame.Shape.NoFrame)
        defilement.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        defilement.setMinimumWidth(300)

        self.resultats = PanneauEpargne()
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

        for champ in (self.capital_initial, self.versement, self.objectif, self.taux,
                      self.prelevements, self.inflation, self.duree):
            champ.valueChanged.connect(self.recalculer)
        self.mode.currentIndexChanged.connect(self.maj_visibilite)
        self.mode.currentIndexChanged.connect(self.recalculer)
        self.placement.currentIndexChanged.connect(self.appliquer_placement)
        self.maj_visibilite()
        self.appliquer_placement(0)

    @property
    def par_objectif(self) -> bool:
        return self.mode.currentIndex() == MODE_OBJECTIF

    def maj_visibilite(self) -> None:
        self.formulaire.setRowVisible(self.versement, not self.par_objectif)
        self.formulaire.setRowVisible(self.objectif, self.par_objectif)

    def appliquer_placement(self, index: int) -> None:
        p = PLACEMENTS[index]
        personnalise = index == PERSONNALISE
        self._chargement = True
        try:
            if not personnalise:
                self.taux.setValue(p.taux)
                self.prelevements.setValue(p.prelevements)
            self.taux.setEnabled(personnalise)
            self.prelevements.setEnabled(personnalise)
        finally:
            self._chargement = False
        plafond = f" Plafond de versements : {eur(p.plafond, 0)}." if p.plafond else ""
        self.note.setText(f"{p.nom} : {p.source}.{plafond} {p.note}".strip())
        self.recalculer()

    def simuler(self, placement: Placement | None = None, duree: int | None = None) -> tuple[ResultatEpargne, float | None]:
        """Simulation avec les paramètres saisis (ou ceux d'un autre placement / d'une autre durée).

        Renvoie (résultat, objectif) ; en mode objectif, le versement mensuel est calculé.
        """
        taux = placement.taux if placement else self.taux.value()
        prelev = placement.prelevements if placement else self.prelevements.value()
        duree = duree or self.duree.value()
        c0, inflation = self.capital_initial.value(), self.inflation.value()
        objectif = None
        if self.par_objectif:
            objectif = self.objectif.value()
            versement = versement_pour_objectif(objectif, c0, duree, taux, prelev)
        else:
            versement = self.versement.value()
        return simuler_epargne(c0, versement, duree, taux, prelev, inflation), objectif

    def recalculer(self) -> None:
        if self._chargement:
            return
        r, objectif = self.simuler()
        p = PLACEMENTS[self.placement.currentIndex()]

        avertissements = []
        if p.plafond:
            annee = annee_depassement(r, p.plafond)
            if annee:
                avertissements.append(
                    f"Les versements dépassent le plafond du {p.nom} ({eur(p.plafond, 0)}) "
                    f"dès l'année {annee} : au-delà, il faudrait un autre placement."
                )
        if p.nom.startswith("PEL") and self.duree.value() > 15:
            avertissements.append("Un PEL dure au plus 15 ans.")
        if r.rendement_reel < 0:
            avertissements.append(
                f"Le rendement net ({pct(r.rendement_net)}) est inférieur à l'inflation "
                f"({pct(r.inflation, 1)}) : l'épargne perd du pouvoir d'achat."
            )
        self.message.setText("<br>".join(f"⚠ {a}" for a in avertissements))
        self.message.setVisible(bool(avertissements))

        plus_tot = self.simuler(duree=self.duree.value() + 5)[0] if not self.par_objectif else None
        comparaison = [(pl, *self.simuler(pl)) for pl in PLACEMENTS[:PERSONNALISE]]
        if self.placement.currentIndex() == PERSONNALISE:
            comparaison.append((p, r, objectif))
        self.resultats.afficher(r, objectif, plus_tot, comparaison, p)


class PanneauEpargne(QWidget):
    CARTES = [
        ("final", "Capital final", True),
        ("interets", "Intérêts gagnés (nets)", True),
        ("reel", "Valeur en euros d'aujourd'hui", True),
        ("verse", "Total versé", False),
        ("prelevements", "Impôt et prélèvements", False),
        ("net", "Rendement net / an", False),
        ("reel_an", "Rendement réel / an", False),
    ]
    AIDE = {
        "interets": "Intérêts composés",
        "reel": "Pouvoir d'achat / euros d'aujourd'hui",
        "prelevements": "Prélèvements sociaux et PFU",
        "net": "Taux brut / rendement net",
        "reel_an": "Rendement réel",
    }

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 16, 20, 16)

        self.cartes: dict[str, CarteValeur] = {
            cle: CarteValeur(titre, avant) for cle, titre, avant in self.CARTES
        }
        grille = GrilleCartes(
            [self.cartes[c[0]] for c in self.CARTES if c[2]],
            [self.cartes[c[0]] for c in self.CARTES if not c[2]],
        )
        for cle, terme in self.AIDE.items():
            self.cartes[cle].setToolTip(LEXIQUE_EPARGNE[terme])

        haut = QWidget()
        h = QVBoxLayout(haut)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(10)
        h.addWidget(grille)
        self.indicateurs = QLabel()
        self.indicateurs.setObjectName("indicateurs")
        self.indicateurs.setWordWrap(True)
        self.indicateurs.setTextFormat(Qt.TextFormat.RichText)
        h.addWidget(self.indicateurs)

        self.onglets = QTabWidget()
        self.separateur = SeparateurResultats(haut, self.onglets)
        layout.addWidget(self.separateur, 1)

        page = QWidget()
        pg = QVBoxLayout(page)
        pg.setContentsMargins(8, 8, 8, 8)
        self.vue_graphique = QChartView()
        self.vue_graphique.setRenderHint(QPainter.RenderHint.Antialiasing)
        self.vue_graphique.setMinimumHeight(180)
        pg.addWidget(self.vue_graphique)
        self.onglets.addTab(page, "Graphique")

        self.explication = QTextBrowser()
        self.explication.setFrameShape(QFrame.Shape.NoFrame)
        self.explication.document().setDocumentMargin(16)
        self.onglets.addTab(self.explication, "Comment c'est calculé")

        self.table_placements = self._nouvelle_table()
        page = QWidget()
        pc = QVBoxLayout(page)
        pc.setContentsMargins(0, 0, 0, 10)
        pc.addWidget(self.table_placements)
        aide = QLabel(
            "Mêmes versements et même durée pour chaque placement, aux taux de référence. "
            "La ligne en gras est le placement choisi."
        )
        aide.setObjectName("note")
        aide.setWordWrap(True)
        aide.setContentsMargins(14, 0, 14, 0)
        pc.addWidget(aide)
        self.onglets.addTab(page, "Comparer les placements")

        self.table_annees = self._nouvelle_table()
        self.onglets.addTab(self.table_annees, "Tableau annuel")

    @staticmethod
    def _nouvelle_table() -> QTableWidget:
        t = QTableWidget()
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        t.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        t.verticalHeader().setVisible(False)
        t.verticalHeader().setDefaultSectionSize(34)
        t.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        t.setShowGrid(False)
        t.setAlternatingRowColors(True)
        t.setFrameShape(QFrame.Shape.NoFrame)
        return t

    @staticmethod
    def _remplir(table: QTableWidget, colonnes: list[str], lignes: list[list[str]],
                 gras: int | None = None, rouges: set[tuple[int, int]] = frozenset()) -> None:
        table.clear()
        table.setColumnCount(len(colonnes))
        table.setHorizontalHeaderLabels(colonnes)
        table.setRowCount(len(lignes))
        police = QFont(table.font())
        police.setBold(True)
        for i, ligne in enumerate(lignes):
            for j, texte in enumerate(ligne):
                item = QTableWidgetItem(texte)
                item.setTextAlignment(
                    (Qt.AlignmentFlag.AlignLeft if j == 0 else Qt.AlignmentFlag.AlignRight)
                    | Qt.AlignmentFlag.AlignVCenter
                )
                if i == gras:
                    item.setFont(police)
                    item.setBackground(QBrush(QColor("#eaf1fe")))
                if (i, j) in rouges:
                    item.setForeground(QBrush(QColor(COULEUR_ALERTE)))
                table.setItem(i, j, item)

    def afficher(self, r: ResultatEpargne, objectif, plus_tot, comparaison, placement: Placement) -> None:
        self.resultat = r
        valeurs = {
            "final": eur(r.capital_final),
            "interets": eur(r.interets_nets),
            "reel": eur(r.capital_final_reel),
            "verse": eur(r.total_verse),
            "prelevements": eur(r.prelevements),
            "net": pct(r.rendement_net),
            "reel_an": pct(r.rendement_reel),
        }
        for cle, texte in valeurs.items():
            self.cartes[cle].valeur.setText(texte)
        self.cartes["reel_an"].valeur.setStyleSheet(
            f"color: {COULEUR_ALERTE if r.rendement_reel < 0 else COULEUR_OK};"
        )

        lignes = []
        if objectif is not None:
            lignes.append(
                f"Versement mensuel nécessaire pour atteindre {eur(objectif, 0)} : "
                f"<b style='color:{COULEUR_OK}'>{eur(r.versement_mensuel)}</b>"
            )
        lignes += [
            f"Part des intérêts dans le capital final : <b>{pct(r.part_interets, 1)}</b>",
            f"Gain de pouvoir d'achat par rapport aux sommes versées : "
            f"<b style='color:{COULEUR_OK if r.capital_final_reel >= r.total_verse else COULEUR_ALERTE}'>"
            f"{eur(r.capital_final_reel - r.total_verse, 0)}</b> (en euros d'aujourd'hui)",
        ]
        self.indicateurs.setText("<br>".join(lignes))
        self.separateur.ajuster_plus_tard()

        self._dessiner(r)
        defilement = self.explication.verticalScrollBar().value()
        self.explication.setHtml(expliquer_epargne(r, objectif=objectif, plus_tot=plus_tot))
        self.explication.verticalScrollBar().setValue(defilement)
        self._remplir_placements(comparaison, placement, objectif is not None)
        self._remplir(
            self.table_annees,
            ["Année", "Versements", "Intérêts bruts", "Prélèvements", "Capital au 31/12",
             "Total versé", "Valeur réelle"],
            [[str(a.annee), eur(a.versements), eur(a.interets), eur(a.prelevements), eur(a.capital),
              eur(a.total_verse), eur(a.capital_reel)] for a in r.annees],
        )

    def _remplir_placements(self, comparaison, choisi: Placement, par_objectif: bool) -> None:
        colonne_cle = "Versement nécessaire" if par_objectif else "Capital final"
        lignes, rouges, gras = [], set(), None
        for i, (p, r, _) in enumerate(comparaison):
            if p == choisi:
                gras = i
            depassement = annee_depassement(r, p.plafond) if p.plafond else None
            if depassement:
                rouges.add((i, 7))
            lignes.append([
                p.nom,
                pct(p.taux),
                pct(p.prelevements, 1),
                eur(r.versement_mensuel) if par_objectif else eur(r.capital_final, 0),
                eur(r.interets_nets, 0),
                eur(r.capital_final_reel, 0),
                pct(r.rendement_reel),
                f"dépassé an {depassement}" if depassement else ("—" if not p.plafond else "respecté"),
            ])
        self._remplir(
            self.table_placements,
            ["Placement", "Taux brut", "Prélèvements", colonne_cle, "Intérêts nets",
             "Valeur réelle", "Rendement réel", "Plafond"],
            lignes, gras, rouges,
        )
        self.table_placements.horizontalHeaderItem(5).setToolTip("Capital final en euros d'aujourd'hui")
        for colonne in (0, 7):
            self.table_placements.horizontalHeader().setSectionResizeMode(
                colonne, QHeaderView.ResizeMode.ResizeToContents
            )

    def _dessiner(self, r: ResultatEpargne) -> None:
        versements, interets = QBarSet("Sommes versées"), QBarSet("Intérêts nets cumulés")
        versements.setColor(COULEUR_CAPITAL)
        versements.setBorderColor(COULEUR_CAPITAL)
        interets.setColor(COULEUR_ASSURANCE)
        interets.setBorderColor(COULEUR_ASSURANCE)
        reel = QLineSeries()
        reel.setName("Capital en euros d'aujourd'hui")
        stylo = QPen(QColor("#374151"))
        stylo.setWidthF(2)
        stylo.setStyle(Qt.PenStyle.DashLine)
        reel.setPen(stylo)
        for k, a in enumerate(r.annees):
            versements.append(a.total_verse)
            interets.append(a.capital - a.total_verse)
            reel.append(k, a.capital_reel)
        serie = QStackedBarSeries()
        serie.setBarWidth(0.6)
        serie.append(versements)
        serie.append(interets)

        chart = nouveau_graphique("L'effet boule de neige : capital au 31 décembre de chaque année (en €)")
        chart.addSeries(serie)
        chart.addSeries(reel)
        n = len(r.annees)
        axe_x = QBarCategoryAxis()
        axe_x.append([
            str(a.annee) if n <= 15 or a.annee == 1 or a.annee % 5 == 0 else " " * a.annee
            for a in r.annees
        ])
        axe_x.setTitleText("Année")
        axe_x.setTruncateLabels(False)
        axe_y = QValueAxis()
        axe_y.setRange(0, max(a.capital for a in r.annees) * 1.08 or 1)
        axe_y.setLabelFormat("%.0f")
        axe_y.applyNiceNumbers()
        chart.addAxis(axe_x, Qt.AlignmentFlag.AlignBottom)
        chart.addAxis(axe_y, Qt.AlignmentFlag.AlignLeft)
        for s in (serie, reel):
            s.attachAxis(axe_x)
            s.attachAxis(axe_y)
        chart.legend().setAlignment(Qt.AlignmentFlag.AlignBottom)
        styliser(chart)
        self.vue_graphique.setChart(chart)
