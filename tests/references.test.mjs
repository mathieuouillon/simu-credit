// Non-régression : le code actuel doit redonner les résultats de tests/references.json
// (nombres à 1e-9 près en relatif, textes affichés au caractère près).

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";

import { recalculer } from "./references.mjs";

const REFERENCES = JSON.parse(readFileSync(new URL("./references.json", import.meta.url), "utf-8"));
const ACTUEL = recalculer(REFERENCES);

/** Comparaison profonde : nombres à 1e-9 près (relatif), tout le reste à l'identique. */
function comparer(obtenu, attendu, chemin) {
  if (typeof attendu === "number") {
    assert.equal(typeof obtenu, "number", `${chemin} : ${obtenu} n'est pas un nombre`);
    const tolerance = 1e-9 * Math.max(1, Math.abs(attendu));
    assert.ok(Math.abs(obtenu - attendu) <= tolerance, `${chemin} : ${obtenu} ≠ ${attendu}`);
  } else if (Array.isArray(attendu)) {
    assert.ok(Array.isArray(obtenu), `${chemin} : tableau attendu`);
    assert.equal(obtenu.length, attendu.length, `${chemin} : longueur`);
    attendu.forEach((v, k) => comparer(obtenu[k], v, `${chemin}[${k}]`));
  } else if (attendu !== null && typeof attendu === "object") {
    assert.deepEqual(Object.keys(obtenu).sort(), Object.keys(attendu).sort(), `${chemin} : clés`);
    for (const [cle, v] of Object.entries(attendu)) comparer(obtenu[cle], v, `${chemin}.${cle}`);
  } else {
    assert.equal(obtenu, attendu, chemin);
  }
}

for (const partie of ["formats", "durees", "credit", "tauxReference", "scenarios", "epargne"]) {
  test(`références : ${partie} (${REFERENCES[partie].length} cas)`, () => {
    comparer(ACTUEL[partie], REFERENCES[partie], partie);
  });
}

test("les références contiennent des explications pas à pas", () => {
  const explications = [...REFERENCES.scenarios, ...REFERENCES.epargne].filter((c) => c.attendu?.explication);
  assert.ok(explications.length >= 50);
});
