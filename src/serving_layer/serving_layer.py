from fastapi import FastAPI
import psycopg
from psycopg.rows import dict_row

app = FastAPI()

DB_DSN = "postgresql://admin:admin@localhost:5432/mydb"

@app.get("/shops")
def get_shops():
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT shop_id, shop_name FROM shop ORDER BY shop_name;")
            rows = cur.fetchall()
    return {"shops": rows}

from fastapi import FastAPI
import psycopg
from psycopg.rows import dict_row

DB_DSN = "postgresql://admin:admin@localhost:5432/mydb"

app = FastAPI()

@app.get("/delivery/greeter")
def get_delivery_greeter(shop_id: int | None = None, limit: int = 50):
    query = """
        SELECT id, arrival_time, begin_time, cur_duration, cur_mileage,
               destination, mac, product_code, robot_name,
               shop_id, shop_name, sn, stay_duration, task_time, inserted_at
        FROM robot_delivery_greeter_task
    """
    params = []
    if shop_id is not None:
        query += " WHERE shop_id = %s"
        params.append(shop_id)
    query += " ORDER BY task_time DESC LIMIT %s"
    params.append(limit)

    with psycopg.connect(DB_DSN) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return {"greeter": rows}


@app.get("/delivery/recovery")
def get_delivery_recovery(shop_id: int | None = None, limit: int = 50):
    query = """
        SELECT id, task_time, mac, shop_id, shop_name,
               product_code, product_name, bind_time, mileage, duration,
               table_count, tray_count, already_unbind,
               sn, task_count, speed, run_count, bind_count, inserted_at
        FROM robot_delivery_recovery_task
    """
    params = []
    if shop_id is not None:
        query += " WHERE shop_id = %s"
        params.append(shop_id)
    query += " ORDER BY task_time DESC LIMIT %s"
    params.append(limit)

    with psycopg.connect(DB_DSN) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return {"recovery": rows}


@app.get("/delivery/call")
def get_delivery_call(shop_id: int | None = None, limit: int = 50):
    query = """
        SELECT id, arrival_time, begin_time, cur_duration, cur_mileage,
               destination, mac, product_code, robot_name,
               shop_id, shop_name, sn, stay_duration, task_time, inserted_at
        FROM robot_delivery_call_task
    """
    params = []
    if shop_id is not None:
        query += " WHERE shop_id = %s"
        params.append(shop_id)
    query += " ORDER BY task_time DESC LIMIT %s"
    params.append(limit)

    with psycopg.connect(DB_DSN) as conn, conn.cursor(row_factory=dict_row) as cur:
        cur.execute(query, params)
        rows = cur.fetchall()
    return {"call": rows}

