// Outils communs aux tests.

import assert from "node:assert/strict";

/** Égalité numérique à `ecart` près (absolu, 1e-9 par défaut, relatif au-delà de 1). */
export function proche(obtenu, attendu, ecart = 1e-9) {
  const tolerance = ecart * Math.max(1, ecart < 1e-6 ? Math.abs(attendu) : 1);
  assert.ok(Math.abs(obtenu - attendu) <= tolerance, `${obtenu} ≠ ${attendu} (écart ${obtenu - attendu})`);
}

/** Générateur pseudo-aléatoire à graine fixe (mulberry32) : des cas « au hasard » mais reproductibles. */
export function aleatoire(graine) {
  let etat = graine >>> 0;
  const suivant = () => {
    etat = (etat + 0x6d2b79f5) >>> 0;
    let t = etat;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
  return {
    uniforme: (min, max) => min + (max - min) * suivant(),
    entier: (min, max) => min + Math.floor(suivant() * (max - min + 1)),
    choix: (liste) => liste[Math.floor(suivant() * liste.length)],
    hasard: suivant,
  };
}
