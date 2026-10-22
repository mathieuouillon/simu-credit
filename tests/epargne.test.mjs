// Calculs d'épargne : formule fermée, exemples simples, fiscalité, inflation, objectif, plafonds.

import assert from "node:assert/strict";
import { test } from "node:test";

import { anneeDepassement, dureeDoublement, simulerEpargne, tauxMensuel, versementPourObjectif } from "../js/epargne.js";
import { aleatoire, proche } from "./outils.mjs";

/** Formule fermée (sans prélèvements) : C0 (1+i)^n + V ((1+i)^n − 1) / i. */
function valeurAcquise(c0, v, annees, taux) {
  const n = 12 * annees;
  const i = (1 + taux / 100) ** (1 / 12) - 1;
  if (i === 0) return c0 + v * n;
  const q = (1 + i) ** n;
  return c0 * q + (v * (q - 1)) / i;
}

test("taux mensuel équivalent : 12 mois redonnent le taux annuel", () => {
  for (const taux of [0, 1.7, 2.5, 10]) proche((1 + tauxMensuel(taux)) ** 12, 1 + taux / 100);
});

test("300 cas au hasard : simulation = formule fermée", () => {
  const alea = aleatoire(42);
  for (let k = 0; k < 300; k++) {
    const c0 = alea.uniforme(0, 50_000);
    const v = alea.uniforme(0, 2_000);
    const annees = alea.entier(1, 50);
    const taux = alea.choix([0, alea.uniforme(0.1, 8)]);
    const r = simulerEpargne(c0, v, annees, taux);
    const attendu = valeurAcquise(c0, v, annees, taux);
    assert.ok(Math.abs(r.capitalFinal - attendu) <= 1e-10 * attendu, `${c0} + ${v}/mois, ${annees} ans à ${taux} %`);
    proche(r.totalVerse, c0 + 12 * v * annees, 1e-6);
    proche(r.interetsNets, r.capitalFinal - r.totalVerse, 1e-6);
  }
});

test("Livret A : 10 000 € placés un an à 1,7 % → 10 170 €", () => {
  proche(simulerEpargne(10_000, 0, 1, 1.7).capitalFinal, 10_170, 1e-6);
});

test("PEL : 2 % brut, 30 % de prélèvements → 1,4 % net chaque année", () => {
  const r = simulerEpargne(10_000, 0, 10, 2, 30);
  let precedent = 10_000;
  for (const a of r.annees) {
    proche(a.capital, precedent * (1 + 0.02 * 0.7), 1e-6);
    proche(a.prelevements, a.interets * 0.3, 1e-9);
    precedent = a.capital;
  }
  proche(r.rendementNet, 1.4);
});

test("inflation et rendement réel", () => {
  const r = simulerEpargne(10_000, 0, 10, 1.7, 0, 3.1);
  proche(r.capitalFinalReel, r.capitalFinal / 1.031 ** 10, 1e-6);
  assert.ok(r.capitalFinalReel < 10_000); // le Livret A ne compense pas une inflation à 3,1 %
  proche(r.rendementReel, (1.017 / 1.031 - 1) * 100);
});

test("objectif : aller-retour, et 0 € si le capital de départ suffit", () => {
  const alea = aleatoire(3);
  for (let k = 0; k < 100; k++) {
    const c0 = alea.uniforme(0, 20_000);
    const annees = alea.entier(1, 40);
    const taux = alea.uniforme(0, 5);
    const f = alea.choix([0, 17.2, 30]);
    const objectif = c0 + alea.uniforme(1_000, 200_000);
    const v = versementPourObjectif(objectif, c0, annees, taux, f);
    const final = simulerEpargne(c0, v, annees, taux, f).capitalFinal;
    if (v > 0) assert.ok(Math.abs(final - objectif) <= 1e-9 * objectif);
    else assert.ok(final >= objectif);
  }
  assert.equal(versementPourObjectif(5_000, 10_000, 5, 2), 0);
});

test("durée de doublement et règle de 72", () => {
  assert.equal(dureeDoublement(0), Infinity);
  for (const taux of [1, 2, 3, 6, 9]) {
    proche((1 + taux / 100) ** dureeDoublement(taux), 2);
    assert.ok(Math.abs(dureeDoublement(taux) - 72 / taux) <= 0.06 * (72 / taux));
  }
});

test("plafond de versements", () => {
  const r = simulerEpargne(5_000, 200, 10, 1.7); // 5 000 € + 2 400 € par an
  assert.equal(anneeDepassement(r, 12_000), 3); // LDDS : 12 200 € versés en année 3
  assert.equal(anneeDepassement(r, 1_000_000), null);
});
