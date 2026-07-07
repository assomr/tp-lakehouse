"""Lit un enregistrement bronze, applique les 5 règles qualité,
écrit en silver (validé) ou silver-quarantine (rejeté), et logge chaque règle."""
from scripts.common import db, minio_client
from scripts.quality.rules import evaluate_all

# set partagé au niveau du run pour la règle d'unicité — un run = un exécution_date,
# donc réinitialisé à chaque déclenchement du DAG (pas de portée globale entre runs).
_DEJA_VUS_RUN: set = set()


def process(devise: str, execution_date: str) -> str:
    """Retourne 'valide' ou 'quarantaine' selon le résultat des règles qualité."""
    client = minio_client.get_client()
    conn = db.get_connection()

    bronze_record = minio_client.get_json(client, "bronze", minio_client.bronze_key(execution_date, devise))

    resultats = evaluate_all(bronze_record, devise, execution_date, _DEJA_VUS_RUN)

    for regle, ok, detail in resultats:
        db.log_qualite(
            conn,
            execution_date=execution_date,
            devise=devise,
            regle=regle,
            statut="ok" if ok else "quarantaine",
            detail=detail,
        )

    toutes_ok = all(ok for _, ok, _ in resultats)

    if toutes_ok:
        minio_client.put_json(
            client, "silver", minio_client.silver_key(execution_date, devise), bronze_record
        )
        conn.close()
        return "valide"
    else:
        raisons = "; ".join(f"{regle}: {detail}" for regle, ok, detail in resultats if not ok)
        bronze_record["_raison_quarantaine"] = raisons
        minio_client.put_json(
            client, "silver-quarantine", minio_client.quarantine_key(execution_date, devise), bronze_record
        )
        conn.close()
        return "quarantaine"
