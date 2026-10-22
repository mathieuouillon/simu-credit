// Explications pas à pas — portage de simu_credit/pedagogie.py.
// Les textes sont identiques au module Python (vérifié par les tests) ; seule la mise en page HTML change.

import { calculTaeg, mensualite, moisBascule } from "./calcul.js";
import { DONNEES } from "./donnees.js";
import { dureeDoublement, tauxMensuel } from "./epargne.js";
import { dureeTexte, eur, nombre, pct } from "./formats.js";

const formule = (...lignes) => `<div class="formule">${lignes.join("<br>")}</div>`;
const tableau = (lignes) =>
  `<table class="etapes">${lignes.map(([l, v]) => `<tr><td>${l}</td><td>${v}</td></tr>`).join("")}</table>`;
const section = (numero, titre, corps) => `<h3>${numero}. ${titre}</h3>${corps}`;
const lexique = (entrees) =>
  Object.entries(entrees).map(([terme, def]) => `<p><b>${terme}</b> — ${def}</p>`).join("");
const liste = (points) => `<ul>${points.map((p) => `<li>${p}</li>`).join("")}</ul>`;

/** Contenu du panneau « Comment c'est calculé » pour un crédit. */
export function expliquer(r, { etapesMontant, mensualiteCible, budget, endettementMax, comparaison }) {
  const C = r.capital;
  const n = r.dureeMois;
  const t = r.tauxAnnuel / 100 / 12;
  const M = r.mensualiteHorsAssurance;
  const tauxAssMensuel = r.tauxAssurance / 100 / 12;
  const sections = [];

  // 1. Montant emprunté
  let corps = "";
  if (mensualiteCible !== null && mensualiteCible !== undefined) {
    const parEuro = mensualite(1, r.tauxAnnuel, n) + tauxAssMensuel;
    corps +=
      "<p>Vous êtes parti de la mensualité que vous voulez payer. On calcule d'abord la mensualité " +
      "pour <b>1 € emprunté</b>, puis on divise la mensualité visée par ce montant (la mensualité " +
      "est proportionnelle au capital) :</p>" +
      formule(
        `mensualité pour 1 € = t / (1 − (1 + t)<sup>−n</sup>) + assurance / 12 = ${nombre(parEuro, 6)} €`,
        `capital = ${eur(mensualiteCible)} / ${nombre(parEuro, 6)} = <b>${eur(C)}</b>`,
      );
  }
  if (etapesMontant.length) corps += "<p>Le montant à financer se déduit du projet :</p>" + tableau(etapesMontant);
  sections.push(section(1, "Le montant emprunté (C)", corps || `<p>C = <b>${eur(C)}</b></p>`));

  // 2. Taux mensuel
  sections.push(section(2, "Le taux mensuel (t)",
    "<p>En France, le taux mensuel est le taux annuel divisé par 12 (taux proportionnel).</p>" +
      formule(`t = ${pct(r.tauxAnnuel)} / 12 = <b>${pct(r.tauxAnnuel / 12, 4)}</b> = ${nombre(t, 6)}`)));

  // 3. Mensualité
  const formuleM = t > 0
    ? formule(
        "M = C × t / (1 − (1 + t)<sup>−n</sup>)",
        `M = ${nombre(C)} × ${nombre(t, 6)} / (1 − ${nombre(1 + t, 6)}<sup>−${n}</sup>)`,
        `M = <b>${eur(M)}</b> par mois, hors assurance`,
      )
    : formule("Taux nul : M = C / n", `M = ${nombre(C)} / ${n} = <b>${eur(M)}</b>`);
  sections.push(section(3, `La mensualité (M) sur n = ${n} mois`,
    "<p>Cette formule donne la mensualité <b>constante</b> qui rembourse exactement le capital " +
      "et tous les intérêts en n mois.</p>" + formuleM));

  // 4. Intérêts puis capital
  const premiere = r.tableau[0];
  const derniere = r.tableau.at(-1);
  const bascule = moisBascule(r.tableau);
  let phraseBascule = "";
  if (bascule === 1) phraseBascule = "Ici, la part de capital dépasse celle des intérêts dès la 1re échéance.";
  else if (bascule) {
    phraseBascule =
      `Jusqu'à l'échéance n°${bascule - 1}, vous payez surtout des intérêts. ` +
      `<b>À partir de l'échéance n°${bascule}</b> (année ${Math.floor((bascule - 1) / 12) + 1}), vous remboursez ` +
      "plus de capital que d'intérêts : c'est le <b>point de bascule</b>, surligné dans le tableau " +
      "d'amortissement.";
  }
  sections.push(section(4, "Dans chaque mensualité : d'abord les intérêts, puis le capital",
    "<p>Chaque mois, les intérêts sont calculés sur le <b>capital restant dû</b> ; le reste de la " +
      "mensualité rembourse le capital. Comme le capital restant dû baisse, les intérêts baissent et " +
      "la part de capital augmente.</p>" +
      formule(
        "<b>1re échéance</b>",
        `intérêts = capital restant dû × t = ${nombre(C)} × ${nombre(t, 6)} = ${eur(premiere.interets)}`,
        `capital remboursé = M − intérêts = ${nombre(M)} − ${nombre(premiere.interets)} = ${eur(premiere.capital)}`,
        `capital restant dû après = ${nombre(C)} − ${nombre(premiere.capital)} = ${eur(premiere.capitalRestant)}`,
        "",
        `<b>Dernière échéance (n°${n})</b> : intérêts ${eur(derniere.interets)}, capital ${eur(derniere.capital)}`,
      ) +
      `<p>${phraseBascule}</p>`));

  // 5. Assurance
  if (r.tauxAssurance <= 0) corps = "<p>Aucune assurance n'est retenue dans cette simulation.</p>";
  else if (!r.assuranceSurCrd) {
    corps = formule(
      "Sur le capital initial : assurance = C × taux / 12",
      `= ${nombre(C)} × ${pct(r.tauxAssurance)} / 12 = <b>${eur(r.assuranceMensuelle)}</b> par mois, ` +
        "le même montant chaque mois",
      `total = ${eur(r.assuranceMensuelle)} × ${n} = <b>${eur(r.coutAssurance)}</b>`,
    );
  } else {
    const surInitial = C * tauxAssMensuel * n;
    corps = formule(
      "Sur le capital restant dû : assurance du mois = capital restant dû × taux / 12",
      `1er mois = ${nombre(C)} × ${pct(r.tauxAssurance)} / 12 = ${eur(r.assuranceMensuelle)} ; ` +
        `dernier mois = ${eur(derniere.assurance)}`,
      `total = <b>${eur(r.coutAssurance)}</b>, contre ${eur(surInitial)} si elle portait ` + "sur le capital initial",
    );
  }
  sections.push(section(5, `L'assurance emprunteur (${pct(r.tauxAssurance)} par an)`, corps));

  // 6. Coût total
  sections.push(section(6, "Le coût total du crédit",
    formule(
      "coût total = intérêts + assurance + frais",
      `= ${nombre(r.coutInterets)} + ${nombre(r.coutAssurance)} + ${nombre(r.frais)} = <b>${eur(r.coutTotal)}</b>`,
      `montant total dû = capital + coût total = ${nombre(C)} + ${nombre(r.coutTotal)} = ${eur(r.montantTotalDu)}`,
    ) + `<p>Pour <b>1 € emprunté</b>, vous remboursez <b>${nombre(r.montantTotalDu / C)} €</b>.</p>`));

  // 7. TAEG décomposé
  if (!Number.isNaN(r.taeg)) {
    const i = (1 + r.taeg / 100) ** (1 / 12) - 1;
    const taegSeul = ((1 + t) ** 12 - 1) * 100;
    const taegAvecAssurance = calculTaeg(C, r.tableau.map((e) => e.mensualite + e.assurance));
    const decomposition = [
      ["Taux nominal", pct(r.tauxAnnuel)],
      ["+ effet de l'annualisation actuarielle (intérêts composés)", `+${nombre(taegSeul - r.tauxAnnuel)} pt`],
      ["+ effet de l'assurance", `+${nombre(taegAvecAssurance - taegSeul)} pt`],
      ["+ effet des frais payés au départ", `+${nombre(r.taeg - taegAvecAssurance)} pt`],
      ["<b>= TAEG</b>", `<b>${pct(r.taeg)}</b>`],
    ];
    sections.push(section(7, "Le TAEG",
      `<p>Vous empruntez ${eur(C)} mais payez ${eur(r.frais)} de frais au départ : vous recevez ` +
        `réellement <b>${eur(C - r.frais)}</b>. Le TAEG est le taux annuel qui égalise cette somme et ` +
        "tout ce que vous remboursez (mensualités + assurance). On trouve le taux mensuel i par essais " +
        "successifs (méthode numérique), puis on l'annualise :</p>" +
        formule(
          "C − frais = Σ<sub>k=1…n</sub> versement<sub>k</sub> / (1 + i)<sup>k</sup>",
          `i = ${pct(i * 100, 4)} par mois`,
          `TAEG = (1 + i)<sup>12</sup> − 1 = <b>${pct(r.taeg)}</b>`,
        ) +
        "<p>Pourquoi le TAEG est plus élevé que le taux nominal :</p>" +
        tableau(decomposition)));
  }

  // 8. Budget
  let numero = 8;
  if (budget && budget.revenus > 0) {
    const verdict = budget.endettement <= endettementMax ? "sous le seuil de 35 %" : "<b>au-dessus du seuil de 35 %</b>";
    sections.push(section(numero, "Le poids du crédit dans le budget", formule(
      "taux d'endettement = (mensualité + autres crédits) / revenus",
      `= (${nombre(budget.mensualiteCredit)} + ${nombre(budget.autresCredits)}) / ${nombre(budget.revenus)}` +
        ` = <b>${pct(budget.endettement)}</b>, ${verdict}`,
      "solde du mois = revenus − crédits − dépenses courantes",
      `= ${nombre(budget.revenus)} − ${nombre(budget.totalCredits)} − ${nombre(budget.totalDepenses)}` +
        ` = <b>${eur(budget.solde)}</b>`,
    )));
    numero += 1;
  }

  sections.push(`<h3>${numero}. À retenir</h3>${liste(aRetenir(r, comparaison))}`);
  sections.push(`<h3>Lexique</h3>${lexique(DONNEES.lexique)}`);
  const entete =
    "<h2>Comment c'est calculé</h2>" +
    "<p class='discret'>Chaque étape reprend les chiffres de la simulation affichée. " +
    "Modifiez un paramètre à gauche : les calculs se mettent à jour.</p>";
  return entete + sections.join("");
}

function aRetenir(r, comparaison) {
  const points = [];
  const partInterets = (r.tableau[0].interets / r.mensualiteHorsAssurance) * 100;
  points.push(
    `Votre 1re mensualité contient <b>${pct(partInterets, 0)} d'intérêts</b> ; la dernière presque ` +
      "uniquement du capital.",
  );
  points.push(
    `Les intérêts représentent <b>${pct((r.coutInterets / r.montantTotalDu) * 100, 0)}</b> ` +
      "de tout ce que vous remboursez.",
  );
  const durees = comparaison.map((c) => c.dureeMois);
  const idx = durees.indexOf(r.dureeMois);
  if (idx >= 0) {
    for (const autre of [idx + 1 < comparaison.length ? comparaison[idx + 1] : null, idx > 0 ? comparaison[idx - 1] : null]) {
      if (autre === null) continue;
      const plusLong = autre.dureeMois > r.dureeMois;
      const sur = `Sur ${dureeTexte(autre.dureeMois)} (taux ${pct(autre.tauxAnnuel)})`;
      const dCout = autre.coutTotal - r.coutTotal;
      if (Math.abs(autre.capital - r.capital) < 1) {
        const dMens = autre.mensualiteTotale - r.mensualiteTotale;
        points.push(
          `${sur} : mensualité ${dMens < 0 ? "plus basse" : "plus haute"} de ` +
            `<b>${eur(Math.abs(dMens), 0)}</b>, mais coût total ` +
            `${dCout > 0 ? "plus élevé" : "plus faible"} de <b>${eur(Math.abs(dCout), 0)}</b>.`,
        );
      } else {
        const dCap = autre.capital - r.capital;
        points.push(
          `${sur} : vous pourriez emprunter <b>${dCap > 0 ? eur(dCap, 0) : eur(-dCap, 0)}` +
            `</b> ${dCap > 0 ? "de plus" : "de moins"}, pour un coût total ` +
            `${dCout > 0 ? "plus élevé" : "plus faible"} de <b>${eur(Math.abs(dCout), 0)}</b>.`,
        );
      }
      if (plusLong) points[points.length - 1] += " Allonger la durée allège la mensualité mais coûte plus cher au total.";
    }
  }
  return points;
}

/** Contenu du panneau « Comment c'est calculé » pour une épargne. */
export function expliquerEpargne(r, { objectif, plusTot }) {
  const n = 12 * r.dureeAnnees;
  const i = tauxMensuel(r.tauxAnnuel);
  const C0 = r.capitalInitial;
  const V = r.versementMensuel;
  const f = r.tauxPrelevement;
  const sections = [];

  sections.push(section(1, "Du taux annuel au taux mensuel (i)",
    "<p>Pour l'épargne, on utilise le taux mensuel <b>équivalent</b> : placé 12 mois, il redonne " +
      "exactement le taux annuel annoncé. (Pour un crédit, la convention française divise " +
      "simplement par 12.)</p>" +
      formule(
        `i = (1 + ${pct(r.tauxAnnuel)})<sup>1/12</sup> − 1 = <b>${pct(i * 100, 4)}</b> par mois`,
        `vérification : (1 + i)<sup>12</sup> − 1 = ${pct(((1 + i) ** 12 - 1) * 100)}`,
      )));

  const a1 = r.annees[0];
  sections.push(section(2, "Les intérêts composés",
    "<p>Chaque mois, le solde rapporte i ; ces intérêts s'ajoutent au solde et rapportent à leur " +
      "tour : ce sont les <b>intérêts composés</b>.</p>" +
      formule(
        `1er mois : intérêts = ${nombre(C0)} × ${nombre(i, 6)} = ${eur(C0 * i)}, puis versement de ${eur(V)}`,
        `sur toute la 1re année : ${eur(a1.interets)} d'intérêts bruts`,
        `sur la dernière année : ${eur(r.annees.at(-1).interets)} d'intérêts bruts`,
      ) +
      "<p>Les intérêts de la dernière année sont bien plus élevés que ceux de la première : " +
      "le capital qui rapporte a grossi, intérêts compris.</p>"));

  let corps;
  if (f === 0) {
    let formuleF;
    if (i > 0) {
      const q = (1 + i) ** n;
      formuleF = formule(
        "capital final = C<sub>0</sub> × (1 + i)<sup>n</sup> + V × ((1 + i)<sup>n</sup> − 1) / i",
        `= ${nombre(C0)} × ${nombre(1 + i, 6)}<sup>${n}</sup> + ${nombre(V)} × (${nombre(q, 4)} − 1) / ${nombre(i, 6)}`,
        `= ${nombre(C0 * q)} + ${nombre((V * (q - 1)) / i)} = <b>${eur(r.capitalFinal)}</b>`,
      );
    } else {
      formuleF = formule(
        "Taux nul : capital final = C<sub>0</sub> + V × n",
        `= ${nombre(C0)} + ${nombre(V)} × ${n} = <b>${eur(r.capitalFinal)}</b>`,
      );
    }
    corps = `<p>Avec un capital de départ C<sub>0</sub>, un versement V en fin de chaque mois et n = ${n} mois :</p>` + formuleF;
  } else {
    corps =
      "<p>Les intérêts étant taxés chaque année, le calcul se fait année par année (voir le " +
      `tableau annuel) : on obtient <b>${eur(r.capitalFinal)}</b>.</p>`;
  }
  sections.push(section(3, `Le capital final après ${r.dureeAnnees} ans`, corps + tableau([
    ["Total versé (capital de départ + versements)", eur(r.totalVerse)],
    ["+ intérêts bruts", eur(r.interetsBruts)],
    ["− impôt et prélèvements sociaux", eur(r.prelevements)],
    ["<b>= Capital final</b>", `<b>${eur(r.capitalFinal)}</b>`],
  ])));

  corps = f > 0
    ? `<p>Chaque 31 décembre, ${pct(f, 1)} des intérêts de l'année sont prélevés.</p>` +
      formule(
        `1re année : ${nombre(a1.interets)} × ${pct(f, 1)} = ${eur(a1.prelevements)}`,
        `rendement net = ${pct(r.tauxAnnuel)} × (1 − ${pct(f, 1)}) = <b>${pct(r.rendementNet)}</b> par an`,
        `total prélevé en ${r.dureeAnnees} ans : <b>${eur(r.prelevements)}</b>`,
      )
    : "<p>Ce placement est exonéré : les intérêts ne sont ni imposés ni soumis aux prélèvements sociaux.</p>";
  sections.push(section(4, "Impôt et prélèvements sociaux", corps));

  const perte = r.rendementReel < 0;
  sections.push(section(5, `L'inflation (${pct(r.inflation, 1)} par an)`,
    "<p>Pour savoir ce que le capital final permettra d'acheter, on le ramène aux prix d'aujourd'hui :</p>" +
      formule(
        `valeur en euros d'aujourd'hui = ${nombre(r.capitalFinal)} / (1 + ${pct(r.inflation, 1)})<sup>${r.dureeAnnees}</sup>` +
          ` = <b>${eur(r.capitalFinalReel)}</b>`,
        `rendement réel = (1 + ${pct(r.rendementNet)}) / (1 + ${pct(r.inflation, 1)}) − 1 = <b>${pct(r.rendementReel)}</b> par an`,
      ) +
      (perte
        ? "<p><b>Le rendement réel est négatif</b> : le montant épargné augmente, mais il permet d'acheter de moins en moins.</p>"
        : "<p>Le rendement réel est positif : l'épargne gagne du pouvoir d'achat.</p>")));

  let numero = 6;
  if (objectif !== null && objectif !== undefined) {
    sections.push(section(numero, "Le versement pour atteindre l'objectif",
      "<p>Le capital final augmente proportionnellement au versement mensuel : " +
        "capital final = A + B × V, où A est ce que devient le capital de départ seul et B ce que " +
        "rapporte 1 € versé chaque mois. On en déduit V = (objectif − A) / B.</p>" +
        formule(`objectif ${eur(objectif)} → versement mensuel <b>${eur(V)}</b>`)));
    numero += 1;
  }

  const points = [`Les intérêts représentent <b>${pct(r.partInterets, 0)}</b> du capital final.`];
  const doublement = dureeDoublement(r.rendementNet);
  if (Number.isFinite(doublement)) {
    points.push(
      `À ${pct(r.rendementNet)} net par an, une somme placée double en <b>${nombre(doublement, 0)} ans</b> ` +
        `(règle de 72 : 72 / ${nombre(r.rendementNet, 2)} ≈ ${nombre(72 / r.rendementNet, 0)} ans).`,
    );
  }
  if (plusTot) {
    points.push(
      "En commençant <b>5 ans plus tôt</b> avec le même versement, on aurait " +
        `<b>${eur(plusTot.capitalFinal, 0)}</b>, soit ${eur(plusTot.capitalFinal - r.capitalFinal, 0)} de plus ` +
        `pour seulement ${eur(plusTot.totalVerse - r.totalVerse, 0)} versés en plus.`,
    );
  }
  if (perte) points.push("Avec une inflation supérieure au rendement net, l'épargne perd du pouvoir d'achat.");
  sections.push(`<h3>${numero}. À retenir</h3>${liste(points)}`);
  sections.push(`<h3>Lexique</h3>${lexique(DONNEES.lexiqueEpargne)}`);
  const entete =
    "<h2>Comment c'est calculé</h2>" +
    "<p class='discret'>Chaque étape reprend les chiffres de la simulation affichée.</p>";
  return entete + sections.join("");
}

/** Texte d'un fragment HTML, normalisé comme dans outils/generer_web.py (pour les tests). */
export const texte = (html) =>
  html.replace(/<style>[\s\S]*?<\/style>/g, " ").replace(/<[^>]+>/g, " ").replace(/\s+/g, " ").trim();
