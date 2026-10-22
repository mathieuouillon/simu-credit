"""Scénarios de simulation, indépendants de toute interface.

Rassemble les données de référence (profils de crédit, taux, placements, budget) et la logique qui
transforme les paramètres saisis en résultats affichables : montant emprunté selon le type de crédit,
indicateurs, avertissements, budget. Utilisé par l'application de bureau (Qt) et pris comme
référence par la version web (JavaScript), qui doit donner exactement les mêmes résultats.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from simu_credit.calcul import Budget, ResultatCredit, capital_empruntable, simuler, taux_reference
from simu_credit.epargne import ResultatEpargne, annee_depassement
from simu_credit.formats import duree_texte, eur, nombre, pct

COULEUR_OK = "#059669"
COULEUR_ALERTE = "#dc2626"

# --------------------------------------------------------------------------- crédit


@dataclass(frozen=True)
class Profil:
    """Valeurs par défaut et champs spécifiques d'un type de crédit."""

    libelle: str
    libelle_montant: str
    montant: float
    montant_max: float
    pas_montant: float
    apport: float
    mensualite: float  # mensualité souhaitée par défaut (mode inverse)
    duree: int  # en mois, sauf pour l'immobilier (en années)
    assurance: float
    frais_dossier: float
    grille_taux: dict[int, float]  # {durée en mois: taux nominal de référence}
    source_taux: str
    durees_comparaison: tuple[int, ...]  # en mois
    champs: frozenset[str]


# Taux de référence relevés en octobre 2026 ; à mettre à jour périodiquement.
TAUX_CETELEM = {48: 5.36}  # 15 000 € / 48 mois, TAEG fixe 5,49 % sans frais ni assurance
TAUX_MEILLEURTAUX = {120: 3.71, 180: 3.80, 240: 3.87, 300: 4.01}  # taux moyens avant négociation

PROFILS = {
    "conso": Profil(
        libelle="Consommation", libelle_montant="Montant à emprunter",
        montant=10_000, montant_max=200_000, pas_montant=500, apport=0, mensualite=250,
        duree=48, assurance=0.0, frais_dossier=0,
        grille_taux=TAUX_CETELEM,
        source_taux="Cetelem, prêt personnel, offre « à partir de » (octobre 2026)",
        durees_comparaison=(12, 24, 36, 48, 60, 72, 84),
        champs=frozenset({"duree_mois"}),
    ),
    "auto": Profil(
        libelle="Auto", libelle_montant="Prix du véhicule",
        montant=28_000, montant_max=500_000, pas_montant=500, apport=5_000, mensualite=450,
        duree=60, assurance=0.3, frais_dossier=0,
        grille_taux=TAUX_CETELEM,
        source_taux="Cetelem, crédit auto, offre « à partir de » (octobre 2026)",
        durees_comparaison=(24, 36, 48, 60, 72, 84),
        champs=frozenset({"apport", "reprise", "duree_mois"}),
    ),
    "immo": Profil(
        libelle="Immobilier", libelle_montant="Prix du bien",
        montant=250_000, montant_max=10_000_000, pas_montant=5_000, apport=25_000, mensualite=1_500,
        duree=20, assurance=0.34, frais_dossier=1_000,
        grille_taux=TAUX_MEILLEURTAUX,
        source_taux="Meilleurtaux, taux moyens avant négociation du 19/10/2026",
        durees_comparaison=(120, 180, 240, 300),
        champs=frozenset({"type_bien", "notaire", "travaux", "apport", "duree_ans", "garantie"}),
    ),
}

TAUX_NOTAIRE = {"Ancien": 7.5, "Neuf (VEFA)": 2.5}
# Dépenses courantes du foyer : (libellé, montant mensuel par défaut)
POSTES_BUDGET = [
    ("Logement (loyer, charges)", 900),
    ("Alimentation", 600),
    ("Transport", 250),
    ("Énergie et eau", 150),
    ("Assurances et abonnements", 150),
    ("Loisirs et divers", 300),
]
ENDETTEMENT_MAX = 35.0


@dataclass
class Indicateur:
    """Ligne d'information spécifique à un type de crédit (ex. taux d'endettement)."""

    libelle: str
    valeur: str
    couleur: str | None = None


@dataclass
class Scenario:
    """Résultat complet d'une simulation pour une durée donnée."""

    resultat: ResultatCredit
    indicateurs: list[Indicateur]
    avertissements: list[str]
    endettement: float | None = None  # en %, si les revenus sont renseignés
    budget: Budget | None = None
    etapes_montant: list[tuple[str, str]] = field(default_factory=list)  # pour l'explication pas à pas
    mensualite_cible: float | None = None  # mode « mensualité »


@dataclass
class Parametres:
    """Valeurs saisies pour une simulation de crédit."""

    par_mensualite: bool = False
    montant: float = 0.0
    mensualite_souhaitee: float = 0.0
    apport: float = 0.0
    reprise: float = 0.0
    travaux: float = 0.0
    notaire: float = 7.5
    assurance: float = 0.0
    assurance_sur_crd: bool = False
    frais_dossier: float = 0.0
    garantie: float = 1.0
    revenus: float = 0.0
    charges: float = 0.0
    depenses: dict[str, float] = field(default_factory=dict)


def taux_pour(cle: str, duree_mois: int, taux_saisi: float, reference: bool) -> float:
    """Taux de la grille de référence (arrondi comme à l'affichage) ou taux saisi."""
    if reference:
        return round(taux_reference(PROFILS[cle].grille_taux, duree_mois), 2)
    return taux_saisi


def calculer(cle: str, p: Parametres, duree_mois: int, taux: float) -> Scenario:
    """Simulation d'un crédit du type `cle` (conso, auto, immo) ; ValueError si aucun emprunt n'est possible."""
    calcul = {"conso": _conso, "auto": _auto, "immo": _immo}
    scenario = calcul[cle](p, duree_mois, taux)
    if p.par_mensualite:
        scenario.mensualite_cible = p.mensualite_souhaitee
    _ajouter_budget(cle, p, scenario)
    return scenario


def comparer_durees(cle: str, p: Parametres, duree_mois: int, taux_saisi: float, reference: bool) -> list[Scenario]:
    """La même simulation pour les durées de comparaison du profil et la durée choisie."""
    scenarios = []
    for d in sorted(set(PROFILS[cle].durees_comparaison) | {duree_mois}):
        try:
            scenarios.append(calculer(cle, p, d, taux_pour(cle, d, taux_saisi, reference)))
        except ValueError:
            continue
    return scenarios


def _simuler(p: Parametres, capital: float, duree_mois: int, taux: float, frais: float) -> ResultatCredit:
    return simuler(capital, taux, duree_mois, p.assurance, frais, assurance_sur_crd=p.assurance_sur_crd)


def _capital_pour_mensualite(p: Parametres, duree_mois: int, taux: float) -> float:
    return capital_empruntable(p.mensualite_souhaitee, taux, duree_mois, p.assurance)


def _ajouter_budget(cle: str, p: Parametres, s: Scenario) -> None:
    """Place la mensualité du crédit dans le budget du foyer (tous types de crédit)."""
    b = Budget(
        revenus=p.revenus,
        mensualite_credit=s.resultat.mensualite_totale,
        autres_credits=p.charges,
        depenses=dict(p.depenses),
    )
    s.budget = b
    if b.revenus <= 0:
        return
    s.endettement = b.endettement
    ok = b.endettement <= ENDETTEMENT_MAX
    s.indicateurs += [
        Indicateur("Part de la mensualité dans le revenu", pct(b.part_credit_revenu)),
        Indicateur(
            f"Taux d'endettement, tous crédits (max {ENDETTEMENT_MAX:.0f} %)",
            pct(b.endettement),
            COULEUR_OK if ok else COULEUR_ALERTE,
        ),
        Indicateur(
            "Solde du mois après crédits et dépenses",
            eur(b.solde, 0),
            COULEUR_OK if b.solde >= 0 else COULEUR_ALERTE,
        ),
    ]
    if not ok:
        s.avertissements.append(
            "Taux d'endettement supérieur à 35 % (recommandation HCSF) : "
            "augmentez l'apport ou la durée, ou réduisez le montant."
            if cle == "immo"
            else "Taux d'endettement supérieur à 35 % : seuil au-delà duquel les prêteurs refusent souvent."
        )
    if b.solde < 0:
        s.avertissements.append(
            f"Budget déficitaire : il manque {eur(-b.solde, 0)} par mois une fois crédits et dépenses payés."
        )


def _conso(p: Parametres, duree_mois: int, taux: float) -> Scenario:
    capital = _capital_pour_mensualite(p, duree_mois, taux) if p.par_mensualite else p.montant
    if capital <= 0:
        raise ValueError("Le montant emprunté doit être positif.")
    r = _simuler(p, capital, duree_mois, taux, p.frais_dossier)
    indicateurs = []
    if p.par_mensualite:
        indicateurs.append(Indicateur("Montant empruntable pour cette mensualité", eur(capital, 0), COULEUR_OK))
    avertissements = []
    if not 200 <= capital <= 75_000:
        avertissements.append("Hors du cadre légal du crédit à la consommation (200 € à 75 000 €).")
    etapes = [] if p.par_mensualite else [("Montant emprunté", eur(capital))]
    if p.frais_dossier:
        etapes.append(("Frais de dossier, payés au départ", eur(p.frais_dossier)))
    return Scenario(r, indicateurs, avertissements, etapes_montant=etapes)


def _auto(p: Parametres, duree_mois: int, taux: float) -> Scenario:
    apport = p.apport + p.reprise
    if p.par_mensualite:
        capital = _capital_pour_mensualite(p, duree_mois, taux)
        prix = capital + apport
    else:
        prix = p.montant
        capital = prix - apport
    if capital <= 0:
        raise ValueError("L'apport et la reprise couvrent le prix : aucun emprunt nécessaire.")
    r = _simuler(p, capital, duree_mois, taux, p.frais_dossier)
    indicateurs = []
    if p.par_mensualite:
        indicateurs.append(Indicateur("Prix maximum du véhicule", eur(prix, 0), COULEUR_OK))
    indicateurs += [
        Indicateur("Part financée", pct(capital / prix * 100)),
        Indicateur("Coût total du véhicule (prix + coût du crédit)", eur(prix + r.cout_total)),
    ]
    if p.par_mensualite:
        etapes = [
            ("Montant empruntable (calculé ci-dessus)", eur(capital)),
            ("+ apport", eur(p.apport)),
            ("+ reprise de l'ancien véhicule", eur(p.reprise)),
            ("<b>= Prix maximum du véhicule</b>", f"<b>{eur(prix)}</b>"),
        ]
    else:
        etapes = [
            ("Prix du véhicule", eur(prix)),
            ("− apport", eur(p.apport)),
            ("− reprise de l'ancien véhicule", eur(p.reprise)),
            ("<b>= Montant emprunté C</b>", f"<b>{eur(capital)}</b>"),
        ]
    return Scenario(r, indicateurs, [], etapes_montant=etapes)


def _immo(p: Parametres, duree_mois: int, taux: float) -> Scenario:
    part_notaire = p.notaire / 100
    if p.par_mensualite:
        capital = _capital_pour_mensualite(p, duree_mois, taux)
        projet = capital + p.apport
        prix = (projet - p.travaux) / (1 + part_notaire)
        if prix <= 0:
            raise ValueError("Mensualité et apport insuffisants pour couvrir les travaux.")
    else:
        prix = p.montant
        projet = prix * (1 + part_notaire) + p.travaux
        capital = projet - p.apport
    if capital <= 0:
        raise ValueError("L'apport couvre le coût du projet : aucun emprunt nécessaire.")
    frais = p.frais_dossier + capital * p.garantie / 100
    r = _simuler(p, capital, duree_mois, taux, frais)

    indicateurs = []
    if p.par_mensualite:
        indicateurs.append(Indicateur("Prix maximum du bien", eur(prix, 0), COULEUR_OK))
    indicateurs += [
        Indicateur("Coût total du projet", eur(projet, 0)),
        Indicateur("dont frais de notaire", eur(prix * part_notaire, 0)),
        Indicateur("Apport / coût du projet", pct(p.apport / projet * 100)),
    ]
    avertissements = []
    if p.revenus > 0:
        mensualite_max = p.revenus * ENDETTEMENT_MAX / 100 - p.charges
        capacite = capital_empruntable(mensualite_max, taux, duree_mois, p.assurance)
        indicateurs.append(
            Indicateur(
                f"Capacité d'emprunt max sur {duree_texte(duree_mois)}",
                f"{eur(capacite, 0)} (mensualité ≤ {eur(max(mensualite_max, 0), 0)})",
            )
        )
    if duree_mois > 300:
        avertissements.append("Durée supérieure à 25 ans : au-delà de la norme HCSF (27 ans dans le neuf).")
    notaire = f"frais de notaire ({pct(p.notaire, 1)} du prix)"
    if p.par_mensualite:
        etapes = [
            ("Montant empruntable (calculé ci-dessus)", eur(capital)),
            ("+ apport", eur(p.apport)),
            ("= Budget total du projet", eur(projet)),
            ("− travaux", eur(p.travaux)),
            (f"÷ (1 + {notaire})", nombre(1 + part_notaire, 3)),
            ("<b>= Prix maximum du bien</b>", f"<b>{eur(prix)}</b>"),
        ]
    else:
        etapes = [
            ("Prix du bien", eur(prix)),
            (f"+ {notaire}", eur(prix * part_notaire)),
            ("+ travaux", eur(p.travaux)),
            ("= Coût total du projet", eur(projet)),
            ("− apport", eur(p.apport)),
            ("<b>= Montant emprunté C</b>", f"<b>{eur(capital)}</b>"),
        ]
    etapes.append((
        f"Frais payés au départ : dossier + garantie ({pct(p.garantie, 1)} de C)",
        eur(frais),
    ))
    return Scenario(r, indicateurs, avertissements, etapes_montant=etapes)


# --------------------------------------------------------------------------- épargne


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
INFLATION_DEFAUT = 2.0


def avertissements_epargne(r: ResultatEpargne, placement: Placement) -> list[str]:
    avertissements = []
    if placement.plafond:
        annee = annee_depassement(r, placement.plafond)
        if annee:
            avertissements.append(
                f"Les versements dépassent le plafond du {placement.nom} ({eur(placement.plafond, 0)}) "
                f"dès l'année {annee} : au-delà, il faudrait un autre placement."
            )
    if placement.nom.startswith("PEL") and r.duree_annees > 15:
        avertissements.append("Un PEL dure au plus 15 ans.")
    if r.rendement_reel < 0:
        avertissements.append(
            f"Le rendement net ({pct(r.rendement_net)}) est inférieur à l'inflation "
            f"({pct(r.inflation, 1)}) : l'épargne perd du pouvoir d'achat."
        )
    return avertissements
