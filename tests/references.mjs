// Cas de référence : chaque entrée de tests/references.json est recalculée et résumée ici,
// sous la même forme que les résultats attendus enregistrés dans le fichier.
//
// Les valeurs attendues ont été calculées à l'origine par l'implémentation Python (v0.2.0),
// vérifiée par des méthodes indépendantes et des exemples publiés. Si un changement voulu modifie
// les résultats, relire les écarts signalés par les tests puis réenregistrer :
//   node tests/mettre-a-jour-references.mjs

import { moisBascule, simuler } from "../js/calcul.js";
import { DONNEES } from "../js/donnees.js";
import { anneeDepassement, dureeDoublement, simulerEpargne, versementPourObjectif } from "../js/epargne.js";
import { arrondi, dureeTexte, nombre, pct } from "../js/formats.js";
import { expliquer, expliquerEpargne, texte } from "../js/pedagogie.js";
import { avertissementsEpargne, calculer, comparerDurees, ErreurSimulation, parametres, tauxPour } from "../js/scenarios.js";

/** NaN et infinis n'existent pas en JSON : ils sont enregistrés sous forme de chaîne. */
export const nb = (x) => (Number.isFinite(x) ? x : Number.isNaN(x) ? "NaN" : x > 0 ? "Infinity" : "-Infinity");

function resumeCredit(r) {
  const n = r.tableau.length;
  const lignes = {};
  for (const k of [...new Set([0, Math.floor(n / 2), n - 1])].sort((a, b) => a - b)) {
    const e = r.tableau[k];
    lignes[k] = { numero: e.numero, mensualite: e.mensualite, interets: e.interets, capital: e.capital,
      assurance: e.assurance, capitalRestant: e.capitalRestant };
  }
  return {
    mensualiteHorsAssurance: r.mensualiteHorsAssurance, mensualiteTotale: r.mensualiteTotale,
    assuranceMensuelle: r.assuranceMensuelle, coutInterets: r.coutInterets, coutAssurance: r.coutAssurance,
    coutTotal: r.coutTotal, montantTotalDu: r.montantTotalDu, taeg: nb(r.taeg), bascule: moisBascule(r.tableau), lignes,
  };
}

function resumeScenario(s) {
  const r = s.resultat;
  return {
    capital: r.capital, dureeMois: r.dureeMois, tauxAnnuel: r.tauxAnnuel, frais: r.frais,
    mensualiteTotale: r.mensualiteTotale, taeg: nb(r.taeg), coutTotal: r.coutTotal,
    indicateurs: s.indicateurs, avertissements: s.avertissements, etapes: s.etapesMontant,
    endettement: s.endettement === null ? null : nb(s.endettement), solde: s.budget ? s.budget.solde : null,
    mensualiteCible: s.mensualiteCible,
  };
}

function resumeEpargne(r) {
  const annee = (a) => ({ annee: a.annee, versements: a.versements, interets: a.interets, prelevements: a.prelevements,
    capital: a.capital, totalVerse: a.totalVerse, capitalReel: a.capitalReel });
  return {
    capitalFinal: r.capitalFinal, totalVerse: r.totalVerse, interetsBruts: r.interetsBruts, prelevements: r.prelevements,
    interetsNets: r.interetsNets, capitalFinalReel: r.capitalFinalReel, partInterets: r.partInterets,
    rendementNet: r.rendementNet, rendementReel: r.rendementReel, annees: [annee(r.annees[0]), annee(r.annees.at(-1))],
  };
}

function casScenario({ entree: e, attendu }) {
  const p = parametres(e.parametres);
  try {
    const s = calculer(e.cle, p, e.duree, tauxPour(e.cle, e.duree, e.tauxSaisi, e.reference));
    const comparaison = comparerDurees(e.cle, p, e.duree, e.tauxSaisi, e.reference);
    const resultat = { scenario: resumeScenario(s), comparaison: comparaison.map(resumeScenario) };
    if (attendu?.explication !== undefined) {
      resultat.explication = texte(expliquer(s.resultat, {
        etapesMontant: s.etapesMontant, mensualiteCible: s.mensualiteCible, budget: s.budget,
        endettementMax: DONNEES.endettementMax, comparaison: comparaison.map((c) => c.resultat),
      }));
    }
    return { entree: e, attendu: resultat };
  } catch (err) {
    if (!(err instanceof ErreurSimulation)) throw err;
    return { entree: e, erreur: err.message };
  }
}

function casEpargne({ entree: e, attendu }) {
  const r = simulerEpargne(e.capital, e.versement, e.duree, e.taux, e.prelevements, e.inflation);
  const v = versementPourObjectif(e.objectif, e.capital, e.duree, e.taux, e.prelevements);
  const placement = DONNEES.placements[e.placement];
  const resultat = {
    resultat: resumeEpargne(r), versementObjectif: v, doublement: nb(dureeDoublement(r.rendementNet)),
    depassement: placement.plafond ? anneeDepassement(r, placement.plafond) : null,
    avertissements: avertissementsEpargne(r, placement),
  };
  if (attendu.explication !== undefined) {
    resultat.explication = texte(attendu.parObjectif
      ? expliquerEpargne(simulerEpargne(e.capital, v, e.duree, e.taux, e.prelevements, e.inflation), { objectif: e.objectif, plusTot: null })
      : expliquerEpargne(r, {
          objectif: null,
          plusTot: simulerEpargne(e.capital, e.versement, e.duree + 5, e.taux, e.prelevements, e.inflation),
        }));
    resultat.parObjectif = attendu.parObjectif;
  }
  return { entree: e, attendu: resultat };
}

/** Recalcule toutes les valeurs attendues du fichier de références avec le code actuel. */
export function recalculer(references) {
  return {
    ...references,
    formats: references.formats.map(({ x, d }) => ({ x, d, nombre: nombre(x, d), pct: pct(x, d), arrondi: arrondi(x, d) })),
    durees: references.durees.map(({ duree }) => ({ duree, texte: dureeTexte(duree) })),
    credit: references.credit.map(({ entree: e }) => ({
      entree: e, attendu: resumeCredit(simuler(e.capital, e.taux, e.duree, e.assurance, e.frais, e.crd)),
    })),
    tauxReference: references.tauxReference.map(({ cle, duree }) => ({ cle, duree, affiche: tauxPour(cle, duree, 0, true) })),
    scenarios: references.scenarios.map(casScenario),
    epargne: references.epargne.map(casEpargne),
  };
}
