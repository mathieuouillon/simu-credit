"""Prépare la version web à partir du code Python, qui reste la référence.

    uv run python outils/generer_web.py

Produit :
- web/logo.svg : copie du logo de l'application ;
- web/js/donnees.js : données de référence (profils de crédit, taux, placements, budget, lexiques),
  exportées depuis simu_credit/scenarios.py et pedagogie.py — une seule source pour les deux versions ;
- web/tests/cas_reference.json : des centaines de cas calculés par Python, que la version
  JavaScript doit reproduire exactement (web/tests/coherence.test.mjs).
"""

from __future__ import annotations

import json
import shutil
import math
import random
import re
from dataclasses import asdict
from pathlib import Path

from simu_credit import __version__, scenarios
from simu_credit.calcul import (
    Budget,
    calcul_taeg,
    capital_empruntable,
    mois_bascule,
    simuler,
    taux_reference,
)
from simu_credit.epargne import (
    annee_depassement,
    duree_doublement,
    simuler_epargne,
    versement_pour_objectif,
)
from simu_credit.formats import duree_texte, eur, nombre, pct
from simu_credit.pedagogie import LEXIQUE, LEXIQUE_EPARGNE, expliquer, expliquer_epargne

RACINE = Path(__file__).resolve().parent.parent


def nb(x):
    """Nombre JSON ; NaN et infini (absents du JSON) deviennent des chaînes lues par Number() en JS."""
    if isinstance(x, float) and not math.isfinite(x):
        return "NaN" if math.isnan(x) else ("Infinity" if x > 0 else "-Infinity")
    return x


def texte(html: str) -> str:
    """Texte d'un fragment HTML, normalisé de la même façon côté JavaScript."""
    html = re.sub(r"<style>.*?</style>", " ", html, flags=re.S)
    html = re.sub(r"<[^>]+>", " ", html)
    return re.sub(r"\s+", " ", html).strip()


# --------------------------------------------------------------------------- données


def donnees() -> dict:
    return {
        "version": __version__,
        "profils": {
            cle: {
                "libelle": p.libelle,
                "libelleMontant": p.libelle_montant,
                "montant": p.montant,
                "montantMax": p.montant_max,
                "pasMontant": p.pas_montant,
                "apport": p.apport,
                "mensualite": p.mensualite,
                "duree": p.duree,
                "assurance": p.assurance,
                "fraisDossier": p.frais_dossier,
                "grilleTaux": sorted(p.grille_taux.items()),
                "sourceTaux": p.source_taux,
                "dureesComparaison": list(p.durees_comparaison),
                "champs": sorted(p.champs),
            }
            for cle, p in scenarios.PROFILS.items()
        },
        "tauxNotaire": scenarios.TAUX_NOTAIRE,
        "postesBudget": scenarios.POSTES_BUDGET,
        "endettementMax": scenarios.ENDETTEMENT_MAX,
        "couleurOk": scenarios.COULEUR_OK,
        "couleurAlerte": scenarios.COULEUR_ALERTE,
        "placements": [asdict(p) for p in scenarios.PLACEMENTS],
        "personnalise": scenarios.PERSONNALISE,
        "inflationDefaut": scenarios.INFLATION_DEFAUT,
        "lexique": LEXIQUE,
        "lexiqueEpargne": LEXIQUE_EPARGNE,
    }


# --------------------------------------------------------------------------- cas de référence


def resume_credit(r) -> dict:
    n = len(r.tableau)
    lignes = sorted({0, n // 2, n - 1})
    return {
        "mensualiteHorsAssurance": r.mensualite_hors_assurance,
        "mensualiteTotale": r.mensualite_totale,
        "assuranceMensuelle": r.assurance_mensuelle,
        "coutInterets": r.cout_interets,
        "coutAssurance": r.cout_assurance,
        "coutTotal": r.cout_total,
        "montantTotalDu": r.montant_total_du,
        "taeg": nb(r.taeg),
        "bascule": mois_bascule(r.tableau),
        "lignes": {str(k): {
            "numero": r.tableau[k].numero, "mensualite": r.tableau[k].mensualite,
            "interets": r.tableau[k].interets, "capital": r.tableau[k].capital,
            "assurance": r.tableau[k].assurance, "capitalRestant": r.tableau[k].capital_restant,
        } for k in lignes},
        "parAnnee": r.par_annee(),
    }


def cas_credit(alea: random.Random) -> list[dict]:
    cas = []
    for _ in range(300):
        capital = round(alea.uniform(500, 1_000_000), 2)
        e = {
            "capital": capital,
            "taux": alea.choice([0.0, round(alea.uniform(0.1, 15), 2)]),
            "duree": alea.randint(3, 360),
            "assurance": alea.choice([0.0, round(alea.uniform(0.05, 1.0), 2)]),
            "frais": alea.choice([0.0, round(alea.uniform(0, 0.05) * capital, 2), capital]),
            "crd": alea.random() < 0.5,
        }
        r = simuler(e["capital"], e["taux"], e["duree"], e["assurance"], e["frais"], e["crd"])
        cas.append({"entree": e, "attendu": resume_credit(r)})
    return cas


def cas_formats(alea: random.Random) -> list[dict]:
    valeurs = [0.0, -0.0, 0.125, 0.375, 2.5, 3.5, -2.5, 1.005, 111.5, 1.115, -0.001, 1e6, 1234567.891,
               999.995, 0.5, 1.5, 12345.675, -1500.5, 72 / 1.7, 1e-7]
    valeurs += [alea.uniform(-1e6, 1e6) for _ in range(300)] + [alea.uniform(0, 10) for _ in range(200)]
    return [
        {"x": x, "d": d, "nombre": nombre(x, d), "eur": eur(x, d), "pct": pct(x, d), "arrondi": round(x, d)}
        for x in valeurs for d in (0, 1, 2, 3, 4, 6)
    ] + [{"x": "NaN", "d": 2, "pct": pct(float("nan"))}] + [
        {"duree": m, "texte": duree_texte(m)} for m in range(1, 361)
    ]


def cas_divers(alea: random.Random) -> dict:
    grilles = {cle: p.grille_taux for cle, p in scenarios.PROFILS.items()}
    return {
        "tauxReference": [
            {"cle": cle, "duree": d, "brut": taux_reference(g, d), "affiche": scenarios.taux_pour(cle, d, 0.0, True)}
            for cle, g in grilles.items() for d in range(1, 421)
        ],
        "taeg": [
            {"montant": m, "flux": [f] * n, "attendu": nb(calcul_taeg(m, [f] * n))}
            for m, f, n in [(15_000, 347.89, 48), (1_200, 100, 12), (0, 100, 12), (10_000, 250.0, 48)]
        ],
        "capacite": [
            {"m": m, "taux": t, "n": n, "ass": a, "attendu": capital_empruntable(m, t, n, a)}
            for m, t, n, a in ((alea.uniform(-100, 5_000), alea.uniform(0, 10), alea.randint(3, 360),
                                alea.uniform(0, 1)) for _ in range(200))
        ],
        "budget": [
            {"revenus": b.revenus, "credit": b.mensualite_credit, "autres": b.autres_credits, "depenses": b.depenses,
             "solde": b.solde, "endettement": nb(b.endettement), "partRevenu": nb(b.part_credit_revenu),
             "partSorties": nb(b.part_credit_sorties), "totalDepenses": b.total_depenses}
            for b in (Budget(alea.choice([0.0, alea.uniform(500, 10_000)]), alea.uniform(0, 3_000),
                             alea.uniform(0, 800), {f"p{i}": alea.uniform(0, 1_500) for i in range(6)})
                      for _ in range(200))
        ],
    }


def parametres_aleatoires(alea: random.Random, cle: str, par_mensualite: bool) -> scenarios.Parametres:
    profil = scenarios.PROFILS[cle]
    return scenarios.Parametres(
        par_mensualite=par_mensualite,
        montant=float(round(alea.uniform(0.2, 2.5) * profil.montant)),
        mensualite_souhaitee=float(round(alea.uniform(0.3, 2.0) * profil.mensualite)),
        apport=float(alea.choice([0, round(alea.uniform(0, 1.5) * max(profil.apport, 2_000))])),
        reprise=float(alea.choice([0, round(alea.uniform(0, 8_000))])),
        travaux=float(alea.choice([0, round(alea.uniform(0, 60_000))])),
        notaire=alea.choice([7.5, 2.5, round(alea.uniform(1, 9), 1)]),
        assurance=alea.choice([0.0, round(alea.uniform(0.05, 0.6), 2)]),
        assurance_sur_crd=alea.random() < 0.4,
        frais_dossier=float(alea.choice([0, round(alea.uniform(0, 2_000))])),
        garantie=alea.choice([1.0, round(alea.uniform(0, 2), 1)]),
        revenus=float(alea.choice([0, round(alea.uniform(1_200, 9_000))])),
        charges=float(alea.choice([0, round(alea.uniform(0, 900))])),
        depenses={libelle: float(round(alea.uniform(0, 1.6) * defaut)) for libelle, defaut in scenarios.POSTES_BUDGET},
    )


def resume_scenario(s: scenarios.Scenario) -> dict:
    r = s.resultat
    return {
        "capital": r.capital, "dureeMois": r.duree_mois, "tauxAnnuel": r.taux_annuel, "frais": r.frais,
        "mensualiteTotale": r.mensualite_totale, "taeg": nb(r.taeg), "coutTotal": r.cout_total,
        "indicateurs": [asdict(i) for i in s.indicateurs],
        "avertissements": s.avertissements,
        "etapes": [list(e) for e in s.etapes_montant],
        "endettement": nb(s.endettement) if s.endettement is not None else None,
        "solde": s.budget.solde if s.budget else None,
        "mensualiteCible": s.mensualite_cible,
    }


def cas_scenarios(alea: random.Random) -> list[dict]:
    cas = []
    for k in range(360):
        cle = ("conso", "auto", "immo")[k % 3]
        par_mensualite = (k // 3) % 2 == 1
        p = parametres_aleatoires(alea, cle, par_mensualite)
        profil = scenarios.PROFILS[cle]
        duree = (profil.duree * 12 if cle == "immo" else profil.duree) + alea.choice([-12, 0, 0, 12, 24])
        reference = alea.random() < 0.7
        taux_saisi = round(alea.uniform(0, 9), 2)
        taux = scenarios.taux_pour(cle, duree, taux_saisi, reference)
        entree = {"cle": cle, "parametres": asdict(p), "duree": duree, "tauxSaisi": taux_saisi, "reference": reference}
        try:
            s = scenarios.calculer(cle, p, duree, taux)
        except ValueError as err:
            cas.append({"entree": entree, "erreur": str(err)})
            continue
        comparaison = scenarios.comparer_durees(cle, p, duree, taux_saisi, reference)
        attendu = {"scenario": resume_scenario(s), "comparaison": [resume_scenario(c) for c in comparaison]}
        if k % 3 == 0 or k < 30:
            attendu["explication"] = texte(expliquer(
                s.resultat, etapes_montant=s.etapes_montant, mensualite_cible=s.mensualite_cible,
                budget=s.budget, endettement_max=scenarios.ENDETTEMENT_MAX,
                comparaison=[c.resultat for c in comparaison],
            ))
        cas.append({"entree": entree, "attendu": attendu})
    return cas


def resume_epargne(r) -> dict:
    return {
        "capitalFinal": r.capital_final, "totalVerse": r.total_verse, "interetsBruts": r.interets_bruts,
        "prelevements": r.prelevements, "interetsNets": r.interets_nets, "capitalFinalReel": r.capital_final_reel,
        "partInterets": r.part_interets, "rendementNet": r.rendement_net, "rendementReel": r.rendement_reel,
        "annees": [
            {"annee": a.annee, "versements": a.versements, "interets": a.interets, "prelevements": a.prelevements,
             "capital": a.capital, "totalVerse": a.total_verse, "capitalReel": a.capital_reel}
            for a in r.annees
        ],
    }


def cas_epargne(alea: random.Random) -> list[dict]:
    cas = []
    for k in range(240):
        placement = alea.choice(scenarios.PLACEMENTS)
        e = {
            "capital": float(alea.choice([0, round(alea.uniform(0, 50_000))])),
            "versement": float(alea.choice([0, round(alea.uniform(0, 1_500))])),
            "duree": alea.randint(1, 50),
            "taux": alea.choice([placement.taux, round(alea.uniform(0, 8), 2)]),
            "prelevements": alea.choice([placement.prelevements, round(alea.uniform(0, 40), 1)]),
            "inflation": alea.choice([2.0, 3.1, round(alea.uniform(0, 6), 1)]),
            "objectif": float(round(alea.uniform(1_000, 300_000))),
            "placement": scenarios.PLACEMENTS.index(placement),
        }
        r = simuler_epargne(e["capital"], e["versement"], e["duree"], e["taux"], e["prelevements"], e["inflation"])
        v = versement_pour_objectif(e["objectif"], e["capital"], e["duree"], e["taux"], e["prelevements"])
        attendu = {
            "resultat": resume_epargne(r),
            "versementObjectif": v,
            "doublement": nb(duree_doublement(r.rendement_net)),
            "depassement": annee_depassement(r, placement.plafond) if placement.plafond else None,
            "avertissements": scenarios.avertissements_epargne(r, placement),
        }
        if k % 3 == 0:
            par_objectif = k % 2 == 0
            if par_objectif:
                ro = simuler_epargne(e["capital"], v, e["duree"], e["taux"], e["prelevements"], e["inflation"])
                attendu["explication"] = texte(expliquer_epargne(ro, objectif=e["objectif"], plus_tot=None))
            else:
                plus_tot = simuler_epargne(e["capital"], e["versement"], e["duree"] + 5, e["taux"],
                                           e["prelevements"], e["inflation"])
                attendu["explication"] = texte(expliquer_epargne(r, objectif=None, plus_tot=plus_tot))
            attendu["parObjectif"] = par_objectif
        cas.append({"entree": e, "attendu": attendu})
    return cas


def main() -> None:
    js = RACINE / "web" / "js" / "donnees.js"
    contenu = json.dumps(donnees(), ensure_ascii=False, indent=2)
    js.write_text(
        "// Fichier généré par outils/generer_web.py à partir de simu_credit/ — ne pas modifier à la main.\n"
        f"export const DONNEES = {contenu};\n",
        encoding="utf-8",
    )
    shutil.copyfile(RACINE / "simu_credit" / "assets" / "logo.svg", RACINE / "web" / "logo.svg")
    alea = random.Random(2026)
    cas = {
        "credit": cas_credit(alea),
        "formats": cas_formats(alea),
        **cas_divers(alea),
        "scenarios": cas_scenarios(alea),
        "epargne": cas_epargne(alea),
    }
    sortie = RACINE / "web" / "tests" / "cas_reference.json"
    sortie.write_text(json.dumps(cas, ensure_ascii=False, allow_nan=False), encoding="utf-8")
    print(f"{js.relative_to(RACINE)} et {sortie.relative_to(RACINE)} ({sortie.stat().st_size // 1024} Ko) générés.")


if __name__ == "__main__":
    main()
