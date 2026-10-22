// Calculs d'un prêt amortissable à mensualités constantes — portage de simu_credit/calcul.py.
// Les taux sont en pourcentage annuel ; taux mensuel = taux annuel / 12 (convention française).
// Toute modification doit garder ce fichier identique au module Python : les tests
// web/tests/coherence.test.mjs comparent les deux sur des centaines de cas.

import { somme } from "./formats.js";

export class ResultatCredit {
  constructor({ capital, dureeMois, tauxAnnuel, tauxAssurance, assuranceSurCrd, mensualiteHorsAssurance, frais, taeg, tableau }) {
    Object.assign(this, { capital, dureeMois, tauxAnnuel, tauxAssurance, assuranceSurCrd, mensualiteHorsAssurance, frais, taeg, tableau });
  }
  /** Assurance de la 1re échéance (la plus élevée si elle porte sur le capital restant dû). */
  get assuranceMensuelle() {
    return this.tableau.length ? this.tableau[0].assurance : 0;
  }
  /** Mensualité assurance incluse de la 1re échéance, donc la plus élevée. */
  get mensualiteTotale() {
    return this.mensualiteHorsAssurance + this.assuranceMensuelle;
  }
  get coutInterets() {
    return somme(this.tableau.map((e) => e.interets));
  }
  get coutAssurance() {
    return somme(this.tableau.map((e) => e.assurance));
  }
  /** Coût total du crédit : intérêts + assurance + frais. */
  get coutTotal() {
    return this.coutInterets + this.coutAssurance + this.frais;
  }
  get montantTotalDu() {
    return this.capital + this.coutTotal;
  }
  /** Agrège le tableau par année : [année, capital, intérêts, assurance]. */
  parAnnee() {
    const annees = new Map();
    for (const e of this.tableau) {
      const an = Math.floor((e.numero - 1) / 12) + 1;
      if (!annees.has(an)) annees.set(an, [0, 0, 0]);
      const a = annees.get(an);
      a[0] += e.capital;
      a[1] += e.interets;
      a[2] += e.assurance;
    }
    return [...annees.entries()].sort((x, y) => x[0] - y[0]).map(([an, v]) => [an, ...v]);
  }
}

/** Mensualité constante (hors assurance) d'un prêt amortissable. */
export function mensualite(capital, tauxAnnuel, dureeMois) {
  if (dureeMois <= 0) throw new RangeError("La durée doit être positive");
  if (capital <= 0) return 0;
  const t = tauxAnnuel / 100 / 12;
  if (t === 0) return capital / dureeMois;
  return (capital * t) / (1 - (1 + t) ** -dureeMois);
}

/** Capital maximal empruntable pour une mensualité donnée (assurance comprise). */
export function capitalEmpruntable(mensualiteMax, tauxAnnuel, dureeMois, tauxAssurance = 0) {
  if (mensualiteMax <= 0) return 0;
  // Mensualité totale pour 1 € emprunté ; la relation est linéaire en capital.
  const parEuro = mensualite(1, tauxAnnuel, dureeMois) + tauxAssurance / 100 / 12;
  return mensualiteMax / parEuro;
}

/** Taux d'une grille [[durée en mois, taux], …], interpolé linéairement entre deux durées. */
export function tauxReference(grille, dureeMois) {
  const points = [...grille].sort((a, b) => a[0] - b[0]);
  if (dureeMois <= points[0][0]) return points[0][1];
  for (let k = 0; k + 1 < points.length; k++) {
    const [d1, t1] = points[k];
    const [d2, t2] = points[k + 1];
    if (dureeMois <= d2) return t1 + ((t2 - t1) * (dureeMois - d1)) / (d2 - d1);
  }
  return points.at(-1)[1];
}

/** Tableau d'amortissement mensuel ; assurance sur le capital initial ou sur le capital restant dû. */
export function tableauAmortissement(capital, tauxAnnuel, dureeMois, tauxAssurance = 0, assuranceSurCrd = false) {
  const m = mensualite(capital, tauxAnnuel, dureeMois);
  const t = tauxAnnuel / 100 / 12;
  const tauxAssMensuel = tauxAssurance / 100 / 12;
  let restant = capital;
  const lignes = [];
  for (let n = 1; n <= dureeMois; n++) {
    const interets = restant * t;
    const assurance = (assuranceSurCrd ? restant : capital) * tauxAssMensuel;
    let partCapital = m - interets;
    if (n === dureeMois) partCapital = restant; // absorbe les erreurs d'arrondi sur la dernière échéance
    restant = Math.max(restant - partCapital, 0);
    lignes.push({ numero: n, mensualite: interets + partCapital, interets, capital: partCapital, assurance, capitalRestant: restant });
  }
  return lignes;
}

/** TAEG actuariel en % : taux mensuel i tel que montantNet = Σ flux[k] / (1+i)^(k+1), annualisé. */
export function calculTaeg(montantNet, flux) {
  const total = somme(flux);
  if (montantNet <= 0 || !flux.length || total <= 0) return NaN;
  if (total <= montantNet) return 0;
  const valeurActuelle = (i) => {
    let actualisation = 1;
    let va = 0;
    for (const f of flux) {
      actualisation /= 1 + i;
      va += f * actualisation;
    }
    return va;
  };
  let bas = 0;
  let haut = 1;
  for (let k = 0; k < 80; k++) {
    const milieu = (bas + haut) / 2;
    if (valeurActuelle(milieu) > montantNet) bas = milieu;
    else haut = milieu;
  }
  return ((1 + (bas + haut) / 2) ** 12 - 1) * 100;
}

/** Simulation complète d'un crédit amortissable. */
export function simuler(capital, tauxAnnuel, dureeMois, tauxAssurance = 0, frais = 0, assuranceSurCrd = false) {
  const tableau = tableauAmortissement(capital, tauxAnnuel, dureeMois, tauxAssurance, assuranceSurCrd);
  return new ResultatCredit({
    capital,
    dureeMois,
    tauxAnnuel,
    tauxAssurance,
    assuranceSurCrd,
    mensualiteHorsAssurance: mensualite(capital, tauxAnnuel, dureeMois),
    frais,
    taeg: calculTaeg(capital - frais, tableau.map((e) => e.mensualite + e.assurance)),
    tableau,
  });
}

/** Budget mensuel du foyer avec le crédit simulé. */
export class Budget {
  constructor(revenus, mensualiteCredit, autresCredits, depenses) {
    Object.assign(this, { revenus, mensualiteCredit, autresCredits, depenses });
  }
  get totalCredits() {
    return this.mensualiteCredit + this.autresCredits;
  }
  get totalDepenses() {
    return somme(Object.values(this.depenses));
  }
  get totalSorties() {
    return this.totalCredits + this.totalDepenses;
  }
  /** Ce qui reste chaque mois une fois crédits et dépenses payés (négatif = déficit). */
  get solde() {
    return this.revenus - this.totalSorties;
  }
  partDuRevenu(montant) {
    return this.revenus > 0 ? (montant / this.revenus) * 100 : NaN;
  }
  get partCreditRevenu() {
    return this.partDuRevenu(this.mensualiteCredit);
  }
  get partCreditSorties() {
    return this.totalSorties > 0 ? (this.mensualiteCredit / this.totalSorties) * 100 : NaN;
  }
  get endettement() {
    return this.partDuRevenu(this.totalCredits);
  }
}

/** 1re échéance où la part de capital remboursé dépasse la part d'intérêts. */
export function moisBascule(tableau) {
  const e = tableau.find((ligne) => ligne.capital >= ligne.interets);
  return e ? e.numero : null;
}
