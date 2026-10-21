import math
import random

import pytest

from simu_credit.epargne import (
    annee_depassement,
    duree_doublement,
    simuler_epargne,
    taux_mensuel,
    versement_pour_objectif,
)


def _valeur_acquise(c0: float, v: float, annees: int, taux: float) -> float:
    """Formule fermée (sans prélèvements) : C0 (1+i)^n + V ((1+i)^n − 1) / i."""
    n = 12 * annees
    i = (1 + taux / 100) ** (1 / 12) - 1
    if i == 0:
        return c0 + v * n
    q = (1 + i) ** n
    return c0 * q + v * (q - 1) / i


def test_taux_mensuel_equivalent():
    # 12 mois au taux mensuel équivalent redonnent exactement le taux annuel
    for taux in (0.0, 1.7, 2.5, 10.0):
        assert (1 + taux_mensuel(taux)) ** 12 == pytest.approx(1 + taux / 100)


def test_formule_fermee_cas_aleatoires():
    alea = random.Random(42)
    for _ in range(300):
        c0, v = alea.uniform(0, 50_000), alea.uniform(0, 2_000)
        annees, taux = alea.randint(1, 50), alea.choice([0.0, alea.uniform(0.1, 8)])
        r = simuler_epargne(c0, v, annees, taux)
        assert r.capital_final == pytest.approx(_valeur_acquise(c0, v, annees, taux), rel=1e-10)
        assert r.total_verse == pytest.approx(c0 + 12 * v * annees)
        assert r.interets_nets == pytest.approx(r.capital_final - r.total_verse, abs=1e-6)


def test_livret_a_somme_placee_un_an():
    # 10 000 € au Livret A (1,7 %, exonéré) pendant un an → 10 170 €
    assert simuler_epargne(10_000, 0, 1, 1.7).capital_final == pytest.approx(10_170)


def test_prelevements_rendement_net():
    # Somme placée sans versement : chaque année le capital progresse exactement de r × (1 − f)
    r = simuler_epargne(10_000, 0, 10, 2.0, taux_prelevement=30)
    precedent = 10_000
    for a in r.annees:
        assert a.capital == pytest.approx(precedent * (1 + 0.02 * 0.7))
        assert a.prelevements == pytest.approx(a.interets * 0.30)
        precedent = a.capital
    assert r.rendement_net == pytest.approx(1.4)  # PEL 2 % brut → 1,4 % net (PFU 30 %)


def test_inflation_et_rendement_reel():
    r = simuler_epargne(10_000, 0, 10, 1.7, inflation=3.1)
    assert r.capital_final_reel == pytest.approx(r.capital_final / 1.031**10)
    assert r.capital_final_reel < 10_000  # le Livret A ne compense pas une inflation à 3,1 %
    assert r.rendement_reel == pytest.approx((1.017 / 1.031 - 1) * 100)


def test_objectif_aller_retour():
    alea = random.Random(3)
    for _ in range(100):
        c0, annees = alea.uniform(0, 20_000), alea.randint(1, 40)
        taux, f = alea.uniform(0, 5), alea.choice([0.0, 17.2, 30.0])
        objectif = c0 + alea.uniform(1_000, 200_000)
        v = versement_pour_objectif(objectif, c0, annees, taux, f)
        final = simuler_epargne(c0, v, annees, taux, f).capital_final
        if v > 0:
            assert final == pytest.approx(objectif, rel=1e-9)
        else:  # le capital de départ suffit déjà, intérêts compris
            assert final >= objectif


def test_objectif_deja_atteint():
    assert versement_pour_objectif(5_000, 10_000, 5, 2.0) == 0.0


def test_duree_doublement_et_regle_de_72():
    assert duree_doublement(0) == math.inf
    for taux in (1, 2, 3, 6, 9):
        assert (1 + taux / 100) ** duree_doublement(taux) == pytest.approx(2)
        assert duree_doublement(taux) == pytest.approx(72 / taux, rel=0.06)  # règle de 72


def test_plafond():
    r = simuler_epargne(5_000, 200, 10, 1.7)  # 5 000 + 2 400 / an
    assert annee_depassement(r, 12_000) == 3  # LDDS : 5 000 + 7 200 = 12 200 > 12 000 en année 3
    assert annee_depassement(r, 1_000_000) is None
