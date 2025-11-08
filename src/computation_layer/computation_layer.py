import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timezone, timedelta
import json
import os
import time

DB_DSN = os.getenv("DB_DSN", "postgresql://admin:admin@postgres:5432/mydb")

def get_avg_duration_sec(conn, table_name: str, shop_id: int | None):
    base = f"""
        SELECT EXTRACT(EPOCH FROM (arrival_time - begin_time)) AS sec
        FROM {table_name}
        WHERE arrival_time IS NOT NULL
          AND begin_time IS NOT NULL
    """
    params = []
    if shop_id is not None:
        base += " AND shop_id = %s"
        params.append(shop_id)
    base += " ORDER BY arrival_time DESC LIMIT 200"

    with conn.cursor() as cur:
        cur.execute(base, params)
        rows = cur.fetchall()

    secs = [r[0] for r in rows if r[0]]
    if not secs:
        return 300.0
    return sum(secs) / len(secs)

def predict_eta(row: dict, avg_sec: float):
    # se già finita
    if row.get("arrival_time"):
        return 0, row["arrival_time"]

    now = datetime.now(timezone.utc)
    begin_time = row.get("begin_time") or now
    elapsed = (now - begin_time).total_seconds()
    remaining = max(avg_sec - elapsed, 15.0)
    eta = now + timedelta(seconds=remaining)
    return int(remaining), eta

def fetch_row(conn, table_name: str, task_id: int):
    with conn.cursor(row_factory=dict_row) as cur:
        cur.execute(f"SELECT * FROM {table_name} WHERE id = %s", (task_id,))
        return cur.fetchone()

def upsert_eta(conn, task_id: int, table_name: str, remaining: int, eta):
    with conn.cursor() as cur:
        cur.execute("""
            INSERT INTO task_eta (task_id, predicted_end_ts, predicted_remaining_sec)
            VALUES (%s, %s, %s, NOW())
            ON CONFLICT (task_id)
            DO UPDATE SET
                predicted_end_ts = EXCLUDED.predicted_end_ts,
                predicted_remaining_sec = EXCLUDED.predicted_remaining_sec
        """, (task_id, table_name, eta, remaining))
    conn.commit()

def listen():
    with psycopg.connect(DB_DSN) as conn:
        conn.execute("LISTEN new_delivery_task;")
        print("listening on new_delivery_task")
        while True:
            conn.poll()
            while conn.notifies:
                notify = conn.notifies.pop(0)
                payload = json.loads(notify.payload)
                table = payload["table"]
                task_id = payload["id"]
                shop_id = payload.get("shop_id")

                # ricarico riga
                row = fetch_row(conn, table, task_id)
                if not row:
                    continue

                avg_sec = get_avg_duration_sec(conn, table, shop_id)
                remaining, eta = predict_eta(row, avg_sec)
                upsert_eta(conn, task_id, table, remaining, eta)
            time.sleep(0.5)

if __name__ == "__main__":
    listen()
