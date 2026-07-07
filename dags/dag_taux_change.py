"""DAG quotidien : ingestion des taux EUR->USD/GBP/CHF depuis Frankfurter.

Chemins démontrables :
- nominal      : extraction OK -> qualité OK -> silver -> gold (DAG vert)
- échec qualité: extraction OK -> une règle échoue -> quarantaine (DAG vert quand même)
- échec technique: extraction échoue après épuisement des retries (DAG rouge)
"""
from datetime import datetime, timedelta

from airflow.decorators import dag, task
from airflow.exceptions import AirflowException

DEVISES = ["USD", "GBP", "CHF"]

default_args = {
    "owner": "assia",
    "retries": 3,
    "retry_delay": timedelta(minutes=2),
    "execution_timeout": timedelta(minutes=2),
}


@dag(
    dag_id="taux_change_frankfurter",
    description="Ingestion quotidienne des taux EUR->USD/GBP/CHF (lakehouse bronze/silver/gold)",
    schedule="0 17 * * *",  # 17h, après la publication BCE (~16h CET)
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["lakehouse", "frankfurter", "finance"],
)
def taux_change_pipeline():

    @task
    def extract(devise: str, run_date: str) -> str:
        from scripts.common import db
        from scripts.extract.extract_frankfurter import ExtractionError, extract_and_store

        conn = db.get_connection()
        try:
            key = extract_and_store(devise, run_date)
            db.log_technique(conn, run_date, devise, "extraction", "succes", f"clé={key}")
            return devise
        except ExtractionError as exc:
            db.log_technique(conn, run_date, devise, "extraction", "echec", str(exc))
            # Remonte l'exception : après épuisement des retries, la tâche
            # échoue et le DAG passe au rouge (chemin d'échec technique).
            raise AirflowException(str(exc)) from exc
        finally:
            conn.close()

    @task
    def quality_and_clean(devise: str, run_date: str) -> dict:
        from scripts.transform.clean_silver import process

        statut = process(devise, run_date)
        return {"devise": devise, "statut": statut}

    @task
    def load_to_gold(resultat: dict, run_date: str) -> None:
        from scripts.load.load_gold import load

        if resultat["statut"] == "valide":
            load(resultat["devise"], run_date)
        else:
            # Donnée en quarantaine : pas de chargement gold pour cette devise,
            # mais la tâche réussit — le DAG reste vert (chemin d'échec qualité).
            print(f"[gold] {resultat['devise']} en quarantaine, non chargée en gold")

    @task
    def log_summary(resultats: list) -> None:
        valides = [r["devise"] for r in resultats if r["statut"] == "valide"]
        quarantaines = [r["devise"] for r in resultats if r["statut"] == "quarantaine"]
        print(f"[résumé] validées={valides} quarantaine={quarantaines}")

    # run_date est passé explicitement (via .partial()) pour que "{{ ds }}"
    # soit bien interprété par le moteur de templating d'Airflow — une valeur
    # par défaut Python n'est jamais templatée.
    devises_extraites = extract.partial(run_date="{{ ds }}").expand(devise=DEVISES)
    resultats_qualite = quality_and_clean.partial(run_date="{{ ds }}").expand(devise=devises_extraites)
    load_to_gold.partial(run_date="{{ ds }}").expand(resultat=resultats_qualite)
    log_summary(resultats_qualite)


taux_change_pipeline()