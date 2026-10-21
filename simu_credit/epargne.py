"""Calculs d'épargne : versements réguliers, intérêts composés, prélèvements et inflation.

Module sans dépendance à l'interface graphique, utilisable et testable seul.
Les taux sont exprimés en pourcentage annuel (ex. 1.7 pour 1,7 %).

Hypothèses :
- le taux annuel est converti en taux mensuel *équivalent* : (1 + r)^(1/12) − 1, de sorte
  qu'une somme placée un an entier rapporte exactement r ;
- les versements mensuels sont faits en fin de mois ;
- les intérêts sont capitalisés chaque mois ; les prélèvements (impôt, prélèvements sociaux)
  sont retenus le 31 décembre sur les intérêts de l'année.
"""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass(frozen=True)
class AnneeEpargne:
    annee: int
    versements: float  # versés pendant l'année (capital de départ inclus en année 1)
    interets: float  # intérêts bruts de l'année
    prelevements: float  # impôt et prélèvements sociaux retenus sur ces intérêts
    capital: float  # au 31 décembre, après prélèvements
    total_verse: float  # cumul des versements depuis le début
    capital_reel: float  # en euros d'aujourd'hui (corrigé de l'inflation)


@dataclass(frozen=True)
class ResultatEpargne:
    capital_initial: float
    versement_mensuel: float
    duree_annees: int
    taux_annuel: float
    taux_prelevement: float
    inflation: float
    annees: list[AnneeEpargne]

    @property
    def capital_final(self) -> float:
        return self.annees[-1].capital

    @property
    def total_verse(self) -> float:
        return self.annees[-1].total_verse

    @property
    def interets_bruts(self) -> float:
        return sum(a.interets for a in self.annees)

    @property
    def prelevements(self) -> float:
        return sum(a.prelevements for a in self.annees)

    @property
    def interets_nets(self) -> float:
        return self.interets_bruts - self.prelevements

    @property
    def capital_final_reel(self) -> float:
        return self.annees[-1].capital_reel

    @property
    def part_interets(self) -> float:
        """Part des intérêts nets dans le capital final, en %."""
        return self.interets_nets / self.capital_final * 100 if self.capital_final > 0 else 0.0

    @property
    def rendement_net(self) -> float:
        """Rendement annuel après prélèvements, en %."""
        return self.taux_annuel * (1 - self.taux_prelevement / 100)

    @property
    def rendement_reel(self) -> float:
        """Rendement annuel après prélèvements et inflation (relation de Fisher), en %."""
        return ((1 + self.rendement_net / 100) / (1 + self.inflation / 100) - 1) * 100


def taux_mensuel(taux_annuel: float) -> float:
    """Taux mensuel équivalent : 12 mois à ce taux donnent exactement le taux annuel."""
    return (1 + taux_annuel / 100) ** (1 / 12) - 1


def simuler_epargne(
    capital_initial: float,
    versement_mensuel: float,
    duree_annees: int,
    taux_annuel: float,
    taux_prelevement: float = 0.0,
    inflation: float = 0.0,
) -> ResultatEpargne:
    """Évolution de l'épargne année par année."""
    if duree_annees <= 0:
        raise ValueError("La durée doit être positive")
    i = taux_mensuel(taux_annuel)
    solde = capital_initial
    total_verse = capital_initial
    annees: list[AnneeEpargne] = []
    for annee in range(1, duree_annees + 1):
        interets = 0.0
        for _ in range(12):
            interet = solde * i
            solde += interet + versement_mensuel
            interets += interet
        versements = 12 * versement_mensuel + (capital_initial if annee == 1 else 0.0)
        total_verse += 12 * versement_mensuel
        prelevements = interets * taux_prelevement / 100
        solde -= prelevements
        annees.append(AnneeEpargne(
            annee=annee,
            versements=versements,
            interets=interets,
            prelevements=prelevements,
            capital=solde,
            total_verse=total_verse,
            capital_reel=solde / (1 + inflation / 100) ** annee,
        ))
    return ResultatEpargne(
        capital_initial, versement_mensuel, duree_annees, taux_annuel, taux_prelevement, inflation, annees
    )


def versement_pour_objectif(
    objectif: float,
    capital_initial: float,
    duree_annees: int,
    taux_annuel: float,
    taux_prelevement: float = 0.0,
) -> float:
    """Versement mensuel nécessaire pour atteindre `objectif` (0 si le capital de départ suffit).

    Le capital final est une fonction affine du versement : final(V) = A + B × V.
    Deux simulations suffisent donc pour trouver A et B, puis V = (objectif − A) / B.
    """
    a = simuler_epargne(capital_initial, 0.0, duree_annees, taux_annuel, taux_prelevement).capital_final
    b = simuler_epargne(capital_initial, 1.0, duree_annees, taux_annuel, taux_prelevement).capital_final - a
    return max((objectif - a) / b, 0.0)


def duree_doublement(rendement_annuel: float) -> float:
    """Nombre d'années pour doubler une somme placée (exact) ; inf si rendement nul ou négatif."""
    if rendement_annuel <= 0:
        return math.inf
    return math.log(2) / math.log(1 + rendement_annuel / 100)


def annee_depassement(resultat: ResultatEpargne, plafond: float) -> int | None:
    """1re année où le cumul des versements dépasse le plafond du placement."""
    return next((a.annee for a in resultat.annees if a.total_verse > plafond), None)
