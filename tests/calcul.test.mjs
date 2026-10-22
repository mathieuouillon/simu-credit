// Calculs de crédit : valeurs de référence, exemples publiés par des établissements, cas particuliers.

import assert from "node:assert/strict";
import { test } from "node:test";

import { Budget, calculTaeg, capitalEmpruntable, mensualite, moisBascule, simuler, tableauAmortissement, tauxReference } from "../js/calcul.js";
import { proche } from "./outils.mjs";

test("mensualité de référence : 200 000 € sur 20 ans à 3 % ≈ 1 109,20 €", () => {
  proche(mensualite(200_000, 3, 240), 1109.2, 0.01);
});

test("taux nul : 12 000 € sur 24 mois = 500 €", () => {
  proche(mensualite(12_000, 0, 24), 500);
});

test("le tableau solde exactement le capital", () => {
  const tableau = tableauAmortissement(15_000, 5.5, 48);
  assert.equal(tableau.length, 48);
  proche(tableau.at(-1).capitalRestant, 0, 1e-6);
  proche(tableau.reduce((s, e) => s + e.capital, 0), 15_000, 1e-6);
});

test("la capacité d'emprunt est l'inverse de la mensualité", () => {
  const m = mensualite(180_000, 3.4, 300) + (180_000 * 0.3) / 100 / 12;
  proche(capitalEmpruntable(m, 3.4, 300, 0.3), 180_000, 1e-6);
});

test("sans frais ni assurance, le TAEG est le taux actuariel", () => {
  proche(simuler(10_000, 6, 60).taeg, ((1 + 0.06 / 12) ** 12 - 1) * 100, 1e-6);
});

test("frais et assurance augmentent le TAEG", () => {
  const base = simuler(10_000, 6, 60).taeg;
  assert.ok(simuler(10_000, 6, 60, 0, 300).taeg > base);
  assert.ok(simuler(10_000, 6, 60, 0.5).taeg > base);
});

test("coûts cohérents", () => {
  const r = simuler(20_000, 4.9, 60, 0.3, 150);
  proche(r.coutTotal, r.coutInterets + r.coutAssurance + 150);
  proche(r.montantTotalDu, 20_000 + r.coutTotal);
  proche(r.coutAssurance, ((20_000 * 0.003) / 12) * 60);
  const annees = r.parAnnee();
  assert.equal(annees.length, 5);
  proche(annees.reduce((s, a) => s + a[1], 0), 20_000, 1e-6);
});

test("TAEG : cas limites", () => {
  assert.ok(Number.isNaN(calculTaeg(0, Array(12).fill(100))));
  assert.equal(calculTaeg(1200, Array(12).fill(100)), 0);
  assert.ok(Number.isNaN(simuler(1_000, 5, 12, 0, 1_000).taeg)); // frais = capital
});

// --- Exemples publiés (octobre 2026), recalculés à l'identique

test("Meilleurtaux : 250 000 €, assurance 0,34 %, de 10 à 25 ans (mensualités et coûts à l'euro)", () => {
  for (const [annees, taux, mensualiteSite, coutSite] of [
    [10, 3.71, 2568, 58118], [15, 3.8, 1895, 91117], [20, 3.87, 1569, 126491], [25, 4.01, 1392, 167542],
  ]) {
    const r = simuler(250_000, taux, annees * 12, 0.34);
    assert.equal(Math.round(r.mensualiteTotale), mensualiteSite);
    assert.equal(Math.round(r.coutInterets + r.coutAssurance), coutSite);
  }
});

test("Cetelem : 15 000 € sur 48 mois à 347,89 € → TAEG 5,49 %", () => {
  proche(calculTaeg(15_000, Array(48).fill(347.89)), 5.49, 0.005);
});

test("BNP Paribas : 150 000 € sur 25 ans à 2,31 % → 658,66 € hors assurance", () => {
  proche(mensualite(150_000, 2.31, 300), 658.66, 0.005);
});

// --- Assurance sur le capital restant dû

test("assurance sur capital restant dû : décroissante et moins chère", () => {
  const initial = simuler(200_000, 3.8, 240, 0.34);
  const crd = simuler(200_000, 3.8, 240, 0.34, 0, true);
  const assurances = crd.tableau.map((e) => e.assurance);
  assert.deepEqual(assurances, [...assurances].sort((a, b) => b - a));
  proche(crd.assuranceMensuelle, initial.assuranceMensuelle);
  assert.ok(crd.coutAssurance < initial.coutAssurance);
  assert.ok(crd.taeg < initial.taeg);
  proche(crd.coutInterets, initial.coutInterets);
});

test("taux de référence interpolé entre deux durées, borné aux extrémités", () => {
  const grille = [[120, 3.71], [180, 3.8], [240, 3.87], [300, 4.01]];
  proche(tauxReference(grille, 240), 3.87);
  proche(tauxReference(grille, 210), (3.8 + 3.87) / 2);
  proche(tauxReference(grille, 60), 3.71);
  proche(tauxReference(grille, 360), 4.01);
  proche(tauxReference([[48, 5.36]], 12), 5.36);
});

test("point de bascule capital / intérêts", () => {
  const tableau = tableauAmortissement(243_750, 3.87, 240);
  const n = moisBascule(tableau);
  assert.ok(tableau[n - 1].capital >= tableau[n - 1].interets);
  assert.ok(tableau[n - 2].capital < tableau[n - 2].interets);
  assert.equal(moisBascule(tableauAmortissement(10_000, 2, 24)), 1);
});

test("budget du foyer", () => {
  const b = new Budget(4_000, 400, 200, { Logement: 1_000, Alimentation: 600 });
  assert.equal(b.totalCredits, 600);
  assert.equal(b.totalDepenses, 1_600);
  assert.equal(b.solde, 1_800);
  proche(b.partCreditRevenu, 10);
  proche(b.partCreditSorties, (400 / 2_200) * 100);
  proche(b.endettement, 15);
  assert.equal(new Budget(1_000, 500, 0, { Logement: 800 }).solde, -300);
  assert.ok(Number.isNaN(new Budget(0, 100, 0, {}).partCreditRevenu));
});

test("capacité d'emprunt : exactement 35 % d'endettement", () => {
  const capacite = capitalEmpruntable(4_500 * 0.35 - 300, 3.87, 240, 0.34);
  const r = simuler(capacite, 3.87, 240, 0.34);
  proche(new Budget(4_500, r.mensualiteTotale, 300, {}).endettement, 35, 1e-9);
});
