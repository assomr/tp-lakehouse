"""Extraction du taux EUR -> devise depuis l'API Frankfurter, écriture en zone bronze.

Une tâche = une devise = un appel API indépendant (permet la parallélisation
et justifie l'usage du LocalExecutor + Postgres pour la metadata Airflow).
"""
import time

import requests

from scripts.common import minio_client

FRANKFURTER_BASE_URL = "https://api.frankfurter-invalide-test.dev/v1"


class ExtractionError(Exception):
    """Levée après épuisement des tentatives — déclenche le chemin d'échec technique."""


def fetch_rate(devise: str, execution_date: str, timeout: int = 10) -> dict:
    """Appelle Frankfurter pour une devise et une date données.

    Si execution_date correspond à un jour non ouvré (week-end, férié UE),
    Frankfurter renvoie le taux du dernier jour ouvré disponible — c'est un
    comportement normal de la source, pas une erreur technique.
    """
    url = f"{FRANKFURTER_BASE_URL}/{execution_date}"
    params = {"base": "EUR", "symbols": devise}
    resp = requests.get(url, params=params, timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def extract_and_store(devise: str, execution_date: str) -> str:
    """Point d'entrée appelé par la tâche Airflow. Retourne la clé bronze écrite."""
    client = minio_client.get_client()
    start = time.time()
    try:
        payload = fetch_rate(devise, execution_date)
        payload["_ingested_at"] = execution_date
        payload["_devise_demandee"] = devise

        key = minio_client.bronze_key(execution_date, devise)
        minio_client.put_json(client, "bronze", key, payload)
        return key
    except (requests.RequestException, requests.Timeout) as exc:
        # Remontée à Airflow : les `retries`/`execution_timeout` de la tâche
        # géreront les nouvelles tentatives ; épuisées, la tâche échoue (DAG rouge).
        raise ExtractionError(f"Échec extraction {devise} pour {execution_date}: {exc}") from exc
    finally:
        duree_ms = int((time.time() - start) * 1000)
        print(f"[extract] devise={devise} date={execution_date} duree_ms={duree_ms}")