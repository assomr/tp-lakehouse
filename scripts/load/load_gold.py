"""Charge un enregistrement silver validé dans le schéma en étoile (zone gold).

Idempotence : chaque (id_date, id_devise) est contraint UNIQUE en base ;
un rechargement du même jour met à jour la ligne existante (UPSERT) au lieu
d'en créer une nouvelle — un run rejoué plusieurs fois ne duplique rien.
"""
from datetime import datetime

from scripts.common import db, minio_client


def _upsert_dim_date(conn, execution_date: str) -> int:
    d = datetime.strptime(execution_date, "%Y-%m-%d").date()
    id_date = int(d.strftime("%Y%m%d"))
    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO dim_date (id_date, date_complete, annee, mois, jour_semaine, jour_ouvre)
               VALUES (%s, %s, %s, %s, %s, %s)
               ON CONFLICT (id_date) DO NOTHING""",
            (id_date, d, d.year, d.month, d.isoweekday(), d.isoweekday() <= 5),
        )
    conn.commit()
    return id_date


def _get_id_devise(conn, code_iso: str) -> int:
    with conn.cursor() as cur:
        cur.execute("SELECT id_devise FROM dim_devise WHERE code_iso = %s", (code_iso,))
        row = cur.fetchone()
        if row is None:
            raise ValueError(f"Devise inconnue en dimension : {code_iso}")
        return row[0]


def _taux_veille(conn, id_devise: int, id_date: int) -> float | None:
    with conn.cursor() as cur:
        cur.execute(
            """SELECT taux_valeur FROM fact_taux_change
               WHERE id_devise = %s AND id_date < %s
               ORDER BY id_date DESC LIMIT 1""",
            (id_devise, id_date),
        )
        row = cur.fetchone()
        return float(row[0]) if row else None


def load(devise: str, execution_date: str) -> None:
    client = minio_client.get_client()
    conn = db.get_connection()

    record = minio_client.get_json(client, "silver", minio_client.silver_key(execution_date, devise))
    taux_valeur = float(record["rates"][devise])

    id_date = _upsert_dim_date(conn, execution_date)
    id_devise = _get_id_devise(conn, devise)

    veille = _taux_veille(conn, id_devise, id_date)
    variation_pct = round((taux_valeur - veille) / veille * 100, 4) if veille else None

    with conn.cursor() as cur:
        cur.execute(
            """INSERT INTO fact_taux_change (id_date, id_devise, taux_valeur, variation_veille_pct)
               VALUES (%s, %s, %s, %s)
               ON CONFLICT (id_date, id_devise)
               DO UPDATE SET taux_valeur = EXCLUDED.taux_valeur,
                             variation_veille_pct = EXCLUDED.variation_veille_pct,
                             load_ts = now()""",
            (id_date, id_devise, taux_valeur, variation_pct),
        )
    conn.commit()
    conn.close()
