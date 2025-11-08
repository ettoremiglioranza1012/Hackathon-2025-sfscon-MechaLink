import datetime
from fastapi import FastAPI, HTTPException, Query
from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List, Any
import psycopg
from psycopg.rows import dict_row
import os
app = FastAPI()
# Database connection string - uses service name 'postgres' in Docker, 'localhost' for local dev
# Can be overridden with DB_DSN environment variable
DB_HOST = os.getenv("DB_HOST", "postgres")  # Use 'postgres' service name in Docker, 'localhost' for local
DB_USER = os.getenv("DB_USER", "admin")
DB_PASSWORD = os.getenv("DB_PASSWORD", "admin")
DB_NAME = os.getenv("DB_NAME", "mydb")
DB_PORT = os.getenv("DB_PORT", "5432")

DB_DSN = os.getenv(
    "DB_DSN",
    f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
)
@app.get("/shops")
def get_shops():
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("SELECT shop_id, shop_name FROM shop ORDER BY shop_name;")
            rows = cur.fetchall()
    return {"shops": rows}

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

@app.get("/lifting")
def get_industrial_lifting(shop_id: int | None = None, limit: int = 50):
    query = """
        SELECT id, arrival_time, begin_time, cur_duration, cur_mileage, destination,
               mac, product_code, robot_name, shop_id, shop_name, sn,
               stay_duration, task_time, inserted_at
        FROM robot_industrial_lifting_task
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

    return {"lifting": rows}


@app.get("/tasks")
def get_tasks(shop_id: int | None = None):
    """
    Restituisce sn, task_type e shop_id dai robot
    filtrando opzionalmente per shop_id.
    """
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute("""
                SELECT
                    rtb.sn,
                    rtb.task_type,
                    rtb.task_subtype,
                    r.shop_id
                FROM robot_task_capability AS rtb
                JOIN robots AS r ON r.sn = rtb.sn;
            """)
            rows = cur.fetchall()
    return {"tasks": rows}




class RunTaskBody(BaseModel):
    task_type: str              # delivery | cleaning | industrial
    task_subtype: str | None = None  # greeter | call | recovery | lifting | ...


from datetime import datetime
from fastapi import HTTPException

@app.post("/robots/{sn}/run-task")
def run_task(sn: str, body: RunTaskBody):
    now = datetime.utcnow()

    with psycopg.connect(DB_DSN) as conn, conn.cursor(row_factory=dict_row) as cur:
        # robot + mac
        cur.execute("""
            SELECT r.sn,
                   r.shop_id,
                   s.shop_name,
                   r.product_code,
                   r.mac
            FROM robots r
            JOIN shop s ON s.shop_id = r.shop_id
            WHERE r.sn = %s;
        """, (sn,))
        robot = cur.fetchone()
        if not robot:
            raise HTTPException(status_code=404, detail="Robot non trovato")

        shop_id = robot["shop_id"]
        shop_name = robot["shop_name"]
        product_code = robot["product_code"]
        robot_mac = robot["mac"] or "00:00:00:00:00:00"   # fallback inventato

        # capability check compatto
        capability_sql = """
            SELECT 1
            FROM robot_task_capability
            WHERE sn = %s
              AND task_type = %s
        """
        params = [sn, body.task_type]
        if body.task_subtype is None:
            capability_sql += " AND task_subtype IS NULL"
        else:
            capability_sql += " AND task_subtype = %s"
            params.append(body.task_subtype)
        capability_sql += " LIMIT 1;"
        cur.execute(capability_sql, params)
        if not cur.fetchone():
            raise HTTPException(status_code=400, detail="Capability non presente per questo robot")

        # instradamento
        if body.task_type == "delivery":
            if body.task_subtype == "greeter":
                cur.execute("""
                    INSERT INTO robot_delivery_greeter_task (
                        arrival_time,
                        begin_time,
                        cur_duration,
                        cur_mileage,
                        destination,
                        mac,
                        product_code,
                        robot_name,
                        shop_id,
                        shop_name,
                        sn,
                        stay_duration,
                        task_time
                    )
                    VALUES (
                        %s, %s,
                        0,              -- cur_duration inventato
                        0,              -- cur_mileage inventato
                        'AUTO-DEST',    -- destination inventata
                        %s,
                        %s,
                        %s,             -- robot_name (uso sn)
                        %s, %s,
                        %s,
                        0,              -- stay_duration inventato
                        %s
                    )
                    RETURNING id;
                """, (
                    now, now,
                    robot_mac,
                    product_code,
                    sn,
                    shop_id, shop_name,
                    sn,
                    now
                ))
                inserted = cur.fetchone()
                table = "robot_delivery_greeter_task"

            elif body.task_subtype == "call":
                cur.execute("""
                    INSERT INTO robot_delivery_call_task (
                        arrival_time,
                        begin_time,
                        cur_duration,
                        cur_mileage,
                        destination,
                        mac,
                        product_code,
                        robot_name,
                        shop_id,
                        shop_name,
                        sn,
                        stay_duration,
                        task_time
                    )
                    VALUES (
                        %s, %s,
                        0,
                        0,
                        'AUTO-DEST',
                        %s,
                        %s,
                        %s,
                        %s, %s,
                        %s,
                        0,
                        %s
                    )
                    RETURNING id;
                """, (
                    now, now,
                    robot_mac,
                    product_code,
                    sn,
                    shop_id, shop_name,
                    sn,
                    now
                ))
                inserted = cur.fetchone()
                table = "robot_delivery_call_task"

            elif body.task_subtype == "recovery":
                cur.execute("""
                    INSERT INTO robot_delivery_recovery_task (
                        task_time,
                        mac,
                        shop_id,
                        shop_name,
                        product_code,
                        sn,
                        mileage,
                        duration,
                        table_count,
                        tray_count,
                        already_unbind,
                        task_count,
                        speed,
                        run_count,
                        bind_count
                    )
                    VALUES (
                        %s,
                        %s,
                        %s, %s,
                        %s,
                        %s,
                        0,      -- mileage
                        0,      -- duration
                        0,      -- table_count
                        0,      -- tray_count
                        FALSE,  -- already_unbind
                        1,      -- task_count
                        0,      -- speed
                        0,      -- run_count
                        0       -- bind_count
                    )
                    RETURNING id;
                """, (
                    now.date(),
                    robot_mac,
                    shop_id, shop_name,
                    product_code,
                    sn
                ))
                inserted = cur.fetchone()
                table = "robot_delivery_recovery_task"

            else:
                raise HTTPException(status_code=400, detail="delivery sottotipo non supportato")

        elif body.task_type == "cleaning":
            # lasciato come prima
            cur.execute("""
                INSERT INTO cleaning_task (
                    task_id,
                    version,
                    name,
                    description,
                    status,
                    is_single_task,
                    task_count,
                    task_mode,
                    pre_clean_time,
                    is_area_connect,
                    is_hand_sort,
                    shop_id,
                    robot_sn
                )
                VALUES (
                    substring(md5(random()::text) for 16),
                    1,
                    %s,
                    NULL,
                    0,
                    TRUE,
                    1,
                    0,
                    0,
                    FALSE,
                    FALSE,
                    %s,
                    %s
                )
                RETURNING task_id;
            """, (f"auto-{sn}", shop_id, sn))
            inserted = cur.fetchone()
            table = "cleaning_task"

        elif body.task_type == "industrial" and body.task_subtype == "lifting":
            cur.execute("""
                INSERT INTO robot_industrial_lifting_task (
                    arrival_time,
                    begin_time,
                    cur_duration,
                    cur_mileage,
                    destination,
                    mac,
                    product_code,
                    robot_name,
                    shop_id,
                    shop_name,
                    sn,
                    stay_duration,
                    task_time
                )
                VALUES (
                    %s, %s,
                    0,
                    0,
                    'AUTO-DEST',
                    %s,
                    %s,
                    %s,
                    %s, %s,
                    %s,
                    0,
                    %s
                )
                RETURNING id;
            """, (
                now, now,
                robot_mac,
                product_code,
                sn,
                shop_id, shop_name,
                sn,
                now
            ))
            inserted = cur.fetchone()
            table = "robot_industrial_lifting_task"

        else:
            raise HTTPException(status_code=400, detail="task_type/task_subtype non supportati")

        conn.commit()

    return {
        "status": "inserted",
        "table": table,
        "id": inserted.get("id") if "id" in inserted else inserted.get("task_id"),
        "sn": sn,
        "task_type": body.task_type,
        "task_subtype": body.task_subtype,
    }

@app.get("/eta")
def list_eta(
    src_table: Optional[str] = None,
    src_pk: Optional[int] = None,
    sn: Optional[str] = None,
    shop_id: Optional[int] = None,
    limit: int = Query(50, ge=1, le=500),
):
    clauses = []
    params: List[Any] = []

    if src_table:
        clauses.append("src_table = %s")
        params.append(src_table)
    if src_pk is not None:
        clauses.append("src_pk = %s")
        params.append(src_pk)
    if sn:
        clauses.append("sn = %s")
        params.append(sn)
    if shop_id is not None:
        clauses.append("shop_id = %s")
        params.append(shop_id)

    where_sql = ""
    if clauses:
        where_sql = "WHERE " + " AND ".join(clauses)

    sql = f"""
        SELECT id,
               src_table,
               src_pk,
               task_id,
               shop_id,
               sn,
               ending_time,
               computed_at
        FROM task_eta
        {where_sql}
        ORDER BY computed_at DESC
        LIMIT %s
    """
    params.append(limit)

    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(sql, params)
            rows = cur.fetchall()

    return {"count": len(rows), "results": rows}


@app.get("/eta/{eta_id}")
def get_eta(eta_id: int):
    with psycopg.connect(DB_DSN) as conn:
        with conn.cursor(row_factory=dict_row) as cur:
            cur.execute(
                """
                SELECT id,
                       src_table,
                       src_pk,
                       task_id,
                       shop_id,
                       sn,
                       ending_time,
                       computed_at
                FROM task_eta
                WHERE id = %s
                """,
                (eta_id,),
            )
            row = cur.fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="ETA non trovata")

    return row
