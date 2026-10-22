// Calculs d'épargne — portage de simu_credit/epargne.py.
// Taux mensuel équivalent (1 + r)^(1/12) − 1, versements en fin de mois, intérêts capitalisés
// chaque mois, prélèvements retenus le 31 décembre sur les intérêts de l'année.

import { somme } from "./formats.js";

export class ResultatEpargne {
  constructor({ capitalInitial, versementMensuel, dureeAnnees, tauxAnnuel, tauxPrelevement, inflation, annees }) {
    Object.assign(this, { capitalInitial, versementMensuel, dureeAnnees, tauxAnnuel, tauxPrelevement, inflation, annees });
  }
  get capitalFinal() {
    return this.annees.at(-1).capital;
  }
  get totalVerse() {
    return this.annees.at(-1).totalVerse;
  }
  get interetsBruts() {
    return somme(this.annees.map((a) => a.interets));
  }
  get prelevements() {
    return somme(this.annees.map((a) => a.prelevements));
  }
  get interetsNets() {
    return this.interetsBruts - this.prelevements;
  }
  get capitalFinalReel() {
    return this.annees.at(-1).capitalReel;
  }
  /** Part des intérêts nets dans le capital final, en %. */
  get partInterets() {
    return this.capitalFinal > 0 ? (this.interetsNets / this.capitalFinal) * 100 : 0;
  }
  get rendementNet() {
    return this.tauxAnnuel * (1 - this.tauxPrelevement / 100);
  }
  /** Rendement après prélèvements et inflation (relation de Fisher), en %. */
  get rendementReel() {
    return ((1 + this.rendementNet / 100) / (1 + this.inflation / 100) - 1) * 100;
  }
}

export const tauxMensuel = (tauxAnnuel) => (1 + tauxAnnuel / 100) ** (1 / 12) - 1;

export function simulerEpargne(capitalInitial, versementMensuel, dureeAnnees, tauxAnnuel, tauxPrelevement = 0, inflation = 0) {
  if (dureeAnnees <= 0) throw new RangeError("La durée doit être positive");
  const i = tauxMensuel(tauxAnnuel);
  let solde = capitalInitial;
  let totalVerse = capitalInitial;
  const annees = [];
  for (let annee = 1; annee <= dureeAnnees; annee++) {
    let interets = 0;
    for (let m = 0; m < 12; m++) {
      const interet = solde * i;
      solde += interet + versementMensuel;
      interets += interet;
    }
    const versements = 12 * versementMensuel + (annee === 1 ? capitalInitial : 0);
    totalVerse += 12 * versementMensuel;
    const prelevements = (interets * tauxPrelevement) / 100;
    solde -= prelevements;
    annees.push({
      annee,
      versements,
      interets,
      prelevements,
      capital: solde,
      totalVerse,
      capitalReel: solde / (1 + inflation / 100) ** annee,
    });
  }
  return new ResultatEpargne({ capitalInitial, versementMensuel, dureeAnnees, tauxAnnuel, tauxPrelevement, inflation, annees });
}

/** Versement mensuel pour atteindre l'objectif : capital final = A + B × V, donc V = (objectif − A) / B. */
export function versementPourObjectif(objectif, capitalInitial, dureeAnnees, tauxAnnuel, tauxPrelevement = 0) {
  const a = simulerEpargne(capitalInitial, 0, dureeAnnees, tauxAnnuel, tauxPrelevement).capitalFinal;
  const b = simulerEpargne(capitalInitial, 1, dureeAnnees, tauxAnnuel, tauxPrelevement).capitalFinal - a;
  return Math.max((objectif - a) / b, 0);
}

export function dureeDoublement(rendementAnnuel) {
  if (rendementAnnuel <= 0) return Infinity;
  return Math.log(2) / Math.log(1 + rendementAnnuel / 100);
}

export function anneeDepassement(resultat, plafond) {
  const a = resultat.annees.find((x) => x.totalVerse > plafond);
  return a ? a.annee : null;
}
