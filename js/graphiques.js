// Graphiques SVG légers (sans bibliothèque) : anneau, barres empilées avec courbe, barres horizontales.

import { nombre } from "./formats.js";

const PAR_DEFAUT = {
  capital: "#3b82f6",
  interets: "#f59e0b",
  assurance: "#10b981",
  frais: "#8b5cf6",
  depenses: "#a3acb9",
  alerte: "#dc2626",
  ligne: "#374151",
  grille: "#eef0f3",
  axe: "#d1d5db",
  fond: "#ffffff",
};

/** Couleurs des graphiques, lues dans la feuille de style (variables --graphe-capital, etc.). */
export const COULEURS = new Proxy(PAR_DEFAUT, {
  get(defauts, nom) {
    const valeur = getComputedStyle(document.documentElement).getPropertyValue(`--graphe-${nom}`).trim();
    return valeur || defauts[nom];
  },
});

const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
const legende = (elements) =>
  `<div class="legende">${elements.map(([nom, c]) => `<span style="--c:${c}">${esc(nom)}</span>`).join("")}</div>`;

/** Graduations « rondes » (1, 2, 2,5, 5 × 10^k) couvrant 0 → max. */
function graduations(max, nombreVoulu = 5) {
  if (!(max > 0)) return [0, 1];
  const brut = max / nombreVoulu;
  const puissance = 10 ** Math.floor(Math.log10(brut));
  const pas = [1, 2, 2.5, 5, 10].map((m) => m * puissance).find((p) => p >= brut);
  const valeurs = [];
  for (let v = 0; v <= max + pas * 0.001; v += pas) valeurs.push(v);
  if (valeurs.at(-1) < max) valeurs.push(valeurs.at(-1) + pas);
  return valeurs;
}

/** Anneau de répartition ; parts : [{ nom, valeur, couleur }]. */
export function anneau(titre, parts) {
  const visibles = parts.filter((p) => p.valeur > 0);
  const total = visibles.reduce((s, p) => s + p.valeur, 0) || 1;
  const r = 70;
  const circonference = 2 * Math.PI * r;
  let decalage = 0;
  const arcs = visibles.map((p) => {
    const longueur = (p.valeur / total) * circonference;
    const arc = `<circle cx="100" cy="100" r="${r}" fill="none" stroke="${p.couleur}" stroke-width="36"
      stroke-dasharray="${longueur} ${circonference - longueur}" stroke-dashoffset="${-decalage}"
      transform="rotate(-90 100 100)"><title>${esc(p.nom)}</title></circle>`;
    decalage += longueur;
    return arc;
  });
  const separations = visibles.length > 1
    ? visibles.map((_, k) => {
        const angle = (visibles.slice(0, k).reduce((s, p) => s + p.valeur, 0) / total) * 2 * Math.PI - Math.PI / 2;
        return `<line x1="${100 + 52 * Math.cos(angle)}" y1="${100 + 52 * Math.sin(angle)}" x2="${100 + 88 * Math.cos(angle)}"
          y2="${100 + 88 * Math.sin(angle)}" stroke="${COULEURS.fond}" stroke-width="2"/>`;
      }).join("")
    : "";
  return `<div class="graphique"><h5>${esc(titre)}</h5><div class="anneau">
    <svg viewBox="0 0 200 200" role="img" aria-label="${esc(titre)}">${arcs.join("")}${separations}</svg>
    ${legende(visibles.map((p) => [`${p.nom} ${Math.round((p.valeur / total) * 100)} %`, p.couleur]))}</div></div>`;
}

/** Barres verticales empilées, avec une courbe facultative.
 *  series : [{ nom, couleur, valeurs }] ; ligne : { nom, couleur, valeurs } ou null. */
export function barres(titre, { categories, series, ligne = null, titreX = "" }) {
  const L = 640, H = 300, g = 58, d = 12, h = 12, b = titreX ? 46 : 30;
  const n = categories.length;
  const totaux = categories.map((_, k) => series.reduce((s, serie) => s + serie.valeurs[k], 0));
  const max = Math.max(...totaux, ...(ligne ? ligne.valeurs : [0]));
  const ticks = graduations(max);
  const haut = ticks.at(-1) || 1;
  const y = (v) => h + (H - h - b) * (1 - v / haut);
  const bande = (L - g - d) / n;
  const x = (k) => g + bande * k + bande / 2;
  const largeur = Math.max(2, bande * 0.62);

  let svg = "";
  for (const t of ticks) {
    svg += `<line x1="${g}" x2="${L - d}" y1="${y(t)}" y2="${y(t)}" stroke="${COULEURS.grille}"/>`;
    svg += `<text x="${g - 8}" y="${y(t) + 4}" text-anchor="end">${nombre(t, 0)}</text>`;
  }
  categories.forEach((cat, k) => {
    let base = 0;
    for (const serie of series) {
      const v = serie.valeurs[k];
      if (v > 0) {
        svg += `<rect x="${x(k) - largeur / 2}" y="${y(base + v)}" width="${largeur}" height="${y(base) - y(base + v)}"
          fill="${serie.couleur}"><title>${esc(cat)} · ${esc(serie.nom)} : ${nombre(v, 0)} €</title></rect>`;
      }
      base += v;
    }
    const afficher = n <= 15 || k === 0 || Number(cat) % 5 === 0;
    if (afficher) svg += `<text x="${x(k)}" y="${H - b + 16}" text-anchor="middle">${esc(cat)}</text>`;
  });
  if (ligne) {
    const points = ligne.valeurs.map((v, k) => `${x(k)},${y(v)}`).join(" ");
    svg += `<polyline points="${points}" fill="none" stroke="${ligne.couleur}" stroke-width="2" stroke-dasharray="6 4"/>`;
  }
  svg += `<line x1="${g}" x2="${L - d}" y1="${y(0)}" y2="${y(0)}" stroke="${COULEURS.axe}"/>`;
  if (titreX) svg += `<text x="${(g + L - d) / 2}" y="${H - 6}" text-anchor="middle" font-weight="600">${esc(titreX)}</text>`;
  const elements = series.map((s) => [s.nom, s.couleur]).concat(ligne ? [[ligne.nom, ligne.couleur]] : []);
  return `<div class="graphique"><h5>${esc(titre)}</h5>
    <svg viewBox="0 0 ${L} ${H}" role="img" aria-label="${esc(titre)}">${svg}</svg>${legende(elements)}</div>`;
}

/** Barres horizontales ; lignes : [{ libelle, valeur, couleur }], groupes : [[nom, couleur]] pour la légende. */
export function barresHorizontales(titre, lignes, groupes, titreValeurs) {
  const L = 640, gauche = 230, d = 16, rangee = 30, bas = 46;
  const H = lignes.length * rangee + bas + 8;
  const max = Math.max(...lignes.map((l) => l.valeur), 0);
  const ticks = graduations(max);
  const haut = ticks.at(-1) || 1;
  const x = (v) => gauche + (L - gauche - d) * (v / haut);
  let svg = "";
  for (const t of ticks) {
    svg += `<line x1="${x(t)}" x2="${x(t)}" y1="4" y2="${H - bas}" stroke="${COULEURS.grille}"/>`;
    svg += `<text x="${x(t)}" y="${H - bas + 16}" text-anchor="middle">${nombre(t, 0)}</text>`;
  }
  lignes.forEach((l, k) => {
    const yc = 8 + k * rangee + rangee / 2;
    svg += `<text x="${gauche - 10}" y="${yc + 4}" text-anchor="end">${esc(l.libelle)}</text>`;
    svg += `<rect x="${gauche}" y="${yc - 9}" width="${Math.max(0, x(l.valeur) - gauche)}" height="18" rx="2" fill="${l.couleur}">
      <title>${esc(l.libelle)} : ${nombre(l.valeur, 0)} €</title></rect>`;
  });
  svg += `<text x="${(gauche + L - d) / 2}" y="${H - 8}" text-anchor="middle" font-weight="600">${esc(titreValeurs)}</text>`;
  return `<div class="graphique"><h5>${esc(titre)}</h5>
    <svg viewBox="0 0 ${L} ${H}" role="img" aria-label="${esc(titre)}">${svg}</svg>${legende(groupes)}</div>`;
}
