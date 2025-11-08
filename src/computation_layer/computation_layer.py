import os
import time
from datetime import datetime, timedelta
from typing import Any, Optional

import psycopg
from psycopg.rows import dict_row

DB_DSN = os.getenv("DB_DSN", "postgresql://admin:admin@postgres:5432/mydb")

# mapping colonne
DURATION_COLUMNS = {
    "robot_delivery_greeter_task": "cur_duration",
    "robot_delivery_call_task": "cur_duration",
    "robot_industrial_lifting_task": "cur_duration",
    "robot_delivery_recovery_task": "duration",
}

PK_COLUMNS = {
    "robot_delivery_greeter_task": "id",
    "robot_delivery_call_task": "id",
    "robot_delivery_recovery_task": "id",
    "robot_industrial_lifting_task": "id",
}

FALLBACK_SECONDS = 300  # 5 minuti

def _parse_dt(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(str(value), fmt)
        except ValueError:
            continue
    raise ValueError(f"datetime non valido: {value!r}")

def get_baseline_duration_seconds(conn, table, sn, shop_id):
    duration_col = DURATION_COLUMNS.get(table)
    if not duration_col:
        return FALLBACK_SECONDS

    with conn.cursor(row_factory=dict_row) as cur:
        # media per SN
        if sn:
            cur.execute(
                f"SELECT avg({duration_col}) AS avg_d FROM {table} WHERE sn=%s AND {duration_col} IS NOT NULL",
                (sn,),
            )
            r = cur.fetchone()
            if r and r["avg_d"]:
                return int(r["avg_d"])

        # media per shop
        if shop_id:
            cur.execute(
                f"SELECT avg({duration_col}) AS avg_d FROM {table} WHERE shop_id=%s AND {duration_col} IS NOT NULL",
                (shop_id,),
            )
            r = cur.fetchone()
            if r and r["avg_d"]:
                return int(r["avg_d"])

        # media globale
        cur.execute(f"SELECT avg({duration_col}) AS avg_d FROM {table} WHERE {duration_col} IS NOT NULL")
        r = cur.fetchone()
        if r and r["avg_d"]:
            return int(r["avg_d"])

    return FALLBACK_SECONDS

def insert_eta(conn, src_table, src_pk, task_id, shop_id, sn, ending_time):
    with conn.cursor() as cur:
        cur.execute(
            """
            INSERT INTO task_eta (src_table, src_pk, task_id, shop_id, sn, ending_time)
            VALUES (%s, %s, %s, %s, %s, %s)
            """,
            (src_table, src_pk, task_id, shop_id, sn, ending_time),
        )
    conn.commit()

def process_new_rows(conn, table):
    """legge righe recenti e scrive ETA"""
    pk_col = PK_COLUMNS[table]
    duration_col = DURATION_COLUMNS[table]

    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(
            f"""
            SELECT * FROM {table}
            WHERE inserted_at > NOW() - INTERVAL '30 seconds'
            """
        )
        rows = cur.fetchall()

    for row in rows:
        sn = row.get("sn")
        shop_id = row.get("shop_id")
        task_id = row.get("task_id")
        src_pk = row.get(pk_col)
        start_raw = row.get("begin_time") or row.get("task_time")
        if not start_raw:
            continue
        try:
            start_time = _parse_dt(start_raw)
        except ValueError:
            continue

        baseline = get_baseline_duration_seconds(conn, table, sn, shop_id)
        cur_dur = row.get(duration_col)
        dur = int(float(cur_dur)) if cur_dur and float(cur_dur) > 0 else baseline
        ending_time = start_time + timedelta(seconds=dur)

        insert_eta(conn, table, src_pk, task_id, shop_id, sn, ending_time)
        print(f"[ETA] {table} id={src_pk} fine prevista: {ending_time}")

def main():
    print("Serving layer ETA avviato...")
    with psycopg.connect(DB_DSN) as conn:
        while True:
            for table in DURATION_COLUMNS.keys():
                process_new_rows(conn, table)
            time.sleep(10)

if __name__ == "__main__":
    main()
