import csv
import hashlib
from datetime import date, timedelta

INPUT  = "data/raw/france_relance_raw.csv"
OUTPUT = "data/enriched/pmo_enriched.csv"

# ─── RÈGLES MÉTIER DÉTERMINISTES ─────────────────────────────────────────────
# Rien de random() — chaque valeur calculée depuis les données sources.
# Documentées et explicables en entretien face à Jean-François.

def get_complexite(mesure: str) -> str:
    haute = ["décarbonation", "automobile", "aéronautique", "relocalisation", "ami capacity"]
    moyenne = ["investissement industriel", "chaleur bas carbone", "hydrogène"]
    m = mesure.lower()
    for k in haute:
        if k in m:
            return "Haute"
    for k in moyenne:
        if k in m:
            return "Moyenne"
    return "Faible"

def get_nb_jalons(complexite: str) -> int:
    return {"Haute": 7, "Moyenne": 5, "Faible": 3}[complexite]

def get_type_i40(mesure: str, filiere: str) -> str:
    m = mesure.lower()
    f = (filiere or "").lower()
    if "automobile" in m or "automobile" in f:
        return "Robotique"
    if "aéronautique" in m or "aéronautique" in f:
        return "MES"
    if "décarbonation" in m:
        return "Energie"
    if "numérique" in m or "industrie du futur" in m:
        return "BI"
    if "chaleur" in m or "hydrogène" in m:
        return "Energie"
    if "relocalisation" in m or "ami capacity" in m:
        return "IoT"
    return "Qualité"

def get_priorite(type_i40: str, complexite: str) -> str:
    if type_i40 in ("Robotique", "MES") and complexite == "Haute":
        return "Critique"
    if complexite == "Haute":
        return "Haute"
    if complexite == "Moyenne":
        return "Normale"
    return "Basse"

def get_phase(projet_id: str) -> str:
    """Déterministe via hash du SIREN — pas random."""
    phases = ["Cadrage", "Développement", "Test", "Déploiement", "Livré"]
    idx = int(hashlib.md5(projet_id.encode()).hexdigest(), 16) % len(phases)
    return phases[idx]

def get_statut(phase: str, complexite: str, region: str) -> str:
    """
    Règle : Haute complexité + Développement/Test → risque de retard.
    Auvergne-Rhône-Alpes = région Michelin → on force quelques projets à risque
    pour que le dashboard soit intéressant.
    """
    if phase == "Livré":
        return "Livré"
    if complexite == "Haute" and phase in ("Développement", "Test"):
        return "À risque"
    if "auvergne" in region.lower() and phase == "Test":
        return "Bloqué"
    if phase == "Cadrage":
        return "On Track"
    return "On Track"

def get_budget_prevu(mesure: str, complexite: str) -> int:
    """En k€ — basé sur la mesure et la complexité."""
    base = {"Haute": 1200, "Moyenne": 450, "Faible": 120}[complexite]
    if "automobile" in mesure.lower():
        base = int(base * 1.8)
    if "aéronautique" in mesure.lower():
        base = int(base * 2.1)
    if "décarbonation" in mesure.lower():
        base = int(base * 1.4)
    return base

def get_budget_consomme(budget_prevu: int, statut: str, phase: str) -> int:
    """
    Règle : À risque → dépassement 15-30%. Bloqué → dépassement 35-50%.
    Déterministe via ratio fixe par statut+phase.
    """
    ratios = {
        ("On Track",  "Cadrage"):      0.15,
        ("On Track",  "Développement"):0.55,
        ("On Track",  "Test"):         0.82,
        ("On Track",  "Déploiement"):  0.95,
        ("Livré",     "Livré"):        1.02,
        ("À risque",  "Développement"):0.72,
        ("À risque",  "Test"):         1.18,
        ("Bloqué",    "Test"):         1.42,
        ("Bloqué",    "Développement"):1.28,
    }
    ratio = ratios.get((statut, phase), 0.60)
    return int(budget_prevu * ratio)

def get_jalons_valides(nb_jalons: int, phase: str, statut: str) -> int:
    phase_progress = {
        "Cadrage": 0.14, "Développement": 0.43,
        "Test": 0.71, "Déploiement": 0.86, "Livré": 1.0
    }
    ratio = phase_progress.get(phase, 0.5)
    if statut in ("À risque", "Bloqué"):
        ratio = max(0, ratio - 0.15)
    return max(0, int(nb_jalons * ratio))

def get_dates(siren: str, complexite: str):
    """Dates déterministes basées sur le SIREN."""
    seed = int(hashlib.md5(siren.encode()).hexdigest()[:8], 16)
    # date_debut entre 2022-01-01 et 2023-06-01
    offset_debut = seed % 520
    date_debut = date(2022, 1, 1) + timedelta(days=offset_debut)
    # durée selon complexité
    duree_jours = {"Haute": 730, "Moyenne": 450, "Faible": 240}[complexite]
    date_fin_prevue = date_debut + timedelta(days=duree_jours)
    return str(date_debut), str(date_fin_prevue)

def get_retard_jours(statut: str, phase: str, date_fin_prevue: str) -> int:
    if statut == "Livré":
        return 0
    fin = date.fromisoformat(date_fin_prevue)
    aujourd_hui = date(2026, 5, 13)
    if fin > aujourd_hui:
        # pas encore dû
        if statut == "À risque":
            return 12
        if statut == "Bloqué":
            return 45
        return 0
    # dépassé la date
    retard_base = (aujourd_hui - fin).days
    if statut in ("À risque", "Bloqué"):
        return retard_base
    return 0

# ─── MAIN ────────────────────────────────────────────────────────────────────

import os
os.makedirs("data/enriched", exist_ok=True)

fieldnames_out = [
    "projet_id", "entreprise", "siren", "type_i40", "mesure_origine",
    "volet_relance", "filiere", "region", "departement", "commune",
    "complexite", "priorite", "phase", "statut",
    "nb_jalons_total", "nb_jalons_valides",
    "budget_prevu_k", "budget_consomme_k",
    "date_debut", "date_fin_prevue", "retard_jours",
    "description_courte"
]

with open(INPUT, encoding="utf-8") as fin, \
     open(OUTPUT, "w", encoding="utf-8", newline="") as fout:

    reader = csv.DictReader(fin, delimiter=";")
    writer = csv.DictWriter(fout, fieldnames=fieldnames_out)
    writer.writeheader()

    for i, row in enumerate(reader):
        siren      = row.get("siren", str(i)).strip() or str(i)
        entreprise = row.get("entreprise", "").strip()
        mesure     = row.get("mesure", "").strip()
        filiere    = row.get("filiere", "").strip()
        region     = row.get("nom_region", "").strip()
        volet      = row.get("volet_relance", "").strip()
        desc       = row.get("description_projet", "").strip()

        complexite      = get_complexite(mesure)
        nb_jalons       = get_nb_jalons(complexite)
        type_i40        = get_type_i40(mesure, filiere)
        priorite        = get_priorite(type_i40, complexite)
        phase           = get_phase(siren)
        statut          = get_statut(phase, complexite, region)
        budget_prevu    = get_budget_prevu(mesure, complexite)
        budget_consomme = get_budget_consomme(budget_prevu, statut, phase)
        jalons_valides  = get_jalons_valides(nb_jalons, phase, statut)
        date_debut, date_fin_prevue = get_dates(siren, complexite)
        retard_jours    = get_retard_jours(statut, phase, date_fin_prevue)
        description_courte = desc[:150].replace("\n", " ") + "..." if len(desc) > 150 else desc

        writer.writerow({
            "projet_id":        f"PRJ-{i+1:04d}",
            "entreprise":       entreprise,
            "siren":            siren,
            "type_i40":         type_i40,
            "mesure_origine":   mesure,
            "volet_relance":    volet,
            "filiere":          filiere,
            "region":           region,
            "departement":      row.get("nom_departement", "").strip(),
            "commune":          row.get("nom_commune", "").strip(),
            "complexite":       complexite,
            "priorite":         priorite,
            "phase":            phase,
            "statut":           statut,
            "nb_jalons_total":  nb_jalons,
            "nb_jalons_valides":jalons_valides,
            "budget_prevu_k":   budget_prevu,
            "budget_consomme_k":budget_consomme,
            "date_debut":       date_debut,
            "date_fin_prevue":  date_fin_prevue,
            "retard_jours":     retard_jours,
            "description_courte": description_courte
        })

print(f"Done — {i+1} projets enrichis → {OUTPUT}")
