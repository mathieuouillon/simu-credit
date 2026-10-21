# Simulateur de crédit

> **Outil pédagogique**, destiné uniquement à l'enseignement. Les résultats ne constituent ni une offre
> de prêt, ni un conseil financier. Les taux de référence sont des exemples relevés à une date donnée.

Application de bureau (PySide6 / Qt) pour simuler un crédit **à la consommation**, **auto** ou **immobilier**.
Un menu « Type de crédit » adapte le formulaire (champs affichés et valeurs par défaut) ; les résultats se recalculent à chaque modification.

## Lancer

```bash
uv run simu-credit
```

## Fonctionnalités

- **Comment c'est calculé** : onglet qui détaille chaque étape avec les chiffres de la simulation en cours
  (montant emprunté, taux mensuel, formule de la mensualité, part intérêts/capital, assurance, coût total,
  TAEG décomposé en effet actuariel + assurance + frais, poids dans le budget), une rubrique « À retenir »
  générée automatiquement (effet d'une durée plus longue ou plus courte, part des intérêts…) et un lexique.
- **Point de bascule** : la première échéance où l'on rembourse plus de capital que d'intérêts est expliquée
  et surlignée dans le tableau d'amortissement.
- **Lexique en infobulle** sur les cartes de résultats (TAEG, taux nominal, assurance…).
- **Deux modes** : partir du **montant** (prix du bien ou du véhicule) ou de la **mensualité** qu'on veut payer.
  Dans ce second mode, le simulateur donne le montant empruntable et, en auto et en immobilier, le prix maximum
  du véhicule ou du bien.
- **Taux de référence** (case « Réf. ») : taux pré-rempli selon la durée, à partir de taux relevés en octobre 2026
  (Meilleurtaux pour l'immobilier, interpolé entre 10, 15, 20 et 25 ans ; Cetelem pour la conso et l'auto).
  Décocher la case pour saisir son propre taux. Les grilles sont dans `TAUX_MEILLEURTAUX` et `TAUX_CETELEM`
  ([gui.py](simu_credit/gui.py)) et sont à mettre à jour de temps en temps.
- **Assurance** calculée sur le capital initial (montant fixe) ou sur le capital restant dû (montant qui baisse).
- **Comparer les durées** : mensualité, coût total, TAEG (et endettement en immobilier) pour plusieurs durées
  côte à côte ; un double-clic sur une ligne retient cette durée.
- **Budget du foyer** (pour les trois types) : revenus, autres crédits et dépenses courantes (logement,
  alimentation, transport, énergie, abonnements, loisirs). L'onglet « Budget » montre la part du crédit dans
  le revenu et dans l'ensemble des dépenses, le taux d'endettement, le solde du mois (en rouge s'il est
  négatif) et un graphique de répartition du revenu. Les postes et leurs valeurs par défaut sont dans
  `POSTES_BUDGET` ([gui.py](simu_credit/gui.py)).
- **Consommation** : avertissement hors du cadre légal (200 € à 75 000 €).
- **Auto** : apport et reprise ; part financée et coût total du véhicule.
- **Immobilier** : ancien ou neuf (frais de notaire 7,5 % / 2,5 %, modifiables), travaux, apport, garantie ;
  capacité d'emprunt au seuil HCSF de 35 % d'endettement.
- Pour chaque crédit : mensualité, **TAEG** (actuariel, frais et assurance inclus), coût total, graphiques,
  tableau d'amortissement mensuel exportable en CSV (format Excel français).

## Hypothèses de calcul

- Prêt amortissable à mensualités constantes, taux mensuel = taux annuel / 12 (convention française).
- Avec une assurance sur le capital restant dû, la mensualité affichée est la 1re, la plus élevée : c'est elle
  qui sert au taux d'endettement et au mode « mensualité ».
- Frais (dossier, garantie) payés au départ : ils entrent dans le coût total et le TAEG.

## Validation

Les tests recalculent à l'identique des exemples publiés en octobre 2026 : le tableau 250 000 € sur
10 à 25 ans de Meilleurtaux (mensualités et coûts à l'euro près), l'exemple Cetelem (15 000 € sur 48 mois,
TAEG 5,49 %) et un exemple BNP Paribas (150 000 € sur 25 ans à 2,31 %).

## Application autonome (sans installation)

L'application peut être livrée comme un fichier qu'on ouvre d'un double-clic, sans Python ni installation.
Elle est construite avec PyInstaller, **sur chaque système pour ce système** :

```bash
uv run pyinstaller simu_credit.spec --noconfirm
```

- **macOS** : `dist/Simulateur de credit.app` (≈ 120 Mo, 39 Mo zippé). À distribuer zippé :
  `ditto -c -k --keepParent "dist/Simulateur de credit.app" Simulateur-de-credit-macOS.zip`
- **Windows** : `dist/SimulateurCredit.exe`, un seul fichier.

Sans Windows sous la main, le workflow [construire.yml](.github/workflows/construire.yml) construit
les versions Windows, macOS Apple Silicon et macOS Intel sur GitHub (gratuit pour un dépôt public) :
onglet *Actions* > *Construire l'application* > *Run workflow*, puis télécharger les fichiers produits.

**Premier lancement** (l'application n'est pas signée par un éditeur reconnu) :

- **macOS** : double-clic, puis *Réglages Système > Confidentialité et sécurité > Ouvrir quand même*.
  Ou, dans le Terminal : `xattr -dr com.apple.quarantine "Simulateur de credit.app"`.
- **Windows** : à l'écran bleu « Windows a protégé votre ordinateur », cliquer
  *Informations complémentaires > Exécuter quand même*.

Ces avertissements disparaissent avec une signature officielle (compte développeur Apple, 99 $/an ;
certificat de signature de code sous Windows).

## Tests

```bash
uv run pytest
```

Le moteur de calcul (`simu_credit/calcul.py`) ne dépend pas de l'interface et peut être utilisé seul.
