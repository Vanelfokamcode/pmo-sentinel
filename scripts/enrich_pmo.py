import csv
import hashlib
import os
from datetime import date, timedelta

INPUT  = "data/raw/france_relance_raw.csv"
OUTPUT = "data/enriched/pmo_enriched.csv"

def get_complexite(mesure):
    m = mesure.lower()
    if any(k in m for k in ["décarbonation", "automobile", "aéronautique"]): return "Haute"
    if any(k in m for k in ["investissement", "chaleur"]): return "Moyenne"
    return "Faible"

def get_type_i40(mesure, filiere):
    m, f = mesure.lower(), (filiere or "").lower()
    if "auto" in m or "auto" in f: return "Robotique"
    if "aéro" in m or "aéro" in f: return "MES"
    if "décarb" in m or "chaleur" in m: return "Energie"
    if "numérique" in m: return "BI"
    return "IoT"

os.makedirs("data/enriched", exist_ok=True)

with open(INPUT, encoding="utf-8-sig") as fin:
    reader = csv.DictReader(fin, delimiter=";")
    reader.fieldnames = [name.strip() for name in reader.fieldnames]
    
    with open(OUTPUT, "w", encoding="utf-8", newline="") as fout:
        # Liste complète des colonnes pour dbt et Power BI
        fieldnames = [
            "projet_id", "entreprise", "siren", "type_i40", "volet_relance", 
            "complexite", "statut", "phase", "priorite", "region", 
            "description_courte", "budget_prevu_k", "budget_consomme_k", 
            "nb_jalons_total", "nb_jalons_valides", "retard_jours",
            "date_debut", "date_fin_prevue"
        ]
        writer = csv.DictWriter(fout, fieldnames=fieldnames)
        writer.writeheader()

        for i, row in enumerate(reader):
            ent = row.get("entreprise") or row.get("\ufeffentreprise") or "Inconnu"
            mesure = row.get("mesure", "")
            comp = get_complexite(mesure)
            
            # Simulation déterministe pour Power BI
            writer.writerow({
                "projet_id": f"PRJ-{i+1:04d}",
                "entreprise": ent.strip(),
                "siren": row.get("siren", ""),
                "type_i40": get_type_i40(mesure, row.get("filiere")),
                "volet_relance": row.get("volet_relance", "N/A"),
                "complexite": comp,
                "statut": "À risque" if comp == "Haute" else "On Track",
                "phase": "Développement",
                "priorite": "Haute" if comp == "Haute" else "Normale",
                "region": row.get("nom_region", "Inconnue"),
                "description_courte": (row.get("description_projet") or "")[:150],
                "budget_prevu_k": 500 if comp == "Haute" else 150,
                "budget_consomme_k": 550 if comp == "Haute" else 100,
                "nb_jalons_total": 5,
                "nb_jalons_valides": 2,
                "retard_jours": 15 if comp == "Haute" else 0,
                "date_debut": "2024-01-01",
                "date_fin_prevue": "2025-01-01"
            })
print("Enrichissement terminé : data/enriched/pmo_enriched.csv")
