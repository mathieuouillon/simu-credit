<img src="logo.svg" width="96" alt="Logo">

# Simulateur de crédit et d'épargne

**https://mathieuouillon.github.io/simu-credit/** — à utiliser directement dans le navigateur, sans rien installer,
sur ordinateur, tablette ou téléphone.

> **Outil pédagogique**, destiné uniquement à l'enseignement. Les résultats ne constituent ni une offre
> de prêt ou de placement, ni un conseil financier. Les taux de référence sont des exemples relevés à une date donnée.

## Fonctionnalités

**Crédit** (consommation, auto, immobilier)

- Calcul à partir du **montant** ou de la **mensualité** souhaitée (montant empruntable, prix maximum du bien
  ou du véhicule).
- **Taux de référence** pré-rempli selon la durée (case « Réf. ») ou saisi librement ; assurance sur le capital
  initial ou sur le capital restant dû ; frais de dossier, garantie, frais de notaire, travaux, apport, reprise.
- Mensualité, **TAEG**, coût total, graphiques, **comparaison de plusieurs durées**, tableau d'amortissement
  (export CSV, point de bascule capital / intérêts surligné).
- **Budget du foyer** : part du crédit dans le revenu, taux d'endettement (seuil HCSF de 35 %), solde du mois,
  capacité d'emprunt en immobilier.

**Épargne** (Livret A, LDDS, LEP, PEL, assurance vie en fonds euros, ou placement personnalisé)

- À partir des **versements** (capital final) ou d'un **objectif** (versement mensuel nécessaire).
- Taux et prélèvements de référence (case « Réf. ») ou modifiables ; inflation, rendement net et **réel**,
  valeur en euros d'aujourd'hui ; avertissement en cas de dépassement d'un plafond.
- Graphique « boule de neige », comparaison des placements, tableau année par année.

**Pédagogie** : l'onglet **« Comment c'est calculé »** détaille chaque formule avec les chiffres de la simulation
(mensualité, intérêts puis capital, TAEG décomposé, intérêts composés, inflation, règle de 72…), suivi d'une
rubrique « À retenir » et d'un lexique ; les définitions apparaissent aussi au survol des résultats.

Tous les calculs sont faits dans le navigateur : aucune donnée n'est envoyée.

## Hypothèses de calcul

- **Crédit** : prêt amortissable à mensualités constantes ; taux mensuel = taux annuel / 12 (convention
  française) ; TAEG actuariel incluant frais et assurance ; frais payés au départ. Avec une assurance sur le
  capital restant dû, la mensualité affichée est la première, la plus élevée.
- **Épargne** : taux mensuel équivalent (1 + r)^(1/12) − 1 ; versements en fin de mois ; intérêts capitalisés
  chaque mois ; prélèvements retenus le 31 décembre ; l'impôt sur le revenu de l'assurance vie, dû au retrait,
  n'est pas simulé.

## Organisation du code

Site statique, sans dépendance ni étape de construction :

| Fichier | Rôle |
|---|---|
| [index.html](index.html), [style.css](style.css) | page et mise en forme |
| [js/donnees.js](js/donnees.js) | **taux de référence**, profils de crédit, placements, budget, lexiques — à mettre à jour ici |
| [js/calcul.js](js/calcul.js) | moteur de crédit : mensualité, tableau d'amortissement, TAEG, budget |
| [js/epargne.js](js/epargne.js) | moteur d'épargne |
| [js/scenarios.js](js/scenarios.js) | logique par type de crédit : montant emprunté, indicateurs, avertissements |
| [js/pedagogie.js](js/pedagogie.js) | explications pas à pas |
| [js/formats.js](js/formats.js) | nombres à la française |
| [js/graphiques.js](js/graphiques.js) | graphiques SVG |
| [js/app.js](js/app.js) | interface : formulaire, onglets, affichage |

## Tests

```bash
npm test
```

- **Exemples publiés** recalculés à l'identique : Meilleurtaux (250 000 € sur 10 à 25 ans), Cetelem
  (15 000 € sur 48 mois, TAEG 5,49 %), BNP Paribas, Livret A.
- **Audit** sur des centaines de prêts et d'épargnes tirés au hasard : chaque résultat est recalculé par une
  méthode indépendante (dichotomie, méthode de Newton, définition réglementaire du TAEG, formule fermée).
- **Non-régression** : [tests/references.json](tests/references.json) contient des cas validés par
  l'implémentation Python d'origine ; le code doit les reproduire (chiffres à 10⁻⁹ près, textes au caractère
  près). Après un changement voulu des résultats (texte reformulé, nouvelle règle), relire les écarts signalés
  puis réenregistrer les références :

```bash
node tests/mettre-a-jour-references.mjs
```

## Publication

Chaque modification de la branche `main` relance les tests puis publie le site sur GitHub Pages
([site.yml](.github/workflows/site.yml)) ; si un test échoue, le site n'est pas mis à jour.

Pour l'essayer en local :

```bash
npm run site
```

puis ouvrir http://localhost:8765.

## Historique

Les versions 0.1 et 0.2 étaient une application de bureau en Python (PySide6), toujours téléchargeable dans les
[releases](https://github.com/mathieuouillon/simu-credit/releases) ; son code reste dans l'historique Git
(étiquette `v0.2.0`). Depuis la version 0.3, le site web est la seule version maintenue.
