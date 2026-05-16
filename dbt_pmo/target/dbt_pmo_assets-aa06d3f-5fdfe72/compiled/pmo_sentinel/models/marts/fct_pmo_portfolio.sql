with projects as (
    select * from "pmo_sentinel"."main"."stg_pmo_projets"
)

select
    *,
    -- Taux de consommation du budget (Burn Rate)
    round((budget_consomme_k / nullif(budget_prevu_k, 0)) * 100, 2) as burn_rate_pct,
    
    -- Pourcentage d'avancement des jalons
    round((nb_jalons_valides::FLOAT / nullif(nb_jalons_total, 0)) * 100, 2) as progress_pct,
    
    -- Logique de Scoring RAG (Red / Amber / Green)
    -- On automatise ce que Marilyne fait à la main
    case 
        when statut = 'Bloqué' or retard_jours > 30 or (budget_consomme_k > budget_prevu_k * 1.2) then 'RED'
        when statut = 'À risque' or retard_jours > 0 or (budget_consomme_k > budget_prevu_k) then 'AMBER'
        else 'GREEN'
    end as rag_status
from projects