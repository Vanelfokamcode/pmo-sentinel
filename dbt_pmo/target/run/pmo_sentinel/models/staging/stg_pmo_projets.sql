
  
  create view "pmo_sentinel"."main"."stg_pmo_projets__dbt_tmp" as (
    with source as (
    select * from read_csv_auto('../data/enriched/pmo_enriched.csv')
)

select
    projet_id,
    entreprise,
    type_i40,
    volet_relance,
    region,
    complexite,
    priorite,
    phase,
    statut,
    description_courte,
    nb_jalons_total::INT as nb_jalons_total,
    nb_jalons_valides::INT as nb_jalons_valides,
    budget_prevu_k::FLOAT as budget_prevu_k,
    budget_consomme_k::FLOAT as budget_consomme_k,
    date_debut::DATE as date_debut,
    date_fin_prevue::DATE as date_fin_prevue,
    retard_jours::INT as retard_jours
from source
  );
