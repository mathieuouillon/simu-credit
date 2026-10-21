"""Calculs financiers d'un prêt amortissable à mensualités constantes.

Module sans dépendance à l'interface graphique, utilisable et testable seul.
Les taux sont exprimés en pourcentage annuel (ex. 3.5 pour 3,5 %).
Le taux mensuel est le taux proportionnel (taux annuel / 12), convention française.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass


@dataclass(frozen=True)
class Echeance:
    numero: int
    mensualite: float  # hors assurance
    interets: float
    capital: float
    assurance: float
    capital_restant: float


@dataclass(frozen=True)
class ResultatCredit:
    capital: float
    duree_mois: int
    taux_annuel: float
    taux_assurance: float
    assurance_sur_crd: bool
    mensualite_hors_assurance: float
    frais: float
    taeg: float
    tableau: list[Echeance]

    @property
    def assurance_mensuelle(self) -> float:
        """Assurance de la 1re échéance (la plus élevée si elle porte sur le capital restant dû)."""
        return self.tableau[0].assurance if self.tableau else 0.0

    @property
    def mensualite_totale(self) -> float:
        """Mensualité assurance incluse de la 1re échéance, donc la plus élevée."""
        return self.mensualite_hors_assurance + self.assurance_mensuelle

    @property
    def cout_interets(self) -> float:
        return sum(e.interets for e in self.tableau)

    @property
    def cout_assurance(self) -> float:
        return sum(e.assurance for e in self.tableau)

    @property
    def cout_total(self) -> float:
        """Coût total du crédit : intérêts + assurance + frais."""
        return self.cout_interets + self.cout_assurance + self.frais

    @property
    def montant_total_du(self) -> float:
        return self.capital + self.cout_total

    def par_annee(self) -> list[tuple[int, float, float, float]]:
        """Agrège le tableau par année : (année, capital, intérêts, assurance)."""
        annees: dict[int, list[float]] = {}
        for e in self.tableau:
            a = annees.setdefault((e.numero - 1) // 12 + 1, [0.0, 0.0, 0.0])
            a[0] += e.capital
            a[1] += e.interets
            a[2] += e.assurance
        return [(an, *vals) for an, vals in sorted(annees.items())]


def mensualite(capital: float, taux_annuel: float, duree_mois: int) -> float:
    """Mensualité constante (hors assurance) d'un prêt amortissable."""
    if duree_mois <= 0:
        raise ValueError("La durée doit être positive")
    if capital <= 0:
        return 0.0
    t = taux_annuel / 100 / 12
    if t == 0:
        return capital / duree_mois
    return capital * t / (1 - (1 + t) ** -duree_mois)


def capital_empruntable(
    mensualite_max: float, taux_annuel: float, duree_mois: int, taux_assurance: float = 0.0
) -> float:
    """Capital maximal empruntable pour une mensualité donnée (assurance comprise).

    Vaut aussi pour une assurance sur capital restant dû : la 1re échéance, la plus
    élevée, porte alors sur le capital entier.
    """
    if mensualite_max <= 0:
        return 0.0
    # Mensualité totale pour 1 € emprunté ; la relation est linéaire en capital.
    par_euro = mensualite(1.0, taux_annuel, duree_mois) + taux_assurance / 100 / 12
    return mensualite_max / par_euro


def taux_reference(grille: Mapping[int, float], duree_mois: int) -> float:
    """Taux d'une grille {durée en mois: taux}, interpolé linéairement entre deux durées."""
    points = sorted(grille.items())
    if duree_mois <= points[0][0]:
        return points[0][1]
    for (d1, t1), (d2, t2) in zip(points, points[1:]):
        if duree_mois <= d2:
            return t1 + (t2 - t1) * (duree_mois - d1) / (d2 - d1)
    return points[-1][1]


def tableau_amortissement(
    capital: float,
    taux_annuel: float,
    duree_mois: int,
    taux_assurance: float = 0.0,
    assurance_sur_crd: bool = False,
) -> list[Echeance]:
    """Tableau d'amortissement mensuel.

    L'assurance porte sur le capital initial (montant fixe) ou, si `assurance_sur_crd`,
    sur le capital restant dû en début de mois (montant décroissant).
    """
    m = mensualite(capital, taux_annuel, duree_mois)
    t = taux_annuel / 100 / 12
    taux_ass_mensuel = taux_assurance / 100 / 12
    restant = capital
    lignes: list[Echeance] = []
    for n in range(1, duree_mois + 1):
        interets = restant * t
        assurance = (restant if assurance_sur_crd else capital) * taux_ass_mensuel
        part_capital = m - interets
        if n == duree_mois:  # absorbe les erreurs d'arrondi sur la dernière échéance
            part_capital = restant
        restant = max(restant - part_capital, 0.0)
        lignes.append(
            Echeance(n, interets + part_capital, interets, part_capital, assurance, restant)
        )
    return lignes


def calcul_taeg(montant_net: float, flux: Sequence[float]) -> float:
    """TAEG actuariel (méthode européenne) en %.

    `flux` contient les versements mensuels de l'emprunteur (assurance comprise).
    Trouve le taux mensuel i tel que montant_net = Σ flux[k] / (1+i)^(k+1),
    puis l'annualise : TAEG = (1+i)^12 - 1.
    """
    if montant_net <= 0 or not flux or sum(flux) <= 0:
        return math.nan
    if sum(flux) <= montant_net:
        return 0.0

    def valeur_actuelle(i: float) -> float:
        actualisation, total = 1.0, 0.0
        for f in flux:
            actualisation /= 1 + i
            total += f * actualisation
        return total

    bas, haut = 0.0, 1.0
    for _ in range(80):
        milieu = (bas + haut) / 2
        if valeur_actuelle(milieu) > montant_net:
            bas = milieu
        else:
            haut = milieu
    return ((1 + (bas + haut) / 2) ** 12 - 1) * 100


def simuler(
    capital: float,
    taux_annuel: float,
    duree_mois: int,
    taux_assurance: float = 0.0,
    frais: float = 0.0,
    assurance_sur_crd: bool = False,
) -> ResultatCredit:
    """Simulation complète d'un crédit amortissable."""
    tableau = tableau_amortissement(capital, taux_annuel, duree_mois, taux_assurance, assurance_sur_crd)
    return ResultatCredit(
        capital=capital,
        duree_mois=duree_mois,
        taux_annuel=taux_annuel,
        taux_assurance=taux_assurance,
        assurance_sur_crd=assurance_sur_crd,
        mensualite_hors_assurance=mensualite(capital, taux_annuel, duree_mois),
        frais=frais,
        taeg=calcul_taeg(capital - frais, [e.mensualite + e.assurance for e in tableau]),
        tableau=tableau,
    )


@dataclass(frozen=True)
class Budget:
    """Budget mensuel du foyer avec le crédit simulé."""

    revenus: float
    mensualite_credit: float
    autres_credits: float
    depenses: dict[str, float]  # libellé -> montant mensuel

    @property
    def total_credits(self) -> float:
        return self.mensualite_credit + self.autres_credits

    @property
    def total_depenses(self) -> float:
        return sum(self.depenses.values())

    @property
    def total_sorties(self) -> float:
        """Crédits + dépenses courantes."""
        return self.total_credits + self.total_depenses

    @property
    def solde(self) -> float:
        """Ce qui reste chaque mois une fois crédits et dépenses payés (négatif = déficit)."""
        return self.revenus - self.total_sorties

    def part_du_revenu(self, montant: float) -> float:
        return montant / self.revenus * 100 if self.revenus > 0 else math.nan

    @property
    def part_credit_revenu(self) -> float:
        return self.part_du_revenu(self.mensualite_credit)

    @property
    def part_credit_sorties(self) -> float:
        """Part du crédit simulé dans l'ensemble des sorties d'argent du mois."""
        return self.mensualite_credit / self.total_sorties * 100 if self.total_sorties > 0 else math.nan

    @property
    def endettement(self) -> float:
        """Taux d'endettement : tous les crédits rapportés aux revenus."""
        return self.part_du_revenu(self.total_credits)


def mois_bascule(tableau: Sequence[Echeance]) -> int | None:
    """1re échéance où la part de capital remboursé dépasse la part d'intérêts."""
    return next((e.numero for e in tableau if e.capital >= e.interets), None)
