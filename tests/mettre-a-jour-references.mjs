// Réenregistre les valeurs attendues de tests/references.json avec le code actuel.
// À n'utiliser qu'après avoir vérifié que les écarts signalés par « npm test » sont voulus
// (par exemple un texte d'explication reformulé) : sinon on masquerait une erreur de calcul.
//
//   node tests/mettre-a-jour-references.mjs

import { readFileSync, writeFileSync } from "node:fs";

import { recalculer } from "./references.mjs";

const fichier = new URL("./references.json", import.meta.url);
const references = JSON.parse(readFileSync(fichier, "utf-8"));
const misesAJour = recalculer(references);
misesAJour._origine = `${references._origine} Réenregistrées le ${new Date().toISOString().slice(0, 10)}.`;
writeFileSync(fichier, JSON.stringify(misesAJour));
console.log("tests/references.json mis à jour.");
