import re

import pytest

from simu_credit.calcul import Budget, simuler
from simu_credit.formats import eur, nombre, pct
from simu_credit.pedagogie import expliquer


def _texte(html: str) -> str:
    return re.sub(r"<[^>]+>", "", html)


def _explication(r, **kwargs):
    params = dict(etapes_montant=[], mensualite_cible=None, budget=None, endettement_max=35.0, comparaison=[r])
    params.update(kwargs)
    return _texte(expliquer(r, **params))


def test_chiffres_de_la_simulation_affiches():
    r = simuler(243_750, 3.87, 240, taux_assurance=0.34, frais=3_437.5)
    texte = _explication(r)
    for valeur in (r.mensualite_hors_assurance, r.tableau[0].interets, r.cout_total, r.cout_assurance):
        assert eur(valeur) in texte
    assert pct(r.taeg) in texte
    assert "point de bascule" in texte


def test_decomposition_du_taeg_retombe_sur_le_taeg():
    r = simuler(20_000, 5.0, 60, taux_assurance=0.3, frais=300)
    texte = _explication(r)
    effets = [float(x.replace(",", ".")) for x in re.findall(r"\+([\d,]+) pt", texte)]
    assert len(effets) == 3
    assert r.taux_annuel + sum(effets) == pytest.approx(r.taeg, abs=0.02)


def test_mode_mensualite_et_budget():
    r = simuler(239_049.35, 3.87, 240, taux_assurance=0.34)
    b = Budget(4_500, r.mensualite_totale, 0, {"Logement": 900})
    texte = _explication(r, mensualite_cible=1_500.0, budget=b)
    assert "mensualité pour 1 €" in texte
    assert pct(b.endettement) in texte
    assert eur(b.solde) in texte


def test_a_retenir_compare_les_durees():
    courte = simuler(200_000, 3.80, 180)
    longue = simuler(200_000, 3.87, 240)
    texte = _explication(courte, comparaison=[courte, longue])
    ecart = longue.cout_total - courte.cout_total
    assert eur(ecart, 0) in texte
    assert "Allonger la durée" in texte


def test_taux_nul():
    r = simuler(1_200, 0.0, 12)
    assert "Taux nul" in _explication(r)
    assert nombre(100) in _explication(r)
