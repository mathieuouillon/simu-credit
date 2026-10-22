// Vérifie que la version JavaScript donne exactement les mêmes résultats que le code Python.
// Les cas de référence sont produits par : uv run python outils/generer_web.py
// Lancement : node --test web/tests/

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { Budget, calculTaeg, capitalEmpruntable, moisBascule, simuler, tauxReference } from "../js/calcul.js";
import { DONNEES } from "../js/donnees.js";
import { anneeDepassement, dureeDoublement, simulerEpargne, versementPourObjectif } from "../js/epargne.js";
import { arrondi, dureeTexte, eur, nombre, pct } from "../js/formats.js";
import { expliquer, expliquerEpargne, texte } from "../js/pedagogie.js";
import { avertissementsEpargne, calculer, comparerDurees, ErreurSimulation, parametres, tauxPour } from "../js/scenarios.js";

const CAS = JSON.parse(readFileSync(new URL("./cas_reference.json", import.meta.url), "utf-8"));

/** Égalité numérique à 1e-9 près (relatif), NaN et infinis compris (codés en chaîne dans le JSON). */
function proche(obtenu, attendu, contexte) {
  const a = typeof attendu === "string" ? Number(attendu) : attendu;
  if (Number.isNaN(a) || !Number.isFinite(a)) {
    assert.ok(Object.is(obtenu, a) || (Number.isNaN(a) && Number.isNaN(obtenu)), `${contexte} : ${obtenu} ≠ ${a}`);
    return;
  }
  const tolerance = 1e-9 * Math.max(1, Math.abs(a));
  assert.ok(Math.abs(obtenu - a) <= tolerance, `${contexte} : ${obtenu} ≠ ${a} (écart ${obtenu - a})`);
}

function prochesObjet(obtenu, attendu, contexte) {
  for (const [cle, valeur] of Object.entries(attendu)) proche(obtenu[cle], valeur, `${contexte}.${cle}`);
}

test("formatage des nombres identique à Python", () => {
  for (const c of CAS.formats) {
    if ("duree" in c) {
      assert.equal(dureeTexte(c.duree), c.texte);
      continue;
    }
    const x = Number(c.x);
    if (c.nombre !== undefined) {
      assert.equal(nombre(x, c.d), c.nombre, `nombre(${c.x}, ${c.d})`);
      assert.equal(eur(x, c.d), c.eur);
      assert.equal(arrondi(x, c.d), c.arrondi, `round(${c.x}, ${c.d})`);
    }
    assert.equal(pct(x, c.d), c.pct, `pct(${c.x}, ${c.d})`);
  }
});

test("crédit : mensualité, tableau, coûts, TAEG (300 cas)", () => {
  for (const { entree: e, attendu } of CAS.credit) {
    const r = simuler(e.capital, e.taux, e.duree, e.assurance, e.frais, e.crd);
    const ctx = `crédit ${JSON.stringify(e)}`;
    for (const cle of ["mensualiteHorsAssurance", "mensualiteTotale", "assuranceMensuelle", "coutInterets",
      "coutAssurance", "coutTotal", "montantTotalDu", "taeg"]) {
      proche(r[cle], attendu[cle], `${ctx} ${cle}`);
    }
    assert.equal(moisBascule(r.tableau), attendu.bascule, `${ctx} bascule`);
    for (const [k, ligne] of Object.entries(attendu.lignes)) prochesObjet(r.tableau[Number(k)], ligne, `${ctx} ligne ${k}`);
    const annees = r.parAnnee();
    assert.equal(annees.length, attendu.parAnnee.length);
    annees.forEach((a, k) => a.forEach((v, j) => proche(v, attendu.parAnnee[k][j], `${ctx} année ${k}`)));
  }
});

test("taux de référence, TAEG, capacité d'emprunt, budget", () => {
  for (const c of CAS.tauxReference) {
    proche(tauxReference(DONNEES.profils[c.cle].grilleTaux, c.duree), c.brut, `taux ${c.cle} ${c.duree}`);
    assert.equal(tauxPour(c.cle, c.duree, 0, true), c.affiche, `taux affiché ${c.cle} ${c.duree}`);
  }
  for (const c of CAS.taeg) proche(calculTaeg(c.montant, c.flux), c.attendu, `TAEG ${c.montant}`);
  for (const c of CAS.capacite) proche(capitalEmpruntable(c.m, c.taux, c.n, c.ass), c.attendu, "capacité");
  for (const c of CAS.budget) {
    const b = new Budget(c.revenus, c.credit, c.autres, c.depenses);
    proche(b.solde, c.solde, "solde");
    proche(b.endettement, c.endettement, "endettement");
    proche(b.partCreditRevenu, c.partRevenu, "part du revenu");
    proche(b.partCreditSorties, c.partSorties, "part des sorties");
    proche(b.totalDepenses, c.totalDepenses, "dépenses");
  }
});

const enCamel = (p) => parametres({
  parMensualite: p.par_mensualite, montant: p.montant, mensualiteSouhaitee: p.mensualite_souhaitee,
  apport: p.apport, reprise: p.reprise, travaux: p.travaux, notaire: p.notaire, assurance: p.assurance,
  assuranceSurCrd: p.assurance_sur_crd, fraisDossier: p.frais_dossier, garantie: p.garantie,
  revenus: p.revenus, charges: p.charges, depenses: p.depenses,
});

function verifierScenario(s, attendu, ctx) {
  const r = s.resultat;
  proche(r.capital, attendu.capital, `${ctx} capital`);
  assert.equal(r.dureeMois, attendu.dureeMois);
  proche(r.tauxAnnuel, attendu.tauxAnnuel, `${ctx} taux`);
  for (const cle of ["frais", "mensualiteTotale", "taeg", "coutTotal"]) proche(r[cle], attendu[cle], `${ctx} ${cle}`);
  assert.deepEqual(s.indicateurs, attendu.indicateurs, `${ctx} indicateurs`);
  assert.deepEqual(s.avertissements, attendu.avertissements, `${ctx} avertissements`);
  assert.deepEqual(s.etapesMontant, attendu.etapes, `${ctx} étapes`);
  if (attendu.endettement === null) assert.equal(s.endettement, null);
  else proche(s.endettement, attendu.endettement, `${ctx} endettement`);
  proche(s.budget.solde, attendu.solde, `${ctx} solde`);
  assert.equal(s.mensualiteCible, attendu.mensualiteCible);
}

test("scénarios de crédit : montant, indicateurs, avertissements, explications (360 cas)", () => {
  let explications = 0;
  for (const { entree: e, attendu, erreur } of CAS.scenarios) {
    const p = enCamel(e.parametres);
    const taux = tauxPour(e.cle, e.duree, e.tauxSaisi, e.reference);
    const ctx = `${e.cle} ${e.parametres.par_mensualite ? "mensualité" : "montant"} ${e.duree} mois`;
    if (erreur) {
      assert.throws(() => calculer(e.cle, p, e.duree, taux), (err) => err instanceof ErreurSimulation && err.message === erreur);
      continue;
    }
    const s = calculer(e.cle, p, e.duree, taux);
    verifierScenario(s, attendu.scenario, ctx);
    const comparaison = comparerDurees(e.cle, p, e.duree, e.tauxSaisi, e.reference);
    assert.equal(comparaison.length, attendu.comparaison.length, `${ctx} nombre de durées comparées`);
    comparaison.forEach((c, k) => verifierScenario(c, attendu.comparaison[k], `${ctx} comparaison ${k}`));
    if (attendu.explication) {
      const html = expliquer(s.resultat, {
        etapesMontant: s.etapesMontant, mensualiteCible: s.mensualiteCible, budget: s.budget,
        endettementMax: DONNEES.endettementMax, comparaison: comparaison.map((c) => c.resultat),
      });
      assert.equal(texte(html), attendu.explication, `${ctx} explication`);
      explications++;
    }
  }
  assert.ok(explications > 100);
});

test("épargne : capital, intérêts, prélèvements, inflation, objectif, explications (240 cas)", () => {
  for (const { entree: e, attendu } of CAS.epargne) {
    const ctx = `épargne ${JSON.stringify(e)}`;
    const r = simulerEpargne(e.capital, e.versement, e.duree, e.taux, e.prelevements, e.inflation);
    const { annees, ...resume } = attendu.resultat;
    prochesObjet(r, resume, ctx);
    assert.equal(r.annees.length, annees.length);
    r.annees.forEach((a, k) => prochesObjet(a, annees[k], `${ctx} année ${k + 1}`));
    const v = versementPourObjectif(e.objectif, e.capital, e.duree, e.taux, e.prelevements);
    proche(v, attendu.versementObjectif, `${ctx} objectif`);
    proche(dureeDoublement(r.rendementNet), attendu.doublement, `${ctx} doublement`);
    const placement = DONNEES.placements[e.placement];
    assert.equal(placement.plafond ? anneeDepassement(r, placement.plafond) : null, attendu.depassement);
    assert.deepEqual(avertissementsEpargne(r, placement), attendu.avertissements, `${ctx} avertissements`);
    if (attendu.explication) {
      const html = attendu.parObjectif
        ? expliquerEpargne(simulerEpargne(e.capital, v, e.duree, e.taux, e.prelevements, e.inflation), { objectif: e.objectif, plusTot: null })
        : expliquerEpargne(r, {
            objectif: null,
            plusTot: simulerEpargne(e.capital, e.versement, e.duree + 5, e.taux, e.prelevements, e.inflation),
          });
      assert.equal(texte(html), attendu.explication, `${ctx} explication`);
    }
  }
});
