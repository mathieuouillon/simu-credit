"""Audit du moteur de calcul : chaque résultat est recalculé par une méthode indépendante.

Les références ne réutilisent pas les formules de `calcul.py` :
- mensualité retrouvée par dichotomie sur la propriété qui la définit (solde final nul) ;
- TAEG retrouvé par la méthode de Newton et vérifié par sa définition réglementaire
  (actualisation en années fractionnaires k/12) ;
- tableau d'amortissement rejoué ligne à ligne.
Les cas sont tirés au hasard (graine fixe) sur toute la plage des paramètres de l'interface.
"""

import math
import random

import pytest

from simu_credit.calcul import (
    Budget,
    calcul_taeg,
    capital_empruntable,
    mensualite,
    mois_bascule,
    simuler,
    taux_reference,
)


def _cas_aleatoires(nombre: int, graine: int = 2026):
    alea = random.Random(graine)
    for _ in range(nombre):
        capital = round(alea.uniform(500, 1_000_000), 2)
        yield dict(
            capital=capital,
            taux=alea.choice([0.0, round(alea.uniform(0.1, 15), 2)]),
            duree=alea.randint(3, 360),
            assurance=alea.choice([0.0, round(alea.uniform(0.05, 1.0), 2)]),
            frais=alea.choice([0.0, round(alea.uniform(0, 0.05) * capital, 2)]),
            crd=alea.random() < 0.5,
        )


CAS = list(_cas_aleatoires(400))


def _solde_final(capital: float, t: float, n: int, m: float) -> float:
    """Capital restant dû après n mensualités m, rejoué mois par mois."""
    solde = capital
    for _ in range(n):
        solde = solde * (1 + t) - m
    return solde


def _mensualite_par_dichotomie(capital: float, taux: float, n: int) -> float:
    t = taux / 1200
    bas, haut = 0.0, capital * 2
    for _ in range(200):
        milieu = (bas + haut) / 2
        if _solde_final(capital, t, n, milieu) > 0:
            bas = milieu
        else:
            haut = milieu
    return (bas + haut) / 2


def _taeg_newton(montant_net: float, flux: list[float]) -> float:
    """TAEG par Newton sur le taux mensuel i : f(i) = Σ flux_k (1+i)^-k − montant_net."""
    i = 0.01
    for _ in range(100):
        f = sum(x * (1 + i) ** -(k + 1) for k, x in enumerate(flux)) - montant_net
        df = sum(-(k + 1) * x * (1 + i) ** -(k + 2) for k, x in enumerate(flux))
        pas = f / df
        i -= pas
        if abs(pas) < 1e-15:
            break
    return ((1 + i) ** 12 - 1) * 100


@pytest.mark.parametrize("cas", CAS, ids=lambda c: f"{c['capital']:.0f}€-{c['taux']}%-{c['duree']}m")
def test_simulation_complete(cas):
    C, taux, n, ass, frais, crd = (
        cas["capital"], cas["taux"], cas["duree"], cas["assurance"], cas["frais"], cas["crd"],
    )
    r = simuler(C, taux, n, ass, frais, assurance_sur_crd=crd)
    t = taux / 1200

    # 1. Mensualité = celle qui solde exactement le prêt
    assert r.mensualite_hors_assurance == pytest.approx(_mensualite_par_dichotomie(C, taux, n), rel=1e-9)

    # 2. Tableau rejoué ligne à ligne
    assert len(r.tableau) == n
    restant = C
    for e in r.tableau:
        assert e.interets == pytest.approx(restant * t, abs=1e-9)
        assert e.capital == pytest.approx(e.mensualite - e.interets, abs=1e-9)
        base = restant if crd else C
        assert e.assurance == pytest.approx(base * ass / 1200, abs=1e-9)
        restant -= e.capital
        assert e.capital_restant == pytest.approx(max(restant, 0), abs=1e-6)
    assert r.tableau[-1].capital_restant == 0
    assert sum(e.capital for e in r.tableau) == pytest.approx(C, abs=1e-6)
    # Mensualité constante ; la dernière n'absorbe qu'un écart d'arrondi infime
    for e in r.tableau[:-1]:
        assert e.mensualite == pytest.approx(r.mensualite_hors_assurance, abs=1e-9)
    assert abs(r.tableau[-1].mensualite - r.mensualite_hors_assurance) < 1e-6

    # 3. Totaux
    assert r.cout_interets == pytest.approx(r.mensualite_hors_assurance * n - C, abs=1e-5)
    assert r.cout_total == pytest.approx(r.cout_interets + r.cout_assurance + frais)
    assert r.montant_total_du == pytest.approx(C + r.cout_total)
    if not crd:
        assert r.cout_assurance == pytest.approx(C * ass / 1200 * n)
    assert r.mensualite_totale == pytest.approx(r.mensualite_hors_assurance + C * ass / 1200)

    # 4. TAEG : méthode indépendante + définition réglementaire (années fractionnaires)
    flux = [e.mensualite + e.assurance for e in r.tableau]
    net = C - frais
    if sum(flux) > net:
        assert r.taeg == pytest.approx(_taeg_newton(net, flux), abs=1e-6)
        X = r.taeg / 100
        actualise = sum(f / (1 + X) ** ((k + 1) / 12) for k, f in enumerate(flux))
        assert actualise == pytest.approx(net, abs=0.01)
        # Frais et assurance ne peuvent qu'augmenter le TAEG au-delà du taux actuariel
        assert r.taeg >= ((1 + t) ** 12 - 1) * 100 - 1e-6

    # 5. Mode inverse : la capacité d'emprunt redonne la mensualité de départ
    assert capital_empruntable(r.mensualite_totale, taux, n, ass) == pytest.approx(C, rel=1e-9)

    # 6. Point de bascule
    b = mois_bascule(r.tableau)
    if b is not None:
        assert r.tableau[b - 1].capital >= r.tableau[b - 1].interets
        assert all(e.capital < e.interets for e in r.tableau[: b - 1])


def test_taeg_sans_frais_ni_assurance_est_le_taux_actuariel():
    for cas in CAS[:100]:
        r = simuler(cas["capital"], cas["taux"], cas["duree"])
        attendu = ((1 + cas["taux"] / 1200) ** 12 - 1) * 100
        assert r.taeg == pytest.approx(attendu, abs=1e-6)


def test_taux_nul():
    r = simuler(12_000, 0.0, 48, frais=0)
    assert r.mensualite_hors_assurance == pytest.approx(250.0)
    assert r.cout_interets == pytest.approx(0, abs=1e-9)
    assert r.taeg == 0.0
    # Taux nul mais frais : le TAEG devient positif
    assert simuler(12_000, 0.0, 48, frais=500).taeg > 0


def test_frais_superieurs_au_capital():
    assert math.isnan(simuler(1_000, 5.0, 12, frais=1_000).taeg)


def test_capacite_d_emprunt_atteint_exactement_35_pourcent():
    revenus, charges = 4_500, 300
    mensualite_max = revenus * 0.35 - charges
    capacite = capital_empruntable(mensualite_max, 3.87, 240, 0.34)
    r = simuler(capacite, 3.87, 240, 0.34)
    b = Budget(revenus, r.mensualite_totale, charges, {})
    assert b.endettement == pytest.approx(35.0, abs=1e-9)


def test_taux_reference_grille_meilleurtaux():
    grille = {120: 3.71, 180: 3.80, 240: 3.87, 300: 4.01}
    # Interpolation linéaire entre deux points de la grille
    for mois in range(120, 301):
        attendu = None
        for (d1, t1), (d2, t2) in zip(sorted(grille.items()), sorted(grille.items())[1:]):
            if d1 <= mois <= d2:
                attendu = t1 + (t2 - t1) * (mois - d1) / (d2 - d1)
                break
        assert taux_reference(grille, mois) == pytest.approx(attendu)


def test_budget_identites():
    alea = random.Random(7)
    for _ in range(200):
        depenses = {f"p{i}": alea.uniform(0, 2_000) for i in range(6)}
        b = Budget(alea.uniform(1, 10_000), alea.uniform(0, 3_000), alea.uniform(0, 1_000), depenses)
        assert b.solde == pytest.approx(b.revenus - b.mensualite_credit - b.autres_credits - sum(depenses.values()))
        assert b.endettement == pytest.approx((b.mensualite_credit + b.autres_credits) / b.revenus * 100)
        assert b.part_credit_revenu + b.part_du_revenu(b.autres_credits) == pytest.approx(b.endettement)


def test_mensualite_formule_fermee_contre_dichotomie_cas_extremes():
    for C, taux, n in [(1_000_000, 15, 360), (500, 0.01, 3), (200_000, 3.0, 240), (75_000, 21.0, 84)]:
        assert mensualite(C, taux, n) == pytest.approx(_mensualite_par_dichotomie(C, taux, n), rel=1e-9)


def test_taeg_cetelem_exemple_publie():
    # Recalcul direct de la publicité : 48 × 347,89 € pour 15 000 € reçus → TAEG affiché 5,49 %
    assert round(calcul_taeg(15_000, [347.89] * 48), 2) == 5.49
