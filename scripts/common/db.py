"""Connexion Postgres partagée pour la zone gold et les logs."""
import os

import psycopg2


def get_connection():
    return psycopg2.connect(
        host=os.environ.get("GOLD_DB_HOST", "localhost"),
        port=os.environ.get("GOLD_DB_PORT", "5434"),
        dbname=os.environ.get("GOLD_DB_NAME", "gold"),
        user=os.environ.get("GOLD_DB_USER", "gold_user"),
        password=os.environ.get("GOLD_DB_PASSWORD", "gold_password"),
    )


def log_technique(conn, execution_date, devise, etape, statut, message="", duree_ms=None):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO log_technique (execution_date, devise, etape, statut, message, duree_ms)
               VALUES (%s, %s, %s, %s, %s, %s)""",
            (execution_date, devise, etape, statut, message, duree_ms),
        )
    conn.commit()


def log_qualite(conn, execution_date, devise, regle, statut, detail=""):
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO log_qualite (execution_date, devise, regle, statut, detail)
               VALUES (%s, %s, %s, %s, %s)""",
            (execution_date, devise, regle, statut, detail),
        )
    conn.commit()
