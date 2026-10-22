// Scénarios de simulation — portage de simu_credit/scenarios.py (même logique, mêmes textes).

import { Budget, capitalEmpruntable, simuler, tauxReference } from "./calcul.js";
import { DONNEES } from "./donnees.js";
import { anneeDepassement } from "./epargne.js";
import { arrondi, dureeTexte, eur, fixe, nombre, pct } from "./formats.js";

const { profils: PROFILS, endettementMax: ENDETTEMENT_MAX, couleurOk: OK, couleurAlerte: ALERTE } = DONNEES;

const indicateur = (libelle, valeur, couleur = null) => ({ libelle, valeur, couleur });

/** Paramètres saisis pour une simulation de crédit (mêmes valeurs par défaut qu'en Python). */
export function parametres(valeurs = {}) {
  return {
    parMensualite: false, montant: 0, mensualiteSouhaitee: 0, apport: 0, reprise: 0, travaux: 0,
    notaire: 7.5, assurance: 0, assuranceSurCrd: false, fraisDossier: 0, garantie: 1, revenus: 0,
    charges: 0, depenses: {}, ...valeurs,
  };
}

/** Taux de la grille de référence (arrondi comme à l'affichage) ou taux saisi. */
export function tauxPour(cle, dureeMois, tauxSaisi, reference) {
  return reference ? arrondi(tauxReference(PROFILS[cle].grilleTaux, dureeMois), 2) : tauxSaisi;
}

/** Simulation d'un crédit ; lève une Error (message affichable) si aucun emprunt n'est possible. */
export function calculer(cle, p, dureeMois, taux) {
  const scenario = { conso, auto, immo }[cle](p, dureeMois, taux);
  if (p.parMensualite) scenario.mensualiteCible = p.mensualiteSouhaitee;
  ajouterBudget(cle, p, scenario);
  return scenario;
}

export function comparerDurees(cle, p, dureeMois, tauxSaisi, reference) {
  const durees = [...new Set([...PROFILS[cle].dureesComparaison, dureeMois])].sort((a, b) => a - b);
  const resultats = [];
  for (const d of durees) {
    try {
      resultats.push(calculer(cle, p, d, tauxPour(cle, d, tauxSaisi, reference)));
    } catch (err) {
      if (!(err instanceof ErreurSimulation)) throw err;
    }
  }
  return resultats;
}

export class ErreurSimulation extends Error {}

const scenario = (resultat, indicateurs, avertissements, etapesMontant) => ({
  resultat, indicateurs, avertissements, etapesMontant, endettement: null, budget: null, mensualiteCible: null,
});

const simulerAvec = (p, capital, dureeMois, taux, frais) =>
  simuler(capital, taux, dureeMois, p.assurance, frais, p.assuranceSurCrd);

const capitalPourMensualite = (p, dureeMois, taux) =>
  capitalEmpruntable(p.mensualiteSouhaitee, taux, dureeMois, p.assurance);

function ajouterBudget(cle, p, s) {
  const b = new Budget(p.revenus, s.resultat.mensualiteTotale, p.charges, { ...p.depenses });
  s.budget = b;
  if (b.revenus <= 0) return;
  s.endettement = b.endettement;
  const ok = b.endettement <= ENDETTEMENT_MAX;
  s.indicateurs.push(
    indicateur("Part de la mensualité dans le revenu", pct(b.partCreditRevenu)),
    indicateur(`Taux d'endettement, tous crédits (max ${fixe(ENDETTEMENT_MAX, 0)} %)`, pct(b.endettement), ok ? OK : ALERTE),
    indicateur("Solde du mois après crédits et dépenses", eur(b.solde, 0), b.solde >= 0 ? OK : ALERTE),
  );
  if (!ok) {
    s.avertissements.push(
      cle === "immo"
        ? "Taux d'endettement supérieur à 35 % (recommandation HCSF) : augmentez l'apport ou la durée, ou réduisez le montant."
        : "Taux d'endettement supérieur à 35 % : seuil au-delà duquel les prêteurs refusent souvent.",
    );
  }
  if (b.solde < 0) {
    s.avertissements.push(`Budget déficitaire : il manque ${eur(-b.solde, 0)} par mois une fois crédits et dépenses payés.`);
  }
}

function conso(p, dureeMois, taux) {
  const capital = p.parMensualite ? capitalPourMensualite(p, dureeMois, taux) : p.montant;
  if (capital <= 0) throw new ErreurSimulation("Le montant emprunté doit être positif.");
  const r = simulerAvec(p, capital, dureeMois, taux, p.fraisDossier);
  const indicateurs = [];
  if (p.parMensualite) indicateurs.push(indicateur("Montant empruntable pour cette mensualité", eur(capital, 0), OK));
  const avertissements = [];
  if (!(capital >= 200 && capital <= 75_000)) {
    avertissements.push("Hors du cadre légal du crédit à la consommation (200 € à 75 000 €).");
  }
  const etapes = p.parMensualite ? [] : [["Montant emprunté", eur(capital)]];
  if (p.fraisDossier) etapes.push(["Frais de dossier, payés au départ", eur(p.fraisDossier)]);
  return scenario(r, indicateurs, avertissements, etapes);
}

function auto(p, dureeMois, taux) {
  const apport = p.apport + p.reprise;
  let capital, prix;
  if (p.parMensualite) {
    capital = capitalPourMensualite(p, dureeMois, taux);
    prix = capital + apport;
  } else {
    prix = p.montant;
    capital = prix - apport;
  }
  if (capital <= 0) throw new ErreurSimulation("L'apport et la reprise couvrent le prix : aucun emprunt nécessaire.");
  const r = simulerAvec(p, capital, dureeMois, taux, p.fraisDossier);
  const indicateurs = [];
  if (p.parMensualite) indicateurs.push(indicateur("Prix maximum du véhicule", eur(prix, 0), OK));
  indicateurs.push(
    indicateur("Part financée", pct((capital / prix) * 100)),
    indicateur("Coût total du véhicule (prix + coût du crédit)", eur(prix + r.coutTotal)),
  );
  const etapes = p.parMensualite
    ? [
        ["Montant empruntable (calculé ci-dessus)", eur(capital)],
        ["+ apport", eur(p.apport)],
        ["+ reprise de l'ancien véhicule", eur(p.reprise)],
        ["<b>= Prix maximum du véhicule</b>", `<b>${eur(prix)}</b>`],
      ]
    : [
        ["Prix du véhicule", eur(prix)],
        ["− apport", eur(p.apport)],
        ["− reprise de l'ancien véhicule", eur(p.reprise)],
        ["<b>= Montant emprunté C</b>", `<b>${eur(capital)}</b>`],
      ];
  return scenario(r, indicateurs, [], etapes);
}

function immo(p, dureeMois, taux) {
  const partNotaire = p.notaire / 100;
  let capital, projet, prix;
  if (p.parMensualite) {
    capital = capitalPourMensualite(p, dureeMois, taux);
    projet = capital + p.apport;
    prix = (projet - p.travaux) / (1 + partNotaire);
    if (prix <= 0) throw new ErreurSimulation("Mensualité et apport insuffisants pour couvrir les travaux.");
  } else {
    prix = p.montant;
    projet = prix * (1 + partNotaire) + p.travaux;
    capital = projet - p.apport;
  }
  if (capital <= 0) throw new ErreurSimulation("L'apport couvre le coût du projet : aucun emprunt nécessaire.");
  const frais = p.fraisDossier + (capital * p.garantie) / 100;
  const r = simulerAvec(p, capital, dureeMois, taux, frais);

  const indicateurs = [];
  if (p.parMensualite) indicateurs.push(indicateur("Prix maximum du bien", eur(prix, 0), OK));
  indicateurs.push(
    indicateur("Coût total du projet", eur(projet, 0)),
    indicateur("dont frais de notaire", eur(prix * partNotaire, 0)),
    indicateur("Apport / coût du projet", pct((p.apport / projet) * 100)),
  );
  const avertissements = [];
  if (p.revenus > 0) {
    const mensualiteMax = (p.revenus * ENDETTEMENT_MAX) / 100 - p.charges;
    const capacite = capitalEmpruntable(mensualiteMax, taux, dureeMois, p.assurance);
    indicateurs.push(indicateur(
      `Capacité d'emprunt max sur ${dureeTexte(dureeMois)}`,
      `${eur(capacite, 0)} (mensualité ≤ ${eur(Math.max(mensualiteMax, 0), 0)})`,
    ));
  }
  if (dureeMois > 300) {
    avertissements.push("Durée supérieure à 25 ans : au-delà de la norme HCSF (27 ans dans le neuf).");
  }
  const notaire = `frais de notaire (${pct(p.notaire, 1)} du prix)`;
  const etapes = p.parMensualite
    ? [
        ["Montant empruntable (calculé ci-dessus)", eur(capital)],
        ["+ apport", eur(p.apport)],
        ["= Budget total du projet", eur(projet)],
        ["− travaux", eur(p.travaux)],
        [`÷ (1 + ${notaire})`, nombre(1 + partNotaire, 3)],
        ["<b>= Prix maximum du bien</b>", `<b>${eur(prix)}</b>`],
      ]
    : [
        ["Prix du bien", eur(prix)],
        [`+ ${notaire}`, eur(prix * partNotaire)],
        ["+ travaux", eur(p.travaux)],
        ["= Coût total du projet", eur(projet)],
        ["− apport", eur(p.apport)],
        ["<b>= Montant emprunté C</b>", `<b>${eur(capital)}</b>`],
      ];
  etapes.push([`Frais payés au départ : dossier + garantie (${pct(p.garantie, 1)} de C)`, eur(frais)]);
  return scenario(r, indicateurs, avertissements, etapes);
}

// --------------------------------------------------------------------------- épargne

export function avertissementsEpargne(r, placement) {
  const avertissements = [];
  if (placement.plafond) {
    const annee = anneeDepassement(r, placement.plafond);
    if (annee) {
      avertissements.push(
        `Les versements dépassent le plafond du ${placement.nom} (${eur(placement.plafond, 0)}) ` +
          `dès l'année ${annee} : au-delà, il faudrait un autre placement.`,
      );
    }
  }
  if (placement.nom.startsWith("PEL") && r.dureeAnnees > 15) avertissements.push("Un PEL dure au plus 15 ans.");
  if (r.rendementReel < 0) {
    avertissements.push(
      `Le rendement net (${pct(r.rendementNet)}) est inférieur à l'inflation (${pct(r.inflation, 1)}) : ` +
        "l'épargne perd du pouvoir d'achat.",
    );
  }
  return avertissements;
}
