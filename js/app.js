// Interface du simulateur web : lit le formulaire, lance les calculs (modules vérifiés contre Python)
// et affiche les résultats. Tout se passe dans le navigateur.

import { moisBascule } from "./calcul.js";
import { DONNEES } from "./donnees.js";
import { anneeDepassement, simulerEpargne, versementPourObjectif } from "./epargne.js";
import { dureeTexte, eur, pct } from "./formats.js";
import { anneau, barres, barresHorizontales, COULEURS } from "./graphiques.js";
import { expliquer, expliquerEpargne } from "./pedagogie.js";
import { avertissementsEpargne, calculer, comparerDurees, ErreurSimulation, parametres, tauxPour } from "./scenarios.js";

const $ = (id) => document.getElementById(id);
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
const PROFILS = DONNEES.profils;
const etat = { activite: "credit", type: "conso", modeCredit: "montant", modeEpargne: "versements", resume: {} };

/** Barre de résumé des écrans étroits : chiffres clés de l'activité affichée. */
function resumeMobile(activite, chiffres) {
  etat.resume[activite] = chiffres;
  const actuels = etat.resume[etat.activite] || [];
  $("resume-mobile").innerHTML = actuels.map(([titre, v]) => `<div><small>${esc(titre)}</small><b>${v}</b></div>`).join("");
}

/** Valeur numérique d'un champ, bornée (les champs vides ou invalides valent la borne basse). */
function valeur(id, min = 0, max = Infinity, entier = false) {
  const brut = Number.parseFloat(String($(id).value).replace(",", "."));
  let v = Number.isFinite(brut) ? brut : min;
  if (entier) v = Math.round(v);
  return Math.min(max, Math.max(min, v));
}
const fixer = (id, v) => { $(id).value = String(v); };

function segmente(conteneur, attribut, auChoix) {
  conteneur.addEventListener("click", (ev) => {
    const bouton = ev.target.closest("button");
    if (!bouton) return;
    for (const b of conteneur.querySelectorAll("button")) b.classList.toggle("actif", b === bouton);
    auChoix(bouton.dataset[attribut]);
  });
}

function onglets(groupe) {
  const barre = document.querySelector(`.onglets[data-groupe="${groupe}"]`);
  const panneaux = document.querySelector(`.panneaux[data-groupe="${groupe}"]`);
  barre.addEventListener("click", (ev) => {
    const bouton = ev.target.closest("button");
    if (!bouton) return;
    for (const b of barre.querySelectorAll("button")) b.classList.toggle("actif", b === bouton);
    for (const p of panneaux.querySelectorAll(".panneau")) p.classList.toggle("actif", p.dataset.panneau === bouton.dataset.onglet);
  });
}

/** Classe CSS d'une couleur de résultat (favorable / alerte) : chaque thème choisit ses teintes. */
const classeCouleur = (couleur) =>
  couleur === DONNEES.couleurOk ? "ok" : couleur === DONNEES.couleurAlerte ? "alerte" : "";
const carte = ({ titre, valeur: texte, aide, couleur }) =>
  `<div class="carte"${aide ? ` title="${esc(aide)}"` : ""}><div class="titre">${esc(titre)}</div>` +
  `<div class="valeur ${classeCouleur(couleur)}">${texte}</div></div>`;
const cartes = (id, liste) => { $(id).innerHTML = liste.map(carte).join(""); };
const valeurColoree = (texte, couleur) => `<b class="${classeCouleur(couleur)}">${texte}</b>`;

function message(id, lignes) {
  $(id).innerHTML = lignes.map((l) => `<b>Attention :</b> ${esc(l)}`).join("<br>");
  $(id).hidden = !lignes.length;
}

function tableau(id, colonnes, lignes, { classes = [], rouges = new Set() } = {}) {
  const tete = `<thead><tr>${colonnes.map((c) => `<th>${esc(c)}</th>`).join("")}</tr></thead>`;
  const corps = lignes.map((ligne, i) =>
    `<tr class="${classes[i] || ""}" data-index="${i}">` +
    ligne.map((cellule, j) => `<td${rouges.has(`${i},${j}`) ? ' class="alerte"' : ""}>${esc(cellule)}</td>`).join("") +
    "</tr>").join("");
  $(id).innerHTML = tete + `<tbody>${corps}</tbody>`;
}

// ============================================================================ crédit

function initialiserCredit() {
  for (const nom of Object.keys(DONNEES.tauxNotaire)) $("type-bien").add(new Option(nom, nom));
  $("type-bien").addEventListener("change", () => {
    fixer("notaire", DONNEES.tauxNotaire[$("type-bien").value]);
    recalculerCredit();
  });
  $("postes").innerHTML = DONNEES.postesBudget.map(([libelle, defaut], k) =>
    `<div class="champ"><label for="poste-${k}">${esc(libelle)}</label>` +
    `<div class="saisie"><input id="poste-${k}" type="number" min="0" step="10" value="${defaut}"><span>€</span></div></div>`).join("");

  segmente($("types-credit"), "type", (type) => appliquerProfil(type));
  segmente($("mode-credit"), "mode", (mode) => { etat.modeCredit = mode; visibiliteCredit(); recalculerCredit(); });
  $("form-credit").addEventListener("input", recalculerCredit);
  $("taux-ref").addEventListener("change", recalculerCredit);
  $("base-assurance").addEventListener("change", recalculerCredit);
  onglets("credit");
  $("table-durees").classList.add("cliquable");
  $("table-durees").addEventListener("click", (ev) => {
    const ligne = ev.target.closest("tbody tr");
    if (!ligne) return;
    const duree = etat.dureesComparees[Number(ligne.dataset.index)];
    if (etat.type === "immo") fixer("duree-ans", Math.round(duree / 12));
    else fixer("duree-mois", duree);
    recalculerCredit();
  });
  $("export-csv").addEventListener("click", exporterCsv);
  appliquerProfil("conso");
}

function appliquerProfil(type) {
  etat.type = type;
  const p = PROFILS[type];
  $("libelle-montant").textContent = p.libelleMontant;
  $("montant").step = p.pasMontant;
  $("montant").max = p.montantMax;
  fixer("montant", p.montant);
  fixer("mensualite-souhaitee", p.mensualite);
  fixer("apport", p.apport);
  fixer(type === "immo" ? "duree-ans" : "duree-mois", p.duree);
  fixer("assurance", p.assurance);
  fixer("frais-dossier", p.fraisDossier);
  if (!$("notaire").value) fixer("notaire", DONNEES.tauxNotaire[$("type-bien").value]);
  $("taux-ref").checked = true;
  $("taux-ref").title = `Utiliser le taux de référence du marché. Source : ${p.sourceTaux}`;
  visibiliteCredit();
  recalculerCredit();
}

function visibiliteCredit() {
  const champs = new Set(PROFILS[etat.type].champs);
  for (const ligne of document.querySelectorAll("#form-credit [data-champ]")) ligne.hidden = !champs.has(ligne.dataset.champ);
  const parMensualite = etat.modeCredit === "mensualite";
  document.querySelector('#form-credit [data-ligne="montant"]').hidden = parMensualite;
  document.querySelector('#form-credit [data-ligne="mensualite"]').hidden = !parMensualite;
  $("note-budget").hidden = etat.type !== "immo";
}

const dureeCredit = () => (etat.type === "immo" ? valeur("duree-ans", 5, 30, true) * 12 : valeur("duree-mois", 3, 120, true));

function parametresCredit() {
  return parametres({
    parMensualite: etat.modeCredit === "mensualite",
    montant: valeur("montant"),
    mensualiteSouhaitee: valeur("mensualite-souhaitee"),
    apport: valeur("apport"),
    reprise: valeur("reprise"),
    travaux: valeur("travaux"),
    notaire: valeur("notaire", 0, 15),
    assurance: valeur("assurance", 0, 5),
    assuranceSurCrd: $("base-assurance").value === "crd",
    fraisDossier: valeur("frais-dossier"),
    garantie: valeur("garantie", 0, 5),
    revenus: valeur("revenus"),
    charges: valeur("charges"),
    depenses: Object.fromEntries(DONNEES.postesBudget.map(([libelle], k) => [libelle, valeur(`poste-${k}`)])),
  });
}

function recalculerCredit() {
  const type = etat.type;
  const duree = dureeCredit();
  const reference = $("taux-ref").checked;
  $("taux").disabled = reference;
  if (reference) fixer("taux", tauxPour(type, duree, 0, true).toFixed(2));
  $("note-taux").textContent = reference
    ? `Taux de référence (case « Réf. ») : ${PROFILS[type].sourceTaux}. Décochez pour saisir votre propre taux.`
    : "Taux saisi, appliqué à toutes les durées de la comparaison.";
  const tauxSaisi = valeur("taux", 0, 25);
  const p = parametresCredit();
  let s;
  try {
    s = calculer(type, p, duree, tauxPour(type, duree, tauxSaisi, reference));
  } catch (err) {
    if (!(err instanceof ErreurSimulation)) throw err;
    message("message-credit", [err.message]);
    return;
  }
  const comparaison = comparerDurees(type, p, duree, tauxSaisi, reference);
  message("message-credit", s.avertissements);
  afficherCredit(s, comparaison);
}

function afficherCredit(s, comparaison) {
  const r = s.resultat;
  etat.resultatCredit = r;
  const lex = DONNEES.lexique;
  const crd = r.assuranceSurCrd && r.tauxAssurance > 0;
  cartes("cartes-credit-cles", [
    { titre: crd ? "Mensualité max. (1re échéance)" : "Mensualité (assurance incluse)", valeur: eur(r.mensualiteTotale), aide: lex["Mensualité"] },
    { titre: "TAEG", valeur: pct(r.taeg), aide: lex.TAEG },
    { titre: "Coût total du crédit", valeur: eur(r.coutTotal), aide: lex["Coût total du crédit"] },
  ]);
  cartes("cartes-credit-details", [
    { titre: "Montant emprunté", valeur: eur(r.capital) },
    { titre: "Mensualité hors assurance", valeur: eur(r.mensualiteHorsAssurance), aide: lex.Amortissement },
    { titre: crd ? "Assurance 1er mois (puis décroissante)" : "Assurance / mois", valeur: eur(r.assuranceMensuelle), aide: lex["Assurance emprunteur"] },
    { titre: "Total des intérêts", valeur: eur(r.coutInterets) },
    { titre: "Total assurance", valeur: eur(r.coutAssurance), aide: lex["Assurance emprunteur"] },
    { titre: "Frais (dossier, garantie…)", valeur: eur(r.frais), aide: lex["Frais de dossier et de garantie"] },
    { titre: "Montant total dû", valeur: eur(r.montantTotalDu) },
  ]);
  resumeMobile("credit", [["Mensualité", eur(r.mensualiteTotale)], ["TAEG", pct(r.taeg)], ["Coût total", eur(r.coutTotal, 0)]]);
  $("indicateurs-credit").innerHTML = s.indicateurs
    .map((i) => `${esc(i.libelle)} : ${valeurColoree(i.valeur, i.couleur)}`).join("<br>");

  const annees = r.parAnnee();
  $("graphiques-credit").innerHTML =
    anneau("Répartition du montant total dû", [
      { nom: "Capital", valeur: r.capital, couleur: COULEURS.capital },
      { nom: "Intérêts", valeur: r.coutInterets, couleur: COULEURS.interets },
      { nom: "Assurance", valeur: r.coutAssurance, couleur: COULEURS.assurance },
      { nom: "Frais", valeur: r.frais, couleur: COULEURS.frais },
    ]) +
    barres("Remboursements par année (en €)", {
      categories: annees.map((a) => String(a[0])),
      series: [
        { nom: "Capital", couleur: COULEURS.capital, valeurs: annees.map((a) => a[1]) },
        { nom: "Intérêts", couleur: COULEURS.interets, valeurs: annees.map((a) => a[2]) },
        ...(r.coutAssurance > 0 ? [{ nom: "Assurance", couleur: COULEURS.assurance, valeurs: annees.map((a) => a[3]) }] : []),
      ],
      titreX: "Année",
    });

  $("explication-credit").innerHTML = expliquer(r, {
    etapesMontant: s.etapesMontant, mensualiteCible: s.mensualiteCible, budget: s.budget,
    endettementMax: DONNEES.endettementMax, comparaison: comparaison.map((c) => c.resultat),
  });
  afficherBudget(s.budget);
  afficherDurees(r, comparaison);
  afficherAmortissement(r);
}

function afficherBudget(b) {
  if (!b || b.revenus <= 0) {
    cartes("cartes-budget", []);
    $("resume-budget").textContent = "Renseignez les revenus du foyer pour voir la place du crédit dans le budget.";
    $("graphique-budget").innerHTML = "";
    return;
  }
  const max = DONNEES.endettementMax;
  cartes("cartes-budget", [
    { titre: "Part du crédit dans le revenu", valeur: pct(b.partCreditRevenu) },
    { titre: "Part du crédit dans les dépenses", valeur: pct(b.partCreditSorties) },
    { titre: "Endettement (tous crédits)", valeur: pct(b.endettement), couleur: b.endettement <= max ? DONNEES.couleurOk : DONNEES.couleurAlerte, aide: DONNEES.lexique["Taux d'endettement"] },
    { titre: "Solde du mois", valeur: eur(b.solde, 0), couleur: b.solde >= 0 ? DONNEES.couleurOk : DONNEES.couleurAlerte },
  ]);
  $("resume-budget").textContent =
    `Revenus ${eur(b.revenus, 0)} · crédits ${eur(b.totalCredits, 0)} · dépenses courantes ${eur(b.totalDepenses, 0)} · ` +
    `total des sorties ${eur(b.totalSorties, 0)}`;
  const lignes = [{ libelle: "Crédit simulé", valeur: b.mensualiteCredit, couleur: COULEURS.capital }];
  if (b.autresCredits > 0) lignes.push({ libelle: "Autres crédits", valeur: b.autresCredits, couleur: COULEURS.interets });
  for (const [nom, v] of Object.entries(b.depenses)) if (v > 0) lignes.push({ libelle: nom, valeur: v, couleur: COULEURS.depenses });
  lignes.push(b.solde >= 0
    ? { libelle: "Reste disponible", valeur: b.solde, couleur: COULEURS.assurance }
    : { libelle: "Déficit", valeur: -b.solde, couleur: COULEURS.alerte });
  for (const l of lignes) l.libelle = `${l.libelle}  ${Math.round(b.partDuRevenu(l.valeur))} %`;
  const groupes = [["Crédit simulé", COULEURS.capital]];
  if (b.autresCredits > 0) groupes.push(["Autres crédits", COULEURS.interets]);
  groupes.push(["Dépenses courantes", COULEURS.depenses]);
  groupes.push(b.solde >= 0 ? ["Reste disponible", COULEURS.assurance] : ["Déficit", COULEURS.alerte]);
  $("graphique-budget").innerHTML = barresHorizontales("Où va le revenu chaque mois (en % du revenu)", lignes, groupes, "€ par mois");
}

function afficherDurees(courant, comparaison) {
  const avecEndettement = comparaison.some((s) => s.endettement !== null);
  const colonnes = ["Durée", "Taux", "Montant emprunté", "Mensualité", "Coût total", "TAEG", ...(avecEndettement ? ["Endettement"] : [])];
  etat.dureesComparees = comparaison.map((s) => s.resultat.dureeMois);
  const rouges = new Set();
  const lignes = comparaison.map((s, i) => {
    const r = s.resultat;
    if (s.endettement !== null && s.endettement > DONNEES.endettementMax) rouges.add(`${i},6`);
    return [dureeTexte(r.dureeMois), pct(r.tauxAnnuel), eur(r.capital, 0), eur(r.mensualiteTotale), eur(r.coutTotal, 0),
      pct(r.taeg), ...(avecEndettement ? [s.endettement !== null ? pct(s.endettement) : "—"] : [])];
  });
  const classes = comparaison.map((s) => (s.resultat.dureeMois === courant.dureeMois ? "courante" : ""));
  tableau("table-durees", colonnes, lignes, { classes, rouges });
}

function afficherAmortissement(r) {
  const bascule = moisBascule(r.tableau);
  tableau("table-amortissement", ["N°", "Mensualité", "Intérêts", "Capital", "Assurance", "Capital restant"],
    r.tableau.map((e) => [`${e.numero} (an ${Math.floor((e.numero - 1) / 12) + 1})`, eur(e.mensualite), eur(e.interets),
      eur(e.capital), eur(e.assurance), eur(e.capitalRestant)]),
    { classes: r.tableau.map((e) => (e.numero === bascule ? "bascule" : "")) });
}

function exporterCsv() {
  const r = etat.resultatCredit;
  if (!r) return;
  const num = (v) => v.toFixed(2).replace(".", ","); // format compatible Excel français
  const lignes = [["N°", "Mensualité", "Intérêts", "Capital", "Assurance", "Capital restant"].join(";")];
  for (const e of r.tableau) {
    lignes.push([e.numero, num(e.mensualite), num(e.interets), num(e.capital), num(e.assurance), num(e.capitalRestant)].join(";"));
  }
  const lien = document.createElement("a");
  lien.href = URL.createObjectURL(new Blob(["﻿" + lignes.join("\r\n")], { type: "text/csv;charset=utf-8" }));
  lien.download = "amortissement.csv";
  lien.click();
  URL.revokeObjectURL(lien.href);
}

// ============================================================================ épargne

function initialiserEpargne() {
  DONNEES.placements.forEach((p, k) => $("placement").add(new Option(p.nom, k)));
  fixer("inflation", DONNEES.inflationDefaut.toFixed(2));
  $("placement").addEventListener("change", appliquerPlacement);
  segmente($("mode-epargne"), "mode", (mode) => {
    etat.modeEpargne = mode;
    document.querySelector('#form-epargne [data-ligne="versements"]').hidden = mode === "objectif";
    document.querySelector('#form-epargne [data-ligne="objectif"]').hidden = mode !== "objectif";
    recalculerEpargne();
  });
  document.querySelector('#form-epargne [data-ligne="objectif"]').hidden = true;
  $("form-epargne").addEventListener("input", recalculerEpargne);
  for (const id of ["taux-epargne-ref", "prelevements-ref"]) $(id).addEventListener("change", recalculerEpargne);
  onglets("epargne");
  appliquerPlacement();
}

const placementCourant = () => DONNEES.placements[Number($("placement").value)];
const estPersonnalise = () => Number($("placement").value) === DONNEES.personnalise;

function appliquerPlacement() {
  const p = placementCourant();
  for (const id of ["taux-epargne-ref", "prelevements-ref"]) $(id).checked = !estPersonnalise();
  const plafond = p.plafond ? ` Plafond de versements : ${eur(p.plafond, 0)}.` : "";
  const reference = estPersonnalise() ? "" : " Décochez « Réf. » pour modifier le taux ou les prélèvements.";
  $("note-placement").textContent = `${p.nom} : ${p.source}.${plafond} ${p.note}${reference}`.trim();
  recalculerEpargne();
}

/** Champs cochés « Réf. » : valeur actuelle du placement, non modifiable. */
function synchroniserReferences() {
  const p = placementCourant();
  const personnalise = estPersonnalise();
  for (const [champ, caseRef, v] of [["taux-epargne", "taux-epargne-ref", p.taux], ["prelevements", "prelevements-ref", p.prelevements]]) {
    $(caseRef).disabled = personnalise;
    if (personnalise) $(caseRef).checked = false;
    $(champ).disabled = $(caseRef).checked;
    if ($(caseRef).checked) fixer(champ, v.toFixed(2));
  }
}

function simulerCourant(placement = null, duree = null) {
  const taux = placement ? placement.taux : valeur("taux-epargne", 0, 20);
  const prelev = placement ? placement.prelevements : valeur("prelevements", 0, 100);
  const annees = duree ?? valeur("duree-epargne", 1, 50, true);
  const c0 = valeur("capital-initial");
  const inflation = valeur("inflation", 0, 20);
  let objectif = null;
  let versement;
  if (etat.modeEpargne === "objectif") {
    objectif = valeur("objectif");
    versement = versementPourObjectif(objectif, c0, annees, taux, prelev);
  } else {
    versement = valeur("versement");
  }
  return [simulerEpargne(c0, versement, annees, taux, prelev, inflation), objectif];
}

function recalculerEpargne() {
  synchroniserReferences();
  const [r, objectif] = simulerCourant();
  const p = placementCourant();
  message("message-epargne", avertissementsEpargne(r, p));
  const plusTot = etat.modeEpargne === "objectif" ? null : simulerCourant(null, r.dureeAnnees + 5)[0];
  const comparaison = DONNEES.placements.slice(0, DONNEES.personnalise).map((pl) => [pl, ...simulerCourant(pl)]);
  let choisi = p;
  if (estPersonnalise()) comparaison.push([p, r, objectif]);
  else if (!$("taux-epargne-ref").checked || !$("prelevements-ref").checked) {
    choisi = { ...p, nom: `${p.nom} (vos valeurs)`, taux: valeur("taux-epargne", 0, 20), prelevements: valeur("prelevements", 0, 100) };
    comparaison.push([choisi, r, objectif]);
  }
  afficherEpargne(r, objectif, plusTot, comparaison, choisi);
}

function afficherEpargne(r, objectif, plusTot, comparaison, choisi) {
  const lex = DONNEES.lexiqueEpargne;
  cartes("cartes-epargne-cles", [
    { titre: "Capital final", valeur: eur(r.capitalFinal) },
    { titre: "Intérêts gagnés (nets)", valeur: eur(r.interetsNets), aide: lex["Intérêts composés"] },
    { titre: "Valeur en euros d'aujourd'hui", valeur: eur(r.capitalFinalReel), aide: lex["Pouvoir d'achat / euros d'aujourd'hui"] },
  ]);
  cartes("cartes-epargne-details", [
    { titre: "Total versé", valeur: eur(r.totalVerse) },
    { titre: "Impôt et prélèvements", valeur: eur(r.prelevements), aide: lex["Prélèvements sociaux et PFU"] },
    { titre: "Rendement net / an", valeur: pct(r.rendementNet), aide: lex["Taux brut / rendement net"] },
    { titre: "Rendement réel / an", valeur: pct(r.rendementReel), aide: lex["Rendement réel"],
      couleur: r.rendementReel < 0 ? DONNEES.couleurAlerte : DONNEES.couleurOk },
  ]);
  resumeMobile("epargne", objectif !== null
    ? [["Versement / mois", eur(r.versementMensuel)], ["Capital final", eur(r.capitalFinal, 0)], ["Rendement réel", pct(r.rendementReel)]]
    : [["Capital final", eur(r.capitalFinal, 0)], ["Intérêts nets", eur(r.interetsNets, 0)], ["Rendement réel", pct(r.rendementReel)]]);
  const lignes = [];
  if (objectif !== null) {
    lignes.push(`Versement mensuel nécessaire pour atteindre ${eur(objectif, 0)} : ${valeurColoree(eur(r.versementMensuel), DONNEES.couleurOk)}`);
  }
  lignes.push(`Part des intérêts dans le capital final : <b>${pct(r.partInterets, 1)}</b>`);
  const gain = r.capitalFinalReel - r.totalVerse;
  lignes.push(`Gain de pouvoir d'achat par rapport aux sommes versées : ` +
    `${valeurColoree(eur(gain, 0), gain >= 0 ? DONNEES.couleurOk : DONNEES.couleurAlerte)} (en euros d'aujourd'hui)`);
  $("indicateurs-epargne").innerHTML = lignes.join("<br>");

  $("graphique-epargne").innerHTML = barres("L'effet boule de neige : capital au 31 décembre de chaque année (en €)", {
    categories: r.annees.map((a) => String(a.annee)),
    series: [
      { nom: "Sommes versées", couleur: COULEURS.capital, valeurs: r.annees.map((a) => a.totalVerse) },
      { nom: "Intérêts nets cumulés", couleur: COULEURS.assurance, valeurs: r.annees.map((a) => a.capital - a.totalVerse) },
    ],
    ligne: { nom: "Capital en euros d'aujourd'hui", couleur: COULEURS.ligne, valeurs: r.annees.map((a) => a.capitalReel) },
    titreX: "Année",
  });
  $("explication-epargne").innerHTML = expliquerEpargne(r, { objectif, plusTot });

  const parObjectif = objectif !== null;
  const rouges = new Set();
  const classes = [];
  const lignesPlacements = comparaison.map(([p, res], i) => {
    const depassement = p.plafond ? anneeDepassement(res, p.plafond) : null;
    if (depassement) rouges.add(`${i},7`);
    classes.push(p.nom === choisi.nom ? "courante" : "");
    return [p.nom, pct(p.taux), pct(p.prelevements, 1), parObjectif ? eur(res.versementMensuel) : eur(res.capitalFinal, 0),
      eur(res.interetsNets, 0), eur(res.capitalFinalReel, 0), pct(res.rendementReel),
      depassement ? `dépassé an ${depassement}` : p.plafond ? "respecté" : "—"];
  });
  tableau("table-placements", ["Placement", "Taux brut", "Prélèvements", parObjectif ? "Versement nécessaire" : "Capital final",
    "Intérêts nets", "Valeur réelle", "Rendement réel", "Plafond"], lignesPlacements, { classes, rouges });
  tableau("table-annuelle", ["Année", "Versements", "Intérêts bruts", "Prélèvements", "Capital au 31/12", "Total versé", "Valeur réelle"],
    r.annees.map((a) => [String(a.annee), eur(a.versements), eur(a.interets), eur(a.prelevements), eur(a.capital),
      eur(a.totalVerse), eur(a.capitalReel)]));
}

// ============================================================================ démarrage

$("version").textContent = `v${DONNEES.version}`;
segmente(document.querySelector(".navigation .segmente"), "activite", (activite) => {
  etat.activite = activite;
  resumeMobile(activite, etat.resume[activite] || []);
  $("page-credit").hidden = activite !== "credit";
  $("page-epargne").hidden = activite !== "epargne";
  $("types-credit").classList.toggle("masque", activite !== "credit");
});
$("resume-mobile").addEventListener("click", () => {
  document.querySelector(`#page-${etat.activite} .resultats`).scrollIntoView({ behavior: "smooth" });
});
initialiserCredit();
initialiserEpargne();
resumeMobile("credit", etat.resume.credit);

// Liens directs vers un simulateur, pratiques pour partager avec des élèves :
// ?type=conso|auto|immo pour un type de crédit, ?simulateur=epargne pour l'épargne.
const adresse = new URLSearchParams(location.search);
if (PROFILS[adresse.get("type")]) document.querySelector(`#types-credit [data-type="${adresse.get("type")}"]`).click();
if (adresse.get("simulateur") === "epargne") document.querySelector('[data-activite="epargne"]').click();
