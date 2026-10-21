"""Audit de l'interface : les chiffres affichés correspondent aux calculs, pour chaque type et mode."""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QLocale
from PySide6.QtWidgets import QApplication

from simu_credit.calcul import capital_empruntable, simuler, taux_reference
from simu_credit.formats import eur, pct
from simu_credit.gui import ENDETTEMENT_MAX, PROFILS, FenetrePrincipale, appliquer_theme

QLocale.setDefault(QLocale(QLocale.Language.French, QLocale.Country.France))
APP = QApplication.instance() or QApplication([])
appliquer_theme(APP)

CONSO, AUTO, IMMO = 0, 1, 2


@pytest.fixture
def ecran():
    fenetre = FenetrePrincipale()
    yield fenetre.ecran
    fenetre.close()


def _espaces(texte: str) -> str:
    """Qt remplace l'espace fine insécable par une espace ordinaire en texte brut."""
    return texte.replace("\u202f", " ").replace("\xa0", " ")


def _carte(e, cle):
    return e.resultats.cartes[cle].valeur.text()


def _verifier_cartes(e, r):
    assert _carte(e, "mensualite") == eur(r.mensualite_totale)
    assert _carte(e, "taeg") == pct(r.taeg)
    assert _carte(e, "cout") == eur(r.cout_total)
    assert _carte(e, "capital") == eur(r.capital)
    assert _carte(e, "interets") == eur(r.cout_interets)
    assert _carte(e, "assurance") == eur(r.cout_assurance)
    assert _carte(e, "frais") == eur(r.frais)
    assert _carte(e, "total_du") == eur(r.montant_total_du)


def test_conso_montant(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(CONSO)
    e.montant.setValue(15_000)
    e.duree_mois.setValue(48)
    taux = round(taux_reference(PROFILS["conso"].grille_taux, 48), 2)
    assert e.taux.value() == pytest.approx(taux)
    r = simuler(15_000, taux, 48, e.assurance.value(), e.frais_dossier.value())
    assert e.resultats.resultat.capital == 15_000
    _verifier_cartes(e, r)
    # Exemple Cetelem : 15 000 € / 48 mois → 347,89 € et TAEG 5,49 % (taux affiché arrondi)
    assert r.mensualite_totale == pytest.approx(347.89, abs=0.03)
    assert pct(r.taeg) == "5,49 %"


def test_auto_montant_et_inverse(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(AUTO)
    e.montant.setValue(30_000)
    e.apport.setValue(4_000)
    e.reprise.setValue(3_000)
    r = e.resultats.resultat
    assert r.capital == 23_000  # 30 000 − 4 000 − 3 000
    attendu = simuler(23_000, e.taux.value(), 60, e.assurance.value(), e.frais_dossier.value())
    _verifier_cartes(e, attendu)

    # Mode inverse : la mensualité obtenue ci-dessus redonne le même prix maximum
    mensualite = r.mensualite_totale
    e.mode.setCurrentIndex(1)
    e.mensualite_souhaitee.setValue(round(mensualite))
    r2 = e.resultats.resultat
    capital = capital_empruntable(round(mensualite), e.taux.value(), 60, e.assurance.value())
    assert r2.capital == pytest.approx(capital)
    prix_max = capital + 4_000 + 3_000
    # La mensualité saisie est arrondie à l'euro : ±0,50 €/mois ≈ ±27 € de prix sur 60 mois
    assert prix_max == pytest.approx(30_000, abs=30)
    assert eur(prix_max, 0) in e.resultats.zone_indicateurs.text()


def test_immo_montant(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(IMMO)
    e.montant.setValue(300_000)
    e.travaux.setValue(20_000)
    e.apport.setValue(40_000)
    e.notaire.setValue(7.5)
    r = e.resultats.resultat
    capital = 300_000 * 1.075 + 20_000 - 40_000
    assert r.capital == pytest.approx(capital)
    frais = e.frais_dossier.value() + capital * e.garantie.value() / 100
    assert r.frais == pytest.approx(frais)
    attendu = simuler(capital, e.taux.value(), 240, e.assurance.value(), frais)
    _verifier_cartes(e, attendu)


def test_immo_type_de_bien_change_les_frais_de_notaire(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(IMMO)
    e.type_bien.setCurrentText("Neuf (VEFA)")
    assert e.notaire.value() == 2.5
    assert e.resultats.resultat.capital == pytest.approx(e.montant.value() * 1.025 - e.apport.value())


def test_immo_inverse_aller_retour(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(IMMO)
    e.mode.setCurrentIndex(1)
    e.mensualite_souhaitee.setValue(1_500)
    e.travaux.setValue(10_000)
    r = e.resultats.resultat
    assert r.mensualite_totale == pytest.approx(1_500)
    prix_max = (r.capital + e.apport.value() - 10_000) / 1.075
    # Retour en mode montant avec ce prix : on retrouve 1 500 €/mois
    e.mode.setCurrentIndex(0)
    e.montant.setValue(round(prix_max))
    assert e.resultats.resultat.mensualite_totale == pytest.approx(1_500, abs=0.02)


def test_endettement_capacite_et_solde(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(IMMO)
    e.revenus.setValue(5_000)
    e.charges.setValue(250)
    s = e.calculer(240, e.taux.value())
    r, b = s.resultat, s.budget
    assert s.endettement == pytest.approx((r.mensualite_totale + 250) / 5_000 * 100)
    depenses = sum(c.value() for c in e.postes.values())
    assert b.solde == pytest.approx(5_000 - r.mensualite_totale - 250 - depenses)
    # Capacité affichée : emprunter ce montant donne exactement 35 % d'endettement
    capacite = capital_empruntable(5_000 * ENDETTEMENT_MAX / 100 - 250, e.taux.value(), 240, e.assurance.value())
    assert eur(capacite, 0) in e.resultats.zone_indicateurs.text()
    r_max = simuler(capacite, e.taux.value(), 240, e.assurance.value())
    assert (r_max.mensualite_totale + 250) / 5_000 * 100 == pytest.approx(35.0)
    # Cartes de l'onglet Budget
    cartes = e.resultats.cartes_budget
    assert cartes["endettement"].valeur.text() == pct(b.endettement)
    assert cartes["solde"].valeur.text() == eur(b.solde, 0)


def test_comparaison_des_durees(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(IMMO)
    t = e.resultats.table_comparaison
    grille = PROFILS["immo"].grille_taux
    capital = e.resultats.resultat.capital
    for ligne in range(t.rowCount()):
        duree = e.resultats._durees_comparaison[ligne]
        taux = round(taux_reference(grille, duree), 2)
        frais = e.frais_dossier.value() + capital * e.garantie.value() / 100
        r = simuler(capital, taux, duree, e.assurance.value(), frais)
        assert t.item(ligne, 1).text() == pct(taux)
        assert t.item(ligne, 3).text() == eur(r.mensualite_totale)
        assert t.item(ligne, 4).text() == eur(r.cout_total, 0)
        assert t.item(ligne, 5).text() == pct(r.taeg)


def test_taux_saisi_et_assurance_crd(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(CONSO)
    e.taux_reference.setChecked(False)
    e.taux.setValue(0.0)
    e.montant.setValue(12_000)
    e.duree_mois.setValue(24)
    assert _carte(e, "mensualite") == eur(500)
    e.taux.setValue(6.0)
    e.assurance.setValue(0.5)
    e.base_assurance.setCurrentIndex(1)
    _verifier_cartes(e, simuler(12_000, 6.0, 24, 0.5, 0, assurance_sur_crd=True))


def test_explication_reprend_les_chiffres(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(IMMO)
    r = e.resultats.resultat
    texte = _espaces(e.resultats.explication.toPlainText())
    for valeur in (r.capital, r.mensualite_hors_assurance, r.cout_total, r.tableau[0].interets):
        assert _espaces(eur(valeur)) in texte
    assert _espaces(pct(r.taeg)) in texte


def test_cas_impossibles_affiches_sans_planter(ecran):
    e = ecran
    e.type_credit.setCurrentIndex(AUTO)
    e.apport.setValue(50_000)  # apport > prix
    assert e.message.isVisibleTo(e) and "aucun emprunt" in e.message.text()
    e.type_credit.setCurrentIndex(CONSO)
    e.revenus.setValue(0)  # pas de revenus : pas de budget, pas de plantage
    assert e.resultats.cartes_budget["solde"].valeur.text() == "—"


def test_changement_de_type_remet_les_valeurs_par_defaut(ecran):
    e = ecran
    for index, cle in enumerate(PROFILS):
        e.type_credit.setCurrentIndex(index)
        p = PROFILS[cle]
        assert e.montant.value() == p.montant
        assert e.assurance.value() == p.assurance
        assert e.taux_reference.isChecked()
