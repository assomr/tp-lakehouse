# Conventions de nommage

## Buckets MinIO
- `bronze` — données brutes, telles que reçues de l'API
- `silver` — données nettoyées et validées
- `silver-quarantine` — données rejetées par au moins une règle qualité

## Clés d'objets (partitionnement)
`exchange_rates/dt=YYYY-MM-DD/devise=XXX/<fichier>.json`
- `dt=` : partition par date d'exécution (permet de rejouer un jour précis)
- `devise=` : partition par devise (permet un contrôle qualité et un chargement indépendants par devise)

## Tables Postgres (zone gold)
- `dim_*` : tables de dimension (`dim_date`, `dim_devise`)
- `fact_*` : table de faits (`fact_taux_change`)
- `log_technique` : logs techniques (une ligne par tentative d'extraction/chargement)
- `log_qualite` : logs métier (une ligne par règle qualité appliquée)

## Tâches Airflow (TaskFlow API)
- `extract` : un appel API par devise (paramétré via `.expand()`)
- `quality_and_clean` : application des 5 règles + écriture silver/quarantaine
- `load_to_gold` : chargement idempotent en zone gold
- `log_summary` : synthèse de fin de run

## DAG
- `dag_id` : `taux_change_frankfurter` (snake_case, décrit le domaine métier)
