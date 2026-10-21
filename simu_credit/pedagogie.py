"""Explications pas à pas des calculs, avec les chiffres de la simulation en cours.

Produit le contenu (HTML simple, compatible Qt) du panneau « Comment c'est calculé ».
"""

from __future__ import annotations

import math
from collections.abc import Sequence

from simu_credit.calcul import Budget, ResultatCredit, calcul_taeg, mensualite, mois_bascule
from simu_credit.formats import duree_texte, eur, nombre, pct

LEXIQUE = {
    "Taux nominal (ou taux débiteur)": (
        "Taux annuel des intérêts. Il ne tient compte ni de l'assurance ni des frais."
    ),
    "TAEG": (
        "Taux annuel effectif global : le coût complet du crédit (intérêts, assurance obligatoire, frais) "
        "exprimé en taux annuel. C'est le taux qui permet de comparer deux offres ; il figure "
        "obligatoirement sur toute offre de crédit."
    ),
    "Mensualité": "Somme versée chaque mois. Dans un prêt amortissable classique, elle est constante hors assurance.",
    "Amortissement": (
        "Remboursement progressif du capital. Chaque mensualité paie d'abord les intérêts du mois ; "
        "le reste rembourse le capital."
    ),
    "Capital restant dû": (
        "Part du capital qui reste à rembourser à une date donnée. Les intérêts du mois sont calculés sur ce montant."
    ),
    "Assurance emprunteur": (
        "Garantit le remboursement en cas de décès ou d'invalidité. Calculée sur le capital initial "
        "(montant fixe) ou sur le capital restant dû (montant qui baisse)."
    ),
    "Frais de dossier et de garantie": (
        "Frais payés à la mise en place du prêt. La garantie (caution ou hypothèque) protège le prêteur "
        "si l'emprunteur ne rembourse plus."
    ),
    "Frais de notaire": (
        "Droits et taxes payés lors d'un achat immobilier : environ 7 à 8 % du prix dans l'ancien, "
        "2 à 3 % dans le neuf."
    ),
    "Apport personnel": "Somme que l'emprunteur finance lui-même. Il réduit le montant emprunté.",
    "Taux d'endettement": (
        "Part des revenus consacrée au remboursement de tous les crédits. Le HCSF recommande de ne pas "
        "dépasser 35 % pour un crédit immobilier."
    ),
    "Coût total du crédit": "Ce que le crédit coûte en plus du capital emprunté : intérêts, assurance et frais.",
}

STYLE = """
h2 { color: #1d4f8c; }
h3 { color: #1d4f8c; margin-top: 18px; margin-bottom: 4px; }
p, li { line-height: 140%; }
.discret { color: #6b7280; }
"""


def _formule(*lignes: str) -> str:
    contenu = "<br>".join(lignes)
    return (
        '<table width="100%" cellpadding="8" cellspacing="0" bgcolor="#eef3fa">'
        f"<tr><td>{contenu}</td></tr></table>"
    )


def _tableau(lignes: Sequence[tuple[str, str]]) -> str:
    rangees = "".join(
        f'<tr><td>{libelle}</td><td align="right">{valeur}</td></tr>' for libelle, valeur in lignes
    )
    return f'<table cellpadding="4" cellspacing="0" bgcolor="#eef3fa" width="100%">{rangees}</table>'


def _section(numero: int, titre: str, corps: str) -> str:
    return f"<h3>{numero}. {titre}</h3>{corps}"


def expliquer(
    r: ResultatCredit,
    *,
    etapes_montant: Sequence[tuple[str, str]],
    mensualite_cible: float | None,
    budget: Budget | None,
    endettement_max: float,
    comparaison: Sequence[ResultatCredit],
) -> str:
    """HTML du panneau « Comment c'est calculé » pour la simulation `r`."""
    C, n = r.capital, r.duree_mois
    t = r.taux_annuel / 100 / 12
    M = r.mensualite_hors_assurance
    taux_ass_mensuel = r.taux_assurance / 100 / 12
    sections: list[str] = []

    # 1. Montant emprunté
    corps = ""
    if mensualite_cible is not None:
        par_euro = mensualite(1.0, r.taux_annuel, n) + taux_ass_mensuel
        corps += (
            "<p>Vous êtes parti de la mensualité que vous voulez payer. On calcule d'abord la mensualité "
            "pour <b>1 € emprunté</b>, puis on divise la mensualité visée par ce montant (la mensualité "
            "est proportionnelle au capital) :</p>"
            + _formule(
                f"mensualité pour 1 € = t / (1 − (1 + t)<sup>−n</sup>) + assurance / 12 = {nombre(par_euro, 6)} €",
                f"capital = {eur(mensualite_cible)} / {nombre(par_euro, 6)} = <b>{eur(C)}</b>",
            )
        )
    if etapes_montant:
        corps += "<p>Le montant à financer se déduit du projet :</p>" + _tableau(etapes_montant)
    sections.append(_section(1, "Le montant emprunté (C)", corps or f"<p>C = <b>{eur(C)}</b></p>"))

    # 2. Taux mensuel
    sections.append(_section(2, "Le taux mensuel (t)", (
        "<p>En France, le taux mensuel est le taux annuel divisé par 12 (taux proportionnel).</p>"
        + _formule(f"t = {pct(r.taux_annuel)} / 12 = <b>{pct(r.taux_annuel / 12, 4)}</b> = {nombre(t, 6)}")
    )))

    # 3. Mensualité
    if t > 0:
        formule = _formule(
            "M = C × t / (1 − (1 + t)<sup>−n</sup>)",
            f"M = {nombre(C)} × {nombre(t, 6)} / (1 − {nombre(1 + t, 6)}<sup>−{n}</sup>)",
            f"M = <b>{eur(M)}</b> par mois, hors assurance",
        )
    else:
        formule = _formule("Taux nul : M = C / n", f"M = {nombre(C)} / {n} = <b>{eur(M)}</b>")
    sections.append(_section(3, f"La mensualité (M) sur n = {n} mois", (
        "<p>Cette formule donne la mensualité <b>constante</b> qui rembourse exactement le capital "
        "et tous les intérêts en n mois.</p>" + formule
    )))

    # 4. Intérêts puis capital
    premiere, derniere = r.tableau[0], r.tableau[-1]
    bascule = mois_bascule(r.tableau)
    if bascule == 1:
        phrase_bascule = "Ici, la part de capital dépasse celle des intérêts dès la 1re échéance."
    elif bascule:
        phrase_bascule = (
            f"Jusqu'à l'échéance n°{bascule - 1}, vous payez surtout des intérêts. "
            f"<b>À partir de l'échéance n°{bascule}</b> (année {(bascule - 1) // 12 + 1}), vous remboursez "
            "plus de capital que d'intérêts : c'est le <b>point de bascule</b>, surligné dans le tableau "
            "d'amortissement."
        )
    else:
        phrase_bascule = ""
    sections.append(_section(4, "Dans chaque mensualité : d'abord les intérêts, puis le capital", (
        "<p>Chaque mois, les intérêts sont calculés sur le <b>capital restant dû</b> ; le reste de la "
        "mensualité rembourse le capital. Comme le capital restant dû baisse, les intérêts baissent et "
        "la part de capital augmente.</p>"
        + _formule(
            "<b>1re échéance</b>",
            f"intérêts = capital restant dû × t = {nombre(C)} × {nombre(t, 6)} = {eur(premiere.interets)}",
            f"capital remboursé = M − intérêts = {nombre(M)} − {nombre(premiere.interets)} = {eur(premiere.capital)}",
            f"capital restant dû après = {nombre(C)} − {nombre(premiere.capital)} = {eur(premiere.capital_restant)}",
            "",
            f"<b>Dernière échéance (n°{n})</b> : intérêts {eur(derniere.interets)}, capital {eur(derniere.capital)}",
        )
        + f"<p>{phrase_bascule}</p>"
    )))

    # 5. Assurance
    if r.taux_assurance <= 0:
        corps = "<p>Aucune assurance n'est retenue dans cette simulation.</p>"
    elif not r.assurance_sur_crd:
        corps = _formule(
            "Sur le capital initial : assurance = C × taux / 12",
            f"= {nombre(C)} × {pct(r.taux_assurance)} / 12 = <b>{eur(r.assurance_mensuelle)}</b> par mois, "
            "le même montant chaque mois",
            f"total = {eur(r.assurance_mensuelle)} × {n} = <b>{eur(r.cout_assurance)}</b>",
        )
    else:
        sur_initial = C * taux_ass_mensuel * n
        corps = _formule(
            "Sur le capital restant dû : assurance du mois = capital restant dû × taux / 12",
            f"1er mois = {nombre(C)} × {pct(r.taux_assurance)} / 12 = {eur(r.assurance_mensuelle)} ; "
            f"dernier mois = {eur(derniere.assurance)}",
            f"total = <b>{eur(r.cout_assurance)}</b>, contre {eur(sur_initial)} si elle portait "
            "sur le capital initial",
        )
    sections.append(_section(5, f"L'assurance emprunteur ({pct(r.taux_assurance)} par an)", corps))

    # 6. Coût total
    sections.append(_section(6, "Le coût total du crédit", _formule(
        "coût total = intérêts + assurance + frais",
        f"= {nombre(r.cout_interets)} + {nombre(r.cout_assurance)} + {nombre(r.frais)} = <b>{eur(r.cout_total)}</b>",
        f"montant total dû = capital + coût total = {nombre(C)} + {nombre(r.cout_total)} = {eur(r.montant_total_du)}",
    ) + f"<p>Pour <b>1 € emprunté</b>, vous remboursez <b>{nombre(r.montant_total_du / C)} €</b>.</p>"))

    # 7. TAEG, décomposé
    if not math.isnan(r.taeg):
        i = (1 + r.taeg / 100) ** (1 / 12) - 1
        taeg_seul = ((1 + t) ** 12 - 1) * 100
        taeg_avec_assurance = calcul_taeg(C, [e.mensualite + e.assurance for e in r.tableau])
        decomposition = [
            ("Taux nominal", pct(r.taux_annuel)),
            ("+ effet de l'annualisation actuarielle (intérêts composés)", f"+{nombre(taeg_seul - r.taux_annuel)} pt"),
            ("+ effet de l'assurance", f"+{nombre(taeg_avec_assurance - taeg_seul)} pt"),
            ("+ effet des frais payés au départ", f"+{nombre(r.taeg - taeg_avec_assurance)} pt"),
            ("<b>= TAEG</b>", f"<b>{pct(r.taeg)}</b>"),
        ]
        sections.append(_section(7, "Le TAEG", (
            f"<p>Vous empruntez {eur(C)} mais payez {eur(r.frais)} de frais au départ : vous recevez "
            f"réellement <b>{eur(C - r.frais)}</b>. Le TAEG est le taux annuel qui égalise cette somme et "
            "tout ce que vous remboursez (mensualités + assurance). On trouve le taux mensuel i par essais "
            "successifs (méthode numérique), puis on l'annualise :</p>"
            + _formule(
                "C − frais = Σ<sub>k=1…n</sub> versement<sub>k</sub> / (1 + i)<sup>k</sup>",
                f"i = {pct(i * 100, 4)} par mois",
                f"TAEG = (1 + i)<sup>12</sup> − 1 = <b>{pct(r.taeg)}</b>",
            )
            + "<p>Pourquoi le TAEG est plus élevé que le taux nominal :</p>"
            + _tableau(decomposition)
        )))

    # 8. Budget
    numero = 8
    if budget is not None and budget.revenus > 0:
        verdict = (
            "sous le seuil de 35 %" if budget.endettement <= endettement_max else "<b>au-dessus du seuil de 35 %</b>"
        )
        sections.append(_section(numero, "Le poids du crédit dans le budget", _formule(
            "taux d'endettement = (mensualité + autres crédits) / revenus",
            f"= ({nombre(budget.mensualite_credit)} + {nombre(budget.autres_credits)}) / {nombre(budget.revenus)}"
            f" = <b>{pct(budget.endettement)}</b>, {verdict}",
            "solde du mois = revenus − crédits − dépenses courantes",
            f"= {nombre(budget.revenus)} − {nombre(budget.total_credits)} − {nombre(budget.total_depenses)}"
            f" = <b>{eur(budget.solde)}</b>",
        )))
        numero += 1

    # À retenir
    sections.append(f"<h3>{numero}. À retenir</h3><ul>{''.join(f'<li>{p}</li>' for p in _a_retenir(r, comparaison))}</ul>")

    # Lexique
    lexique = "".join(f"<p><b>{terme}</b> — {definition}</p>" for terme, definition in LEXIQUE.items())
    sections.append(f"<h3>Lexique</h3>{lexique}")

    entete = (
        "<h2>Comment c'est calculé</h2>"
        "<p class='discret'>Chaque étape reprend les chiffres de la simulation affichée. "
        "Modifiez un paramètre à gauche : les calculs se mettent à jour.</p>"
    )
    return f"<html><head><style>{STYLE}</style></head><body>{entete}{''.join(sections)}</body></html>"


def _a_retenir(r: ResultatCredit, comparaison: Sequence[ResultatCredit]) -> list[str]:
    points = []
    part_interets = r.tableau[0].interets / r.mensualite_hors_assurance * 100
    points.append(
        f"Votre 1re mensualité contient <b>{pct(part_interets, 0)} d'intérêts</b> ; la dernière presque "
        "uniquement du capital."
    )
    points.append(
        f"Les intérêts représentent <b>{pct(r.cout_interets / r.montant_total_du * 100, 0)}</b> "
        "de tout ce que vous remboursez."
    )
    durees = [c.duree_mois for c in comparaison]
    if r.duree_mois in durees:
        idx = durees.index(r.duree_mois)
        for autre in (comparaison[idx + 1] if idx + 1 < len(comparaison) else None,
                      comparaison[idx - 1] if idx > 0 else None):
            if autre is None:
                continue
            plus_long = autre.duree_mois > r.duree_mois
            sur = f"Sur {duree_texte(autre.duree_mois)} (taux {pct(autre.taux_annuel)})"
            d_cout = autre.cout_total - r.cout_total
            if abs(autre.capital - r.capital) < 1:
                d_mens = autre.mensualite_totale - r.mensualite_totale
                points.append(
                    f"{sur} : mensualité {'plus basse' if d_mens < 0 else 'plus haute'} de "
                    f"<b>{eur(abs(d_mens), 0)}</b>, mais coût total "
                    f"{'plus élevé' if d_cout > 0 else 'plus faible'} de <b>{eur(abs(d_cout), 0)}</b>."
                )
            else:
                d_cap = autre.capital - r.capital
                points.append(
                    f"{sur} : vous pourriez emprunter <b>{eur(d_cap, 0) if d_cap > 0 else eur(-d_cap, 0)}"
                    f"</b> {'de plus' if d_cap > 0 else 'de moins'}, pour un coût total "
                    f"{'plus élevé' if d_cout > 0 else 'plus faible'} de <b>{eur(abs(d_cout), 0)}</b>."
                )
            if plus_long:
                points[-1] += " Allonger la durée allège la mensualité mais coûte plus cher au total."
    return points
