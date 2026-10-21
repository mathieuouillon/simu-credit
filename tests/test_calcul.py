import math

import pytest

from simu_credit.calcul import (
    Budget,
    calcul_taeg,
    capital_empruntable,
    mensualite,
    mois_bascule,
    simuler,
    tableau_amortissement,
    taux_reference,
)


def test_mensualite_reference():
    # 200 000 € sur 20 ans à 3 % : mensualité de référence ≈ 1 109,20 €
    assert mensualite(200_000, 3.0, 240) == pytest.approx(1109.20, abs=0.01)


def test_mensualite_taux_zero():
    assert mensualite(12_000, 0.0, 24) == pytest.approx(500.0)


def test_tableau_solde_a_zero():
    tableau = tableau_amortissement(15_000, 5.5, 48)
    assert len(tableau) == 48
    assert tableau[-1].capital_restant == pytest.approx(0.0, abs=1e-6)
    assert sum(e.capital for e in tableau) == pytest.approx(15_000)


def test_capital_empruntable_inverse_de_mensualite():
    m = mensualite(180_000, 3.4, 300) + 180_000 * 0.3 / 100 / 12
    assert capital_empruntable(m, 3.4, 300, 0.3) == pytest.approx(180_000)


def test_taeg_egal_taux_actuariel_sans_frais():
    r = simuler(10_000, 6.0, 60)
    # Sans frais ni assurance, TAEG = taux nominal annualisé de façon actuarielle
    assert r.taeg == pytest.approx(((1 + 0.06 / 12) ** 12 - 1) * 100, abs=1e-6)


def test_taeg_augmente_avec_frais_et_assurance():
    base = simuler(10_000, 6.0, 60).taeg
    assert simuler(10_000, 6.0, 60, frais=300).taeg > base
    assert simuler(10_000, 6.0, 60, taux_assurance=0.5).taeg > base


def test_couts_coherents():
    r = simuler(20_000, 4.9, 60, taux_assurance=0.3, frais=150)
    assert r.cout_total == pytest.approx(r.cout_interets + r.cout_assurance + 150)
    assert r.montant_total_du == pytest.approx(20_000 + r.cout_total)
    assert r.cout_assurance == pytest.approx(20_000 * 0.003 / 12 * 60)
    annuel = r.par_annee()
    assert len(annuel) == 5
    assert sum(a[1] for a in annuel) == pytest.approx(20_000)


def test_taeg_cas_limites():
    assert math.isnan(calcul_taeg(0, [100] * 12))
    assert calcul_taeg(1200, [100] * 12) == 0.0


# --- Exemples publiés par des établissements (octobre 2026), recalculés à l'identique


@pytest.mark.parametrize(
    "annees, taux, mensualite_site, cout_site",
    [(10, 3.71, 2568, 58118), (15, 3.80, 1895, 91117), (20, 3.87, 1569, 126491), (25, 4.01, 1392, 167542)],
)
def test_exemples_meilleurtaux(annees, taux, mensualite_site, cout_site):
    # 250 000 €, assurance 0,34 % sur le capital initial, simulation du 19/10/2026
    r = simuler(250_000, taux, annees * 12, taux_assurance=0.34)
    assert round(r.mensualite_totale) == mensualite_site
    assert round(r.cout_interets + r.cout_assurance) == cout_site


def test_exemple_cetelem():
    # 15 000 € sur 48 mois, 347,89 €/mois, TAEG fixe affiché 5,49 %
    assert calcul_taeg(15_000, [347.89] * 48) == pytest.approx(5.49, abs=0.005)


def test_exemple_bnp_paribas():
    # 150 000 € sur 25 ans à 2,31 % : 658,66 € hors assurance
    assert mensualite(150_000, 2.31, 300) == pytest.approx(658.66, abs=0.005)


# --- Assurance sur capital restant dû


def test_assurance_crd_decroissante_et_moins_chere():
    initial = simuler(200_000, 3.8, 240, taux_assurance=0.34)
    crd = simuler(200_000, 3.8, 240, taux_assurance=0.34, assurance_sur_crd=True)
    assurances = [e.assurance for e in crd.tableau]
    assert assurances == sorted(assurances, reverse=True)
    assert crd.assurance_mensuelle == pytest.approx(initial.assurance_mensuelle)
    assert crd.cout_assurance < initial.cout_assurance
    assert crd.taeg < initial.taeg
    assert crd.cout_interets == pytest.approx(initial.cout_interets)


def test_taeg_flux_variables_coherent():
    # Avec des flux constants, la version générique retrouve le taux actuariel
    m = mensualite(10_000, 6.0, 60)
    assert calcul_taeg(10_000, [m] * 60) == pytest.approx(((1 + 0.005) ** 12 - 1) * 100, abs=1e-6)


# --- Grille de taux de référence


def test_taux_reference_interpolation():
    grille = {120: 3.71, 180: 3.80, 240: 3.87, 300: 4.01}
    assert taux_reference(grille, 240) == pytest.approx(3.87)
    assert taux_reference(grille, 210) == pytest.approx((3.80 + 3.87) / 2)
    assert taux_reference(grille, 60) == pytest.approx(3.71)  # bornée en dessous
    assert taux_reference(grille, 360) == pytest.approx(4.01)  # bornée au-dessus
    assert taux_reference({48: 5.36}, 12) == pytest.approx(5.36)


# --- Budget du foyer


def test_budget():
    b = Budget(
        revenus=4_000, mensualite_credit=400, autres_credits=200,
        depenses={"Logement": 1_000, "Alimentation": 600},
    )
    assert b.total_credits == 600
    assert b.total_depenses == 1_600
    assert b.total_sorties == 2_200
    assert b.solde == 1_800
    assert b.part_credit_revenu == pytest.approx(10.0)
    assert b.part_credit_sorties == pytest.approx(400 / 2_200 * 100)
    assert b.endettement == pytest.approx(15.0)


def test_budget_deficitaire_et_sans_revenus():
    b = Budget(revenus=1_000, mensualite_credit=500, autres_credits=0, depenses={"Logement": 800})
    assert b.solde == -300
    assert math.isnan(Budget(0, 100, 0, {}).part_credit_revenu)


# --- Point de bascule capital / intérêts


def test_mois_bascule():
    tableau = tableau_amortissement(243_750, 3.87, 240)
    n = mois_bascule(tableau)
    assert tableau[n - 1].capital >= tableau[n - 1].interets
    assert tableau[n - 2].capital < tableau[n - 2].interets
    # Taux faible : le capital dépasse les intérêts dès la 1re échéance
    assert mois_bascule(tableau_amortissement(10_000, 2.0, 24)) == 1
