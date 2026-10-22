// Fichier généré par outils/generer_web.py à partir de simu_credit/ — ne pas modifier à la main.
export const DONNEES = {
  "version": "0.2.0",
  "profils": {
    "conso": {
      "libelle": "Consommation",
      "libelleMontant": "Montant à emprunter",
      "montant": 10000,
      "montantMax": 200000,
      "pasMontant": 500,
      "apport": 0,
      "mensualite": 250,
      "duree": 48,
      "assurance": 0.0,
      "fraisDossier": 0,
      "grilleTaux": [
        [
          48,
          5.36
        ]
      ],
      "sourceTaux": "Cetelem, prêt personnel, offre « à partir de » (octobre 2026)",
      "dureesComparaison": [
        12,
        24,
        36,
        48,
        60,
        72,
        84
      ],
      "champs": [
        "duree_mois"
      ]
    },
    "auto": {
      "libelle": "Auto",
      "libelleMontant": "Prix du véhicule",
      "montant": 28000,
      "montantMax": 500000,
      "pasMontant": 500,
      "apport": 5000,
      "mensualite": 450,
      "duree": 60,
      "assurance": 0.3,
      "fraisDossier": 0,
      "grilleTaux": [
        [
          48,
          5.36
        ]
      ],
      "sourceTaux": "Cetelem, crédit auto, offre « à partir de » (octobre 2026)",
      "dureesComparaison": [
        24,
        36,
        48,
        60,
        72,
        84
      ],
      "champs": [
        "apport",
        "duree_mois",
        "reprise"
      ]
    },
    "immo": {
      "libelle": "Immobilier",
      "libelleMontant": "Prix du bien",
      "montant": 250000,
      "montantMax": 10000000,
      "pasMontant": 5000,
      "apport": 25000,
      "mensualite": 1500,
      "duree": 20,
      "assurance": 0.34,
      "fraisDossier": 1000,
      "grilleTaux": [
        [
          120,
          3.71
        ],
        [
          180,
          3.8
        ],
        [
          240,
          3.87
        ],
        [
          300,
          4.01
        ]
      ],
      "sourceTaux": "Meilleurtaux, taux moyens avant négociation du 19/10/2026",
      "dureesComparaison": [
        120,
        180,
        240,
        300
      ],
      "champs": [
        "apport",
        "duree_ans",
        "garantie",
        "notaire",
        "travaux",
        "type_bien"
      ]
    }
  },
  "tauxNotaire": {
    "Ancien": 7.5,
    "Neuf (VEFA)": 2.5
  },
  "postesBudget": [
    [
      "Logement (loyer, charges)",
      900
    ],
    [
      "Alimentation",
      600
    ],
    [
      "Transport",
      250
    ],
    [
      "Énergie et eau",
      150
    ],
    [
      "Assurances et abonnements",
      150
    ],
    [
      "Loisirs et divers",
      300
    ]
  ],
  "endettementMax": 35.0,
  "couleurOk": "#059669",
  "couleurAlerte": "#dc2626",
  "placements": [
    {
      "nom": "Livret A",
      "taux": 1.7,
      "prelevements": 0.0,
      "plafond": 22950,
      "source": "taux en vigueur depuis le 1er août 2026",
      "note": "Exonéré d'impôt et de prélèvements sociaux."
    },
    {
      "nom": "LDDS",
      "taux": 1.7,
      "prelevements": 0.0,
      "plafond": 12000,
      "source": "taux en vigueur depuis le 1er août 2026 (aligné sur le Livret A)",
      "note": "Exonéré d'impôt et de prélèvements sociaux."
    },
    {
      "nom": "LEP",
      "taux": 2.5,
      "prelevements": 0.0,
      "plafond": 10000,
      "source": "taux en vigueur depuis le 1er août 2026",
      "note": "Réservé aux foyers aux revenus modestes. Exonéré d'impôt et de prélèvements sociaux."
    },
    {
      "nom": "PEL (ouvert en 2026)",
      "taux": 2.0,
      "prelevements": 30.0,
      "plafond": 61200,
      "source": "taux des PEL ouverts depuis le 1er janvier 2026",
      "note": "Intérêts soumis au prélèvement forfaitaire unique de 30 %. Versements limités à 10 ans ; un PEL dure 15 ans au plus."
    },
    {
      "nom": "Assurance vie, fonds €",
      "taux": 2.63,
      "prelevements": 17.2,
      "plafond": null,
      "source": "rendement moyen 2025 publié par l'ACPR en juin 2026, déjà net des frais de gestion",
      "note": "Prélèvements sociaux de 17,2 % retenus chaque année ; l'impôt sur le revenu, dû seulement lors d'un retrait, n'est pas simulé."
    },
    {
      "nom": "Personnalisé",
      "taux": 3.0,
      "prelevements": 30.0,
      "plafond": null,
      "source": "taux et prélèvements saisis librement",
      "note": ""
    }
  ],
  "personnalise": 5,
  "inflationDefaut": 2.0,
  "lexique": {
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
    "Coût total du crédit": "Ce que le crédit coûte en plus du capital emprunté : intérêts, assurance et frais."
  },
  "lexiqueEpargne": {
    "Intérêts composés": "Les intérêts s'ajoutent au capital et rapportent à leur tour des intérêts : l'épargne grossit de plus en plus vite avec le temps (effet « boule de neige »).",
    "Taux brut / rendement net": "Le taux brut est celui annoncé par la banque ; le rendement net est ce qui reste après impôt et prélèvements sociaux.",
    "Prélèvements sociaux et PFU": "Les intérêts de la plupart des placements sont taxés : prélèvements sociaux (17,2 % sur l'assurance vie) ou prélèvement forfaitaire unique de 30 % (PEL). Livret A, LDDS et LEP en sont exonérés.",
    "Inflation": "Hausse générale des prix. Elle réduit ce qu'on peut acheter avec une même somme.",
    "Pouvoir d'achat / euros d'aujourd'hui": "Valeur d'une somme future ramenée aux prix actuels : capital ÷ (1 + inflation)^années.",
    "Rendement réel": "Rendement net corrigé de l'inflation. S'il est négatif, l'épargne perd du pouvoir d'achat même si son montant augmente.",
    "Plafond de versements": "Montant maximal qu'on peut déposer sur un livret réglementé (22 950 € pour le Livret A). Les intérêts, eux, peuvent faire dépasser ce plafond.",
    "Règle de 72": "Pour un rendement de r %, une somme double en environ 72 / r années."
  }
};
