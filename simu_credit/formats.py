"""Mise en forme des nombres à la française."""

from __future__ import annotations

import math


def nombre(valeur: float, decimales: int = 2) -> str:
    """12 345,67 (espace fine insécable comme séparateur de milliers)."""
    return f"{valeur:,.{decimales}f}".replace(",", " ").replace(".", ",")


def eur(valeur: float, decimales: int = 2) -> str:
    """Formate un montant à la française : 12 345,67 €."""
    return f"{nombre(valeur, decimales)} €"


def pct(valeur: float, decimales: int = 2) -> str:
    return "—" if math.isnan(valeur) else f"{nombre(valeur, decimales)} %"


def duree_texte(duree_mois: int) -> str:
    annees, mois = divmod(duree_mois, 12)
    if not annees:
        return f"{duree_mois} mois"
    texte = f"{annees} an{'s' if annees > 1 else ''}"
    return f"{texte} {mois} mois" if mois else texte
