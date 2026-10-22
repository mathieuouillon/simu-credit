// Mise en forme des nombres à la française — portage de simu_credit/formats.py.
// Reproduit exactement le formatage de Python (f"{x:,.2f}"), arrondi compris.

/** Chaîne identique à f"{x:.{d}f}" en Python : arrondi exact, égalités au chiffre pair. */
export function fixe(x, d) {
  const negatif = x < 0 || Object.is(x, -0);
  const a = Math.abs(x);
  let texte = a.toFixed(d);
  // toFixed arrondit les égalités exactes vers le haut ; Python les arrondit au chiffre pair
  const exact = a.toFixed(Math.min(100, d + 70));
  const [entier, decimales = ""] = exact.split(".");
  const reste = decimales.slice(d);
  if (/^50*$/.test(reste)) {
    const tronque = d ? `${entier}.${decimales.slice(0, d)}` : entier;
    if (Number(tronque.at(-1)) % 2 === 0) texte = tronque;
  }
  return (negatif ? "-" : "") + texte;
}

/** 12 345,67 (espace fine insécable comme séparateur de milliers). */
export function nombre(valeur, decimales = 2) {
  const texte = fixe(valeur, decimales);
  const signe = texte.startsWith("-") ? "-" : "";
  const [entier, fraction] = texte.replace("-", "").split(".");
  const groupes = entier.replace(/\B(?=(\d{3})+(?!\d))/g, " ");
  return signe + groupes + (fraction !== undefined ? `,${fraction}` : "");
}

export const eur = (valeur, decimales = 2) => `${nombre(valeur, decimales)} €`;

export const pct = (valeur, decimales = 2) => (Number.isNaN(valeur) ? "—" : `${nombre(valeur, decimales)} %`);

export function dureeTexte(dureeMois) {
  const annees = Math.floor(dureeMois / 12);
  const mois = dureeMois % 12;
  if (!annees) return `${dureeMois} mois`;
  const texte = `${annees} an${annees > 1 ? "s" : ""}`;
  return mois ? `${texte} ${mois} mois` : texte;
}

/** Somme de flottants identique à sum() de Python ≥ 3.12 (sommation compensée de Neumaier). */
export function somme(valeurs) {
  let total = 0;
  let c = 0;
  for (const x of valeurs) {
    const t = total + x;
    if (Math.abs(total) >= Math.abs(x)) c += total - t + x;
    else c += x - t + total;
    total = t;
  }
  return c && Number.isFinite(c) ? total + c : total;
}

/** round(x, n) de Python : arrondi exact de la valeur binaire, égalités au chiffre pair. */
export const arrondi = (x, n) => Number(fixe(x, n));
