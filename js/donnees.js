// Données de référence du simulateur : taux, profils de crédit, placements, budget, lexiques.
// C'est ici qu'on met à jour les taux. Après une modification, lancer les tests (npm test) :
// les tests de non-régression signalent tout changement de résultat (voir tests/references.test.mjs).

// --------------------------------------------------------------------------- taux de référence (octobre 2026)

/** Crédit à la consommation et auto : 15 000 € / 48 mois, TAEG fixe 5,49 % sans frais ni assurance (Cetelem). */
const TAUX_CETELEM = [[48, 5.36]];
/** Crédit immobilier : taux moyens avant négociation, par durée en mois (Meilleurtaux, 19/10/2026). */
const TAUX_MEILLEURTAUX = [[120, 3.71], [180, 3.8], [240, 3.87], [300, 4.01]];

export const DONNEES = {
  version: "0.3.0",

  // ------------------------------------------------------------------------- crédit
  // grilleTaux : [durée en mois, taux nominal] ; entre deux durées, le taux est interpolé.
  // duree : en mois, sauf pour l'immobilier (en années). champs : champs propres au type de crédit.
  profils: {
    conso: {
      libelle: "Consommation",
      libelleMontant: "Montant à emprunter",
      montant: 10000,
      montantMax: 200000,
      pasMontant: 500,
      apport: 0,
      mensualite: 250,
      duree: 48,
      assurance: 0,
      fraisDossier: 0,
      grilleTaux: TAUX_CETELEM,
      sourceTaux: "Cetelem, prêt personnel, offre « à partir de » (octobre 2026)",
      dureesComparaison: [12, 24, 36, 48, 60, 72, 84],
      champs: ["duree_mois"],
    },
    auto: {
      libelle: "Auto",
      libelleMontant: "Prix du véhicule",
      montant: 28000,
      montantMax: 500000,
      pasMontant: 500,
      apport: 5000,
      mensualite: 450,
      duree: 60,
      assurance: 0.3,
      fraisDossier: 0,
      grilleTaux: TAUX_CETELEM,
      sourceTaux: "Cetelem, crédit auto, offre « à partir de » (octobre 2026)",
      dureesComparaison: [24, 36, 48, 60, 72, 84],
      champs: ["apport", "duree_mois", "reprise"],
    },
    immo: {
      libelle: "Immobilier",
      libelleMontant: "Prix du bien",
      montant: 250000,
      montantMax: 10000000,
      pasMontant: 5000,
      apport: 25000,
      mensualite: 1500,
      duree: 20,
      assurance: 0.34,
      fraisDossier: 1000,
      grilleTaux: TAUX_MEILLEURTAUX,
      sourceTaux: "Meilleurtaux, taux moyens avant négociation du 19/10/2026",
      dureesComparaison: [120, 180, 240, 300],
      champs: ["apport", "duree_ans", "garantie", "notaire", "travaux", "type_bien"],
    },
  },
  /** Frais de notaire en % du prix. */
  tauxNotaire: { "Ancien": 7.5, "Neuf (VEFA)": 2.5 },
  /** Dépenses courantes du foyer : [libellé, montant mensuel par défaut]. */
  postesBudget: [
    ["Logement (loyer, charges)", 900],
    ["Alimentation", 600],
    ["Transport", 250],
    ["Énergie et eau", 150],
    ["Assurances et abonnements", 150],
    ["Loisirs et divers", 300],
  ],
  /** Taux d'endettement maximal recommandé par le HCSF, en %. */
  endettementMax: 35,
  couleurOk: "#059669",
  couleurAlerte: "#dc2626",

  // ------------------------------------------------------------------------- épargne
  // taux : taux annuel brut en % ; prelevements : impôt + prélèvements sociaux sur les intérêts, en % ;
  // plafond : plafond de versements en € (null = sans plafond). Taux relevés en octobre 2026.
  placements: [
    {
      nom: "Livret A",
      taux: 1.7,
      prelevements: 0,
      plafond: 22950,
      source: "taux en vigueur depuis le 1er août 2026",
      note: "Exonéré d'impôt et de prélèvements sociaux.",
    },
    {
      nom: "LDDS",
      taux: 1.7,
      prelevements: 0,
      plafond: 12000,
      source: "taux en vigueur depuis le 1er août 2026 (aligné sur le Livret A)",
      note: "Exonéré d'impôt et de prélèvements sociaux.",
    },
    {
      nom: "LEP",
      taux: 2.5,
      prelevements: 0,
      plafond: 10000,
      source: "taux en vigueur depuis le 1er août 2026",
      note: "Réservé aux foyers aux revenus modestes. Exonéré d'impôt et de prélèvements sociaux.",
    },
    {
      nom: "PEL (ouvert en 2026)",
      taux: 2,
      prelevements: 30,
      plafond: 61200,
      source: "taux des PEL ouverts depuis le 1er janvier 2026",
      note: "Intérêts soumis au prélèvement forfaitaire unique de 30 %. Versements limités à 10 ans ; un PEL dure 15 ans au plus.",
    },
    {
      nom: "Assurance vie, fonds €",
      taux: 2.63,
      prelevements: 17.2,
      plafond: null,
      source: "rendement moyen 2025 publié par l'ACPR en juin 2026, déjà net des frais de gestion",
      note: "Prélèvements sociaux de 17,2 % retenus chaque année ; l'impôt sur le revenu, dû seulement lors d'un retrait, n'est pas simulé.",
    },
    {
      nom: "Personnalisé",
      taux: 3,
      prelevements: 30,
      plafond: null,
      source: "taux et prélèvements saisis librement",
      note: "",
    },
  ],
  /** Position du placement « Personnalisé » dans la liste. */
  personnalise: 5,
  /** Inflation par défaut : objectif de long terme de la BCE (3,1 % sur un an en septembre 2026, Insee). */
  inflationDefaut: 2,

  // ------------------------------------------------------------------------- lexiques
  lexique: {
    "Taux nominal (ou taux débiteur)": "Taux annuel des intérêts. Il ne tient compte ni de l'assurance ni des frais.",
    "TAEG": "Taux annuel effectif global : le coût complet du crédit (intérêts, assurance obligatoire, frais) exprimé en taux annuel. C'est le taux qui permet de comparer deux offres ; il figure obligatoirement sur toute offre de crédit.",
    "Mensualité": "Somme versée chaque mois. Dans un prêt amortissable classique, elle est constante hors assurance.",
    "Amortissement": "Remboursement progressif du capital. Chaque mensualité paie d'abord les intérêts du mois ; le reste rembourse le capital.",
    "Capital restant dû": "Part du capital qui reste à rembourser à une date donnée. Les intérêts du mois sont calculés sur ce montant.",
    "Assurance emprunteur": "Garantit le remboursement en cas de décès ou d'invalidité. Calculée sur le capital initial (montant fixe) ou sur le capital restant dû (montant qui baisse).",
    "Frais de dossier et de garantie": "Frais payés à la mise en place du prêt. La garantie (caution ou hypothèque) protège le prêteur si l'emprunteur ne rembourse plus.",
    "Frais de notaire": "Droits et taxes payés lors d'un achat immobilier : environ 7 à 8 % du prix dans l'ancien, 2 à 3 % dans le neuf.",
    "Apport personnel": "Somme que l'emprunteur finance lui-même. Il réduit le montant emprunté.",
    "Taux d'endettement": "Part des revenus consacrée au remboursement de tous les crédits. Le HCSF recommande de ne pas dépasser 35 % pour un crédit immobilier.",
    "Coût total du crédit": "Ce que le crédit coûte en plus du capital emprunté : intérêts, assurance et frais.",
  },
  lexiqueEpargne: {
    "Intérêts composés": "Les intérêts s'ajoutent au capital et rapportent à leur tour des intérêts : l'épargne grossit de plus en plus vite avec le temps (effet « boule de neige »).",
    "Taux brut / rendement net": "Le taux brut est celui annoncé par la banque ; le rendement net est ce qui reste après impôt et prélèvements sociaux.",
    "Prélèvements sociaux et PFU": "Les intérêts de la plupart des placements sont taxés : prélèvements sociaux (17,2 % sur l'assurance vie) ou prélèvement forfaitaire unique de 30 % (PEL). Livret A, LDDS et LEP en sont exonérés.",
    "Inflation": "Hausse générale des prix. Elle réduit ce qu'on peut acheter avec une même somme.",
    "Pouvoir d'achat / euros d'aujourd'hui": "Valeur d'une somme future ramenée aux prix actuels : capital ÷ (1 + inflation)^années.",
    "Rendement réel": "Rendement net corrigé de l'inflation. S'il est négatif, l'épargne perd du pouvoir d'achat même si son montant augmente.",
    "Plafond de versements": "Montant maximal qu'on peut déposer sur un livret réglementé (22 950 € pour le Livret A). Les intérêts, eux, peuvent faire dépasser ce plafond.",
    "Règle de 72": "Pour un rendement de r %, une somme double en environ 72 / r années.",
  },
};
