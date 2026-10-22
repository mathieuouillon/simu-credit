// Audit du moteur de crédit : chaque résultat est recalculé par une méthode indépendante,
// sur 400 prêts tirés au hasard (graine fixe) dans toute la plage des paramètres :
// - mensualité retrouvée par dichotomie sur la propriété qui la définit (solde final nul) ;
// - TAEG retrouvé par la méthode de Newton et vérifié par sa définition réglementaire
//   (actualisation en années fractionnaires k/12) ;
// - tableau d'amortissement rejoué ligne à ligne.

import assert from "node:assert/strict";
import { test } from "node:test";

import { capitalEmpruntable, moisBascule, simuler } from "../js/calcul.js";
import { aleatoire, proche } from "./outils.mjs";

const alea = aleatoire(2026);
const CAS = Array.from({ length: 400 }, () => {
  const capital = Math.round(alea.uniforme(500, 1_000_000) * 100) / 100;
  return {
    capital,
    taux: alea.choix([0, Math.round(alea.uniforme(0.1, 15) * 100) / 100]),
    duree: alea.entier(3, 360),
    assurance: alea.choix([0, Math.round(alea.uniforme(0.05, 1) * 100) / 100]),
    frais: alea.choix([0, Math.round(alea.uniforme(0, 0.05) * capital * 100) / 100]),
    crd: alea.hasard() < 0.5,
  };
});

function soldeFinal(capital, t, n, m) {
  let solde = capital;
  for (let k = 0; k < n; k++) solde = solde * (1 + t) - m;
  return solde;
}

function mensualiteParDichotomie(capital, taux, n) {
  const t = taux / 1200;
  let bas = 0;
  let haut = capital * 2;
  for (let k = 0; k < 200; k++) {
    const milieu = (bas + haut) / 2;
    if (soldeFinal(capital, t, n, milieu) > 0) bas = milieu;
    else haut = milieu;
  }
  return (bas + haut) / 2;
}

function taegNewton(montantNet, flux) {
  let i = 0.01;
  for (let iteration = 0; iteration < 100; iteration++) {
    let f = -montantNet;
    let df = 0;
    flux.forEach((x, k) => {
      f += x * (1 + i) ** -(k + 1);
      df += -(k + 1) * x * (1 + i) ** -(k + 2);
    });
    const pas = f / df;
    i -= pas;
    if (Math.abs(pas) < 1e-15) break;
  }
  return ((1 + i) ** 12 - 1) * 100;
}

test("400 prêts au hasard : mensualité, tableau, assurance, coûts, TAEG, capacité, bascule", () => {
  for (const { capital: C, taux, duree: n, assurance: ass, frais, crd } of CAS) {
    const r = simuler(C, taux, n, ass, frais, crd);
    const t = taux / 1200;
    const ctx = `${C} € à ${taux} % sur ${n} mois`;

    // Mensualité = celle qui solde exactement le prêt
    const reference = mensualiteParDichotomie(C, taux, n);
    assert.ok(Math.abs(r.mensualiteHorsAssurance - reference) <= 1e-9 * reference, `${ctx} : mensualité`);

    // Tableau rejoué ligne à ligne
    assert.equal(r.tableau.length, n);
    let restant = C;
    for (const e of r.tableau) {
      proche(e.interets, restant * t, 1e-7);
      proche(e.capital, e.mensualite - e.interets, 1e-7);
      proche(e.assurance, ((crd ? restant : C) * ass) / 1200, 1e-7);
      restant -= e.capital;
      proche(e.capitalRestant, Math.max(restant, 0), 1e-6);
    }
    assert.equal(r.tableau.at(-1).capitalRestant, 0);
    for (const e of r.tableau.slice(0, -1)) proche(e.mensualite, r.mensualiteHorsAssurance, 1e-7);

    // Totaux
    proche(r.coutInterets, r.mensualiteHorsAssurance * n - C, 1e-5);
    proche(r.coutTotal, r.coutInterets + r.coutAssurance + frais);
    if (!crd) proche(r.coutAssurance, ((C * ass) / 1200) * n, 1e-6);

    // TAEG : méthode indépendante et définition réglementaire
    const flux = r.tableau.map((e) => e.mensualite + e.assurance);
    const net = C - frais;
    if (flux.reduce((s, f) => s + f, 0) > net) {
      proche(r.taeg, taegNewton(net, flux), 1e-6);
      const X = r.taeg / 100;
      const actualise = flux.reduce((s, f, k) => s + f / (1 + X) ** ((k + 1) / 12), 0);
      assert.ok(Math.abs(actualise - net) <= 0.01, `${ctx} : définition du TAEG`);
      assert.ok(r.taeg >= ((1 + t) ** 12 - 1) * 100 - 1e-6, `${ctx} : TAEG ≥ taux actuariel`);
    }

    // Mode inverse
    assert.ok(Math.abs(capitalEmpruntable(r.mensualiteTotale, taux, n, ass) - C) <= 1e-9 * C, `${ctx} : capacité`);

    // Point de bascule
    const b = moisBascule(r.tableau);
    if (b !== null) {
      assert.ok(r.tableau[b - 1].capital >= r.tableau[b - 1].interets);
      assert.ok(r.tableau.slice(0, b - 1).every((e) => e.capital < e.interets));
    }
  }
});
